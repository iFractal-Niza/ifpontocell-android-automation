import base64
import html
import json
import os
import re
from datetime import datetime

import pytest
from pytest_html import extras

from observability import execution_metrics, pastas, testes_manuais
from observability.contexto_execucao import coletar_contexto
from observability.dashboard import (
    build_results_summary_html,
    load_inline_js,
)
from observability.evidencias import retirar_evidencias
from observability.video import ATRIBUTO_VIDEO
from utils.file_utils import (
    build_screenshot_path,
)
from utils.helpers import (
    current_timestamp,
    ensure_dir,
)
from utils.logger import get_logger

logger = get_logger("pytest_report")


# === Diretórios e arquivos ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A pasta pode ser por aparelho (DEVICE=... no make): observability.pastas.
REPORTS_DIR = pastas.REPORTS_DIR

SCREENSHOTS_DIR = os.path.join(
    REPORTS_DIR,
    "screenshots",
)


# === Configuração do relatório ===
MAX_REPORTS = 10

_DRIVER_FIXTURES = (
    "driver",
    "driver_e2e",
    "driver_registro_ponto",
    "home_para_marcacao",
)

# Atributo do report com o título legível do teste (primeira frase do
# docstring), gravado no makereport e usado na tabela e nas ressalvas.
ATRIBUTO_TITULO = "titulo_legivel"

# Marker com o ID do caso de teste (ver observability.casos_teste).
MARKER_CT = "ct"

# Início da execução, para a data e a duração do cabeçalho do dashboard.
_inicio_execucao = datetime.now()

LEGENDA_PRINT_FALHA = "Print da falha"

# Controla a contabilização única por teste na fase de erro.
# Evita que uma falha em setup e outra em teardown do mesmo
# teste incrementem o contador de erros mais de uma vez.
_nodeids_com_erro_contabilizado: set[str] = set()


# === Estrutura dos relatórios ===
def limpar_reports_antigos(
    diretorio: str,
    limite: int = MAX_REPORTS,
) -> None:
    """
    Remove os relatórios HTML antigos, mantendo apenas
    a quantidade mais recente definida pelo limite.
    """
    if not os.path.exists(diretorio):
        return

    arquivos = sorted(
        [
            os.path.join(
                diretorio,
                nome_arquivo,
            )
            for nome_arquivo in os.listdir(diretorio)
            if (
                nome_arquivo.startswith("report_")
                and nome_arquivo.endswith(".html")
            )
        ],
        key=os.path.getmtime,
        reverse=True,
    )

    for arquivo in arquivos[limite:]:
        try:
            os.remove(arquivo)

            logger.info(
                "Relatório antigo removido",
                extra={
                    "event": "old_report_removed",
                    "report_path": arquivo,
                },
            )

        except Exception:
            logger.exception(
                "Não foi possível remover o relatório antigo",
                extra={
                    "event": "old_report_remove_failed",
                    "report_path": arquivo,
                },
            )


def garantir_estrutura_reports() -> None:
    """
    Garante a existência da estrutura mínima necessária
    para geração dos relatórios.
    """
    ensure_dir(REPORTS_DIR)
    ensure_dir(SCREENSHOTS_DIR)


def _driver_de(valor):
    """
    O driver contido em um valor de fixture: o próprio driver, ou o
    .driver de uma Page/AppSession. None se não houver.
    """
    if hasattr(valor, "save_screenshot"):
        return valor

    driver_interno = getattr(valor, "driver", None)

    if hasattr(driver_interno, "save_screenshot"):
        return driver_interno

    return None


def _fixtures_montadas(item) -> list:
    """
    Valores das fixtures que o pytest já montou para o item, inclusive
    as pedidas só por outras fixtures (dependências).

    Usa o cache interno do pytest (item._request._fixture_defs, com
    cached_result = (valor, chave, erro)); se a estrutura mudar numa
    versão futura, devolve vazio em vez de quebrar o report.
    """
    try:
        definicoes = item._request._fixture_defs.values()

        return [
            definicao.cached_result[0]
            for definicao in definicoes
            if definicao.cached_result is not None
            and definicao.cached_result[2] is None
        ]
    except (AttributeError, IndexError, TypeError):
        return []


def obter_driver_ativo(item):
    """
    Retorna a instância ativa do driver usada pelo teste.

    Procura primeiro nas fixtures conhecidas (ordem de preferência) e
    depois em qualquer fixture do teste: assim uma fixture nova (ex.:
    home_autenticada) não fica sem screenshot por não estar na lista.

    Por último, nas fixtures já montadas mas fora do item.funcargs: numa
    falha de setup, a sessão (que tem o driver) já subiu, mas só entra
    em funcargs quem o teste pede direto — se a home_autenticada falha,
    a app_session_... que ela usa não está lá.
    """
    conhecidas = [item.funcargs.get(nome) for nome in _DRIVER_FIXTURES]
    demais = [
        valor
        for nome, valor in item.funcargs.items()
        if nome not in _DRIVER_FIXTURES
    ]

    for valor in (*conhecidas, *demais, *_fixtures_montadas(item)):
        if valor is None:
            continue

        driver = _driver_de(valor)

        if driver is not None:
            return driver

    return None


def titulo_do_item(item) -> str:
    """
    Título legível do teste, com o ID do caso de teste na frente quando
    ele tem o marker ct: "CT011 · Valida a abertura...".
    """
    titulo = execution_metrics.extract_titulo(
        item.nodeid,
        getattr(getattr(item, "function", None), "__doc__", None),
    )

    marker = item.get_closest_marker(MARKER_CT)

    if marker is None or not marker.args:
        return titulo

    return f"{marker.args[0]} · {titulo}"


# === Configuração do Pytest ===
# Criado ao fim da execução quando há teste pulado: o Makefile abre o
# report também nesse caso (pulado não muda o código de saída do pytest,
# que só abre o report sozinho quando algo falha).
ARQUIVO_PULADOS = os.path.join(REPORTS_DIR, ".pulados")


def marcar_pulados(quantidade: int, arquivo: str = ARQUIVO_PULADOS) -> None:
    """Grava a quantidade de pulados, ou apaga o aviso se não houve."""
    try:
        if quantidade > 0:
            with open(arquivo, "w", encoding="utf-8") as saida:
                saida.write(str(quantidade))
        elif os.path.exists(arquivo):
            os.remove(arquivo)
    except OSError:
        logger.warning("Não foi possível atualizar o aviso de pulados.")


def pytest_sessionfinish(session, exitstatus) -> None:
    marcar_pulados(execution_metrics.DASHBOARD_STATS.get("skipped", 0))


# === Correção do JS do pytest-html ===
# O app.js da lib só troca o src do <source> ao abrir outra mídia, sem
# chamar load(); o navegador continua no vídeo anterior. Importante para
# vídeos embutidos como data:video/mp4;base64,...
_TROCA_SRC_VIDEO = re.compile(r"^([ \t]*)sourceEl\.src = media\.path\n", re.M)

_RECARGA_VIDEO = (
    "\n"
    "{indent}// Força o navegador a recarregar o <source> quando a mídia"
    " é trocada.\n"
    "{indent}// Importante para vídeos embutidos como"
    " data:video/mp4;base64,...\n"
    "{indent}videoEl.load()\n"
)


def corrigir_troca_de_video(conteudo: str) -> str:
    """Insere videoEl.load() após a troca do src do vídeo no app.js."""
    if "videoEl.load()" in conteudo:
        return conteudo

    return _TROCA_SRC_VIDEO.sub(
        lambda m: m.group(0) + _RECARGA_VIDEO.format(indent=m.group(1)),
        conteudo,
        count=1,
    )


def pytest_unconfigure(config) -> None:
    """
    Aplica corrigir_troca_de_video no HTML final.

    Roda depois do pytest_sessionfinish do pytest-html, que é quando o
    arquivo do relatório termina de ser gravado.
    """
    caminho = getattr(config.option, "htmlpath", None)
    if not caminho or not os.path.exists(caminho):
        return

    try:
        with open(caminho, encoding="utf-8") as entrada:
            conteudo = entrada.read()

        corrigido = corrigir_troca_de_video(conteudo)
        if corrigido == conteudo:
            if "videoEl.load()" not in conteudo:
                logger.warning(
                    "Trecho de troca de vídeo do pytest-html não encontrado.",
                    extra={"event": "report_video_patch_not_found"},
                )
            return

        with open(caminho, "w", encoding="utf-8") as saida:
            saida.write(corrigido)
    except OSError:
        logger.warning(
            "Não foi possível corrigir a troca de vídeo do relatório."
        )


def pytest_configure(
    config,
) -> None:
    """
    Configura os diretórios, o nome do relatório HTML
    e os metadados da execução.
    """
    timestamp = current_timestamp()

    garantir_estrutura_reports()
    marcar_pulados(0)

    config.option.htmlpath = os.path.join(
        REPORTS_DIR,
        f"report_{timestamp}.html",
    )
    config.option.self_contained_html = True

    limpar_reports_antigos(
        REPORTS_DIR,
        limite=MAX_REPORTS,
    )

    logger.info(
        "Configuração inicial do relatório concluída",
        extra={
            "event": "pytest_report_configured",
            "report_path": config.option.htmlpath,
            "environment": os.getenv(
                "ENV",
                "local",
            ),
        },
    )

    global _inicio_execucao
    _inicio_execucao = datetime.now()

    _nodeids_com_erro_contabilizado.clear()
    execution_metrics.reset_dashboard_stats()


# === Personalização do pytest-html ===
@pytest.hookimpl(optionalhook=True)
def pytest_metadata(
    metadata: dict,
) -> None:
    """
    Remove os metadados nativos do relatório.

    As informações relevantes da execução são exibidas
    diretamente no dashboard customizado.
    """
    metadata.clear()


@pytest.hookimpl(optionalhook=True)
def pytest_html_report_title(
    report,
) -> None:
    """
    Define o título da aba do navegador.
    """
    report.title = "Android Automation Report"


# === Métricas da execução ===
def _e_smoke(report) -> bool:
    """O teste é do smoke (o essencial do app): a falha dele é crítica."""
    return "smoke" in getattr(report, "keywords", {})


def pytest_runtest_logreport(
    report,
) -> None:
    """
    Atualiza as métricas globais com base no resultado
    de cada etapa do teste.

    A fase de chamada registra o resultado funcional do teste.
    As fases de setup e teardown registram apenas erros técnicos
    ou pulos, contabilizados uma única vez por teste para evitar
    dupla contagem quando setup e teardown falham no mesmo nó.
    """
    logger.debug(
        "Atualizando métricas do teste",
        extra={
            "event": "pytest_runtest_logreport",
            "when": report.when,
            "outcome": report.outcome,
            "nodeid": report.nodeid,
        },
    )

    motivo_pulo = (
        execution_metrics.extract_skip_reason(report) if report.skipped else ""
    )

    if report.when in ("setup", "call", "teardown"):
        execution_metrics.registrar_duracao(
            report.nodeid,
            getattr(report, "duration", 0.0),
            titulo=getattr(report, ATRIBUTO_TITULO, ""),
        )

    if report.when == "call":
        execution_metrics.update_dashboard_stats(
            report.nodeid,
            report.outcome,
            motivo=motivo_pulo,
            titulo=getattr(report, ATRIBUTO_TITULO, ""),
            smoke=_e_smoke(report),
        )
        return

    if report.when not in (
        "setup",
        "teardown",
    ):
        return

    if report.failed:
        if report.nodeid in _nodeids_com_erro_contabilizado:
            logger.debug(
                "Erro do teste já contabilizado; ignorando",
                extra={
                    "event": "duplicate_error_skipped",
                    "nodeid": report.nodeid,
                    "when": report.when,
                },
            )
            return

        _nodeids_com_erro_contabilizado.add(report.nodeid)

        execution_metrics.update_dashboard_stats(
            report.nodeid,
            "error",
            titulo=getattr(report, ATRIBUTO_TITULO, ""),
            smoke=_e_smoke(report),
        )

    elif report.skipped:
        execution_metrics.update_dashboard_stats(
            report.nodeid,
            "skipped",
            motivo=motivo_pulo,
            titulo=getattr(report, ATRIBUTO_TITULO, ""),
        )


# === Evidências de falha ===
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item,
    call,
):
    """
    Adiciona screenshot e resumo do erro ao relatório HTML quando ocorre
    uma falha, e as evidências registradas pelo teste em qualquer
    resultado.
    """
    outcome = yield
    report = outcome.get_result()

    setattr(report, ATRIBUTO_TITULO, titulo_do_item(item))

    report_extras = getattr(
        report,
        "extras",
        [],
    )

    etapa_com_falha = (
        report.when
        in (
            "call",
            "setup",
            "teardown",
        )
        and report.failed
    )

    if etapa_com_falha:
        driver_instance = obter_driver_ativo(item)

        error_message = execution_metrics.extract_error_message(report)

        escaped_error = html.escape(
            error_message,
            quote=True,
        )

        logger.debug(
            "Falha identificada durante a geração do relatório",
            extra={
                "event": "pytest_failure_report",
                "test_name": item.name,
                "when": report.when,
            },
        )

        if driver_instance:
            try:
                path = build_screenshot_path(
                    SCREENSHOTS_DIR,
                    item.name,
                )

                screenshot_saved = driver_instance.save_screenshot(path)

                if screenshot_saved and anexar_imagem(
                    report_extras,
                    path,
                    LEGENDA_PRINT_FALHA,
                ):
                    logger.info(
                        "Screenshot anexado ao relatório",
                        extra={
                            "event": ("report_screenshot_attached"),
                            "test_name": item.name,
                            "screenshot_path": path,
                            "when": report.when,
                        },
                    )

                else:
                    logger.warning(
                        "O driver não retornou um screenshot válido",
                        extra={
                            "event": ("report_screenshot_not_saved"),
                            "test_name": item.name,
                            "when": report.when,
                            "screenshot_path": path,
                        },
                    )

            except Exception:
                logger.exception(
                    "Não foi possível salvar o screenshot no relatório",
                    extra={
                        "event": ("report_screenshot_failed"),
                        "test_name": item.name,
                        "when": report.when,
                    },
                )

            anexar_arvore_da_tela(report_extras, driver_instance, item.name)

        else:
            logger.warning(
                "Nenhum driver ativo foi encontrado "
                "para capturar o screenshot",
                extra={
                    "event": "report_driver_not_found",
                    "test_name": item.name,
                    "when": report.when,
                    "available_funcargs": list(item.funcargs.keys()),
                },
            )

        report_extras.append(
            extras.html(
                f'<button type="button" '
                f'style="margin-top:8px;'
                f'padding:6px 10px;'
                f'border-radius:8px;'
                f'border:none;'
                f'cursor:pointer;" '
                f'onclick="navigator.clipboard.'
                f"writeText('{escaped_error}')\">"
                f"Copiar erro</button>"
            )
        )

        report_extras.append(
            extras.text(
                error_message,
                name="Erro resumido",
            )
        )

    # Vídeo do teste (opção --video), gravado durante a chamada.
    caminho_video = getattr(item, ATRIBUTO_VIDEO, None)

    if report.when == "call" and caminho_video:
        anexar_video(report_extras, caminho_video)

    # Evidências registradas pelo próprio teste (capturar_evidencia),
    # qualquer que seja o resultado — inclusive skip por falta de massa.
    for caminho, descricao in retirar_evidencias(report.nodeid):
        anexar_imagem(
            report_extras,
            caminho,
            f"Evidência: {descricao}",
        )

    report.extras = report_extras


# === Imagens no report ===
def anexar_imagem(
    report_extras: list,
    caminho: str,
    legenda: str,
) -> bool:
    """
    Anexa o PNG ao report **embutido** (base64), não pelo caminho.

    Pelo caminho, a imagem só abre na máquina que rodou os testes: no
    HTML enviado ao time (Drive, e-mail) ela aparecia quebrada. O arquivo
    continua salvo em reports/screenshots/. Retorna False se não houver
    arquivo para anexar.
    """
    try:
        with open(caminho, "rb") as arquivo:
            conteudo = base64.b64encode(arquivo.read()).decode("ascii")
    except OSError:
        return False

    report_extras.append(extras.png(conteudo, name=legenda))

    return True


LEGENDA_VIDEO = "Vídeo do teste"
LEGENDA_ARVORE = "Árvore da tela"


def anexar_arvore_da_tela(
    report_extras: list, driver, nome_teste: str
) -> bool:
    """
    Anexa a árvore de acessibilidade da tela no momento da falha (o mesmo
    XML do Appium Inspector), para investigar locator sem reproduzir a
    falha. Salva também o .xml ao lado dos prints. False se o driver não
    devolver a árvore (ex.: sessão perdida).
    """
    try:
        arvore = driver.page_source
    except Exception:
        logger.warning(
            "Não foi possível capturar a árvore da tela na falha",
            extra={
                "event": "report_page_source_failed",
                "test_name": nome_teste,
            },
        )
        return False

    if not arvore:
        return False

    caminho = build_screenshot_path(SCREENSHOTS_DIR, nome_teste).rsplit(
        ".", 1
    )[0]
    caminho = f"{caminho}_arvore.xml"

    try:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(arvore)
    except OSError:
        pass

    report_extras.append(extras.text(arvore, name=LEGENDA_ARVORE))

    return True


def anexar_video(report_extras: list, caminho: str) -> bool:
    """
    Anexa o vídeo do teste ao report, embutido (base64), como as
    imagens. False se não houver arquivo.
    """
    try:
        with open(caminho, "rb") as arquivo:
            conteudo = base64.b64encode(arquivo.read()).decode("ascii")
    except OSError:
        return False

    report_extras.append(extras.video(conteudo, name=LEGENDA_VIDEO))

    return True


# === Coluna Teste ===
def montar_celula_teste(
    celula_original: str,
    titulo: str,
) -> str:
    """
    Célula da coluna Teste com o título legível em destaque e o caminho
    técnico (nodeid) abaixo.

    Fica em uma linha só: o pytest-html extrai o conteúdo da célula com
    uma regex que não atravessa quebras de linha.
    """
    encontrado = re.search(r"<td[^>]*>(.*?)</td>", celula_original)

    if not titulo or encontrado is None:
        return celula_original

    return (
        '<td class="col-testId">'
        f'<div class="qa-test-title">{html.escape(titulo)}</div>'
        f'<div class="qa-test-path">{encontrado.group(1)}</div>'
        "</td>"
    )


# === Classificação do erro (Categoria e Tipo) ===
# Preenchida por quem analisa o report, nas linhas de falha: listas
# editáveis, salvas no navegador (report.js). Ficam logo após a coluna
# Teste.
CATEGORIAS_DE_ERRO = ("Baixo", "Moderado", "Crítico")

TIPOS_DE_ERRO = (
    "Texto / Digitação",
    "Ordenação",
    "Layout",
    "Travamento / Crash",
    "Elemento não exibido",
    "Filtragem",
    "Regra de Negócio",
    "Marcação de Ponto",
    "Cálculo",
    "Outro",
)

# Andamento do apontamento (o erro ou a melhoria apontada ao time).
STATUS_DE_APONTAMENTO = (
    "Melhoria implementada",
    "Melhoria não implementada",
    "Correção realizada",
    "Correção não realizada",
)

COLUNAS_DE_CLASSIFICACAO = (
    ("categoria", "Categoria do erro", CATEGORIAS_DE_ERRO),
    ("tipo", "Tipo de erro", TIPOS_DE_ERRO),
    ("apontamento", "Status apont.", STATUS_DE_APONTAMENTO),
)

# Ordem da tabela: Teste, Status, Categoria do erro, Tipo de erro,
# Status apont., Duração, Evidências. O pytest-html entrega Result,
# Test, Duration, Links: Teste e Status trocam de lugar e a
# classificação entra depois.
POSICAO_CLASSIFICACAO = 2


def _teste_antes_do_status(cells: list) -> None:
    cells[0], cells[1] = cells[1], cells[0]


def montar_celula_classificacao(
    campo: str,
    titulo: str,
    opcoes: tuple[str, ...],
    nodeid: str,
    com_erro: bool,
) -> str:
    """
    Célula com a lista de opções, só nas linhas com erro; nas outras,
    um traço. Em uma linha só, como a célula do teste.
    """
    if not com_erro:
        return '<td class="col-classificacao qa-sem-erro">—</td>'

    itens = '<option value="">Selecionar</option>' + "".join(
        f'<option value="{html.escape(opcao)}">{html.escape(opcao)}</option>'
        for opcao in opcoes
    )

    return (
        '<td class="col-classificacao">'
        f'<select class="qa-classificacao" data-campo="{campo}" '
        f'data-teste="{html.escape(nodeid)}" '
        f'aria-label="{html.escape(titulo)}">{itens}</select>'
        "</td>"
    )


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells) -> None:
    """
    Cabeçalho: Teste antes de Status (a coluna Result, renomeada) e as
    colunas de classificação. Estas levam as opções (data-opcoes) para o
    report.js montar as listas dos testes manuais, que existem mesmo
    quando nenhum teste falhou.
    """
    if len(cells) < 2:
        return

    cells[0] = str(cells[0]).replace(">Result</th>", ">Status</th>")
    _teste_antes_do_status(cells)

    for deslocamento, (campo, titulo, opcoes) in enumerate(
        COLUNAS_DE_CLASSIFICACAO
    ):
        cells.insert(
            POSICAO_CLASSIFICACAO + deslocamento,
            f'<th class="col-classificacao" data-campo="{campo}" '
            f'data-opcoes="{html.escape(json.dumps(list(opcoes)))}">'
            f"{html.escape(titulo)}</th>",
        )


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(
    report,
    cells,
) -> None:
    """
    Troca o nodeid da coluna Teste pelo título legível do teste, põe o
    Teste antes do Status e acrescenta as colunas de classificação.
    """
    if len(cells) < 2:
        return

    cells[1] = montar_celula_teste(
        str(cells[1]),
        getattr(report, ATRIBUTO_TITULO, ""),
    )
    _teste_antes_do_status(cells)

    for deslocamento, (campo, titulo, opcoes) in enumerate(
        COLUNAS_DE_CLASSIFICACAO
    ):
        cells.insert(
            POSICAO_CLASSIFICACAO + deslocamento,
            montar_celula_classificacao(
                campo, titulo, opcoes, report.nodeid, report.failed
            ),
        )


# === Dashboard HTML ===
def _codificar_ascii_seguro(
    texto: str,
) -> str:
    """
    Converte caracteres não-ASCII em referências HTML numéricas
    (ex.: "ç" -> "&#231;").

    O pytest-html corrompe acentuação especificamente no conteúdo
    injetado via prefix.append() (confirmado comparando com o log de
    teste, que passa por json.dumps e chega correto no mesmo
    relatório). Referências numéricas são ASCII puro, então
    sobrevivem a esse pipeline independente de qual encoding a lib
    usa internamente para escrever o arquivo final.

    Seguro para o bloco de dashboard (contexto HTML, onde a
    referência é interpretada). Também aplicado ao CSS: os acentos
    ali existem só em comentários /* */, nunca em valor de
    propriedade, então a referência não interpretada fica inerte —
    só evita a mesma corrupção nos comentários.
    """
    return texto.encode(
        "ascii",
        "xmlcharrefreplace",
    ).decode("ascii")


def _codificar_js_ascii_seguro(
    texto: str,
) -> str:
    """
    Converte caracteres não-ASCII em escapes do JavaScript
    (ex.: "ç" -> "\\u00e7").

    Mesmo motivo do _codificar_ascii_seguro, mas dentro de <script> a
    referência HTML não é interpretada; o escape \\uXXXX é. Os textos
    do script usam só caracteres do plano básico (acentos do português).
    """
    return "".join(
        caractere if ord(caractere) < 128 else f"\\u{ord(caractere):04x}"
        for caractere in texto
    )


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_summary(
    prefix,
    summary,
    postfix,
    session=None,
) -> None:
    """
    Injeta o CSS e o dashboard customizado
    no relatório HTML.
    """
    logger.debug(
        "Enviando métricas para o dashboard HTML",
        extra={
            "event": "html_results_summary",
            "stats": (execution_metrics.DASHBOARD_STATS),
        },
    )

    execution_metrics.DASHBOARD_STATS["contexto"] = coletar_contexto(
        inicio=_inicio_execucao,
        fim=datetime.now(),
        usa_app=execution_metrics.execucao_usa_app(),
    )

    # make evidencias: os testes manuais previstos vão para a página.
    if session is not None and session.config.getoption(
        testes_manuais.OPCAO, default=False
    ):
        execution_metrics.DASHBOARD_STATS["testes_manuais_previstos"] = (
            testes_manuais.carregar()
        )

    inline_css, html_block = build_results_summary_html(
        PROJECT_ROOT,
        execution_metrics.DASHBOARD_STATS,
    )

    inline_css = _codificar_ascii_seguro(inline_css)
    html_block = _codificar_ascii_seguro(html_block)

    if inline_css:
        prefix.append(f"<style>{inline_css}</style>")

        logger.info(
            "CSS customizado injetado no relatório HTML",
            extra={
                "event": "html_css_injected",
                "stats": (execution_metrics.DASHBOARD_STATS),
            },
        )

    else:
        logger.warning(
            "CSS customizado não encontrado",
            extra={
                "event": "html_css_not_found",
            },
        )

    prefix.append(html_block)

    # No postfix: o script precisa vir depois dos filtros no HTML.
    inline_js = _codificar_js_ascii_seguro(load_inline_js(PROJECT_ROOT))

    if inline_js:
        postfix.append(f"<script>{inline_js}</script>")


# === Resumo da execução ===
def pytest_terminal_summary(
    terminalreporter,
    exitstatus,
    config,
) -> None:
    """
    Exibe o resumo da execução no terminal.
    """
    stats = execution_metrics.DASHBOARD_STATS
    report_path = config.option.htmlpath

    logger.debug(
        "Gerando resumo final da execução",
        extra={
            "event": "pytest_terminal_summary",
            "stats": stats,
            "report_path": report_path,
            "exitstatus": exitstatus,
        },
    )

    terminalreporter.write_sep(
        "=",
        "RESUMO",
    )
    terminalreporter.write_line(f"Total:             {stats['total']}")
    terminalreporter.write_line(f"Passou:            {stats['passed']}")
    terminalreporter.write_line(f"Falhou:            {stats['failed']}")
    terminalreporter.write_line(f"Falha na execução: {stats['error']}")
    terminalreporter.write_line(f"Pulados:           {stats['skipped']}")
    terminalreporter.write_line(f"Sucesso:           {stats['success_rate']}%")
    terminalreporter.write_line(f"Relatório:         {report_path}")

    logger.info(
        "Resumo final do dashboard",
        extra={
            "event": "dashboard_summary",
            "stats": stats,
            "report_path": report_path,
        },
    )
