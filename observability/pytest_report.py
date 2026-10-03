import html
import os

import pytest
from pytest_html import extras

from observability import execution_metrics
from observability.dashboard import build_results_summary_html
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
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

REPORTS_DIR = os.path.join(
    PROJECT_ROOT,
    "reports",
)

SCREENSHOTS_DIR = os.path.join(
    REPORTS_DIR,
    "screenshots",
)


# === Configuração do relatório ===
MAX_REPORTS = 10

_DRIVER_FIXTURES = (
    "driver",
    "driver_onboarding",
    "driver_login",
    "driver_unlock",
    "driver_e2e",
    "driver_registro_ponto",
    "home_para_marcacao",
)

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
            for nome_arquivo in os.listdir(
                diretorio
            )
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


def obter_driver_ativo(item):
    """
    Retorna a instância ativa do driver entre as fixtures conhecidas.

    Aceita fixtures que retornam o driver diretamente e fixtures que
    retornam uma Page (que expõe o driver em .driver), como a
    home_para_marcacao dos testes de registro de ponto.
    """
    for fixture_name in _DRIVER_FIXTURES:
        valor = item.funcargs.get(fixture_name)

        if valor is None:
            continue

        if hasattr(valor, "save_screenshot"):
            return valor

        driver_interno = getattr(valor, "driver", None)

        if driver_interno is not None:
            return driver_interno

    return None


# === Configuração do Pytest ===
def pytest_configure(
    config,
) -> None:
    """
    Configura os diretórios, o nome do relatório HTML
    e os metadados da execução.
    """
    timestamp = current_timestamp()

    garantir_estrutura_reports()

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

    if report.when == "call":
        execution_metrics.update_dashboard_stats(
            report.nodeid,
            report.outcome,
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

        _nodeids_com_erro_contabilizado.add(
            report.nodeid
        )

        execution_metrics.update_dashboard_stats(
            report.nodeid,
            "error",
        )

    elif report.skipped:
        execution_metrics.update_dashboard_stats(
            report.nodeid,
            "skipped",
        )


# === Evidências de falha ===
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item,
    call,
):
    """
    Adiciona screenshot e resumo do erro ao relatório HTML
    quando ocorre uma falha.
    """
    outcome = yield
    report = outcome.get_result()

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
        driver_instance = obter_driver_ativo(
            item
        )

        error_message = (
            execution_metrics.extract_error_message(
                report
            )
        )

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

                screenshot_saved = (
                    driver_instance.save_screenshot(
                        path
                    )
                )

                if (
                    screenshot_saved
                    and os.path.exists(path)
                ):
                    report_extras.append(
                        extras.image(path)
                    )
                    report_extras.append(
                        extras.url(
                            path,
                            name="Abrir screenshot",
                        )
                    )

                    logger.info(
                        "Screenshot anexado ao relatório",
                        extra={
                            "event": (
                                "report_screenshot_attached"
                            ),
                            "test_name": item.name,
                            "screenshot_path": path,
                            "when": report.when,
                        },
                    )

                else:
                    logger.warning(
                        "O driver não retornou um screenshot válido",
                        extra={
                            "event": (
                                "report_screenshot_not_saved"
                            ),
                            "test_name": item.name,
                            "when": report.when,
                            "screenshot_path": path,
                        },
                    )

            except Exception:
                logger.exception(
                    "Não foi possível salvar o screenshot "
                    "no relatório",
                    extra={
                        "event": (
                            "report_screenshot_failed"
                        ),
                        "test_name": item.name,
                        "when": report.when,
                    },
                )

        else:
            logger.warning(
                "Nenhum driver ativo foi encontrado "
                "para capturar o screenshot",
                extra={
                    "event": "report_driver_not_found",
                    "test_name": item.name,
                    "when": report.when,
                    "available_funcargs": list(
                        item.funcargs.keys()
                    ),
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

    report.extras = report_extras


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


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_summary(
    prefix,
    summary,
    postfix,
) -> None:
    """
    Injeta o CSS e o dashboard customizado
    no relatório HTML.
    """
    logger.debug(
        "Enviando métricas para o dashboard HTML",
        extra={
            "event": "html_results_summary",
            "stats": (
                execution_metrics.DASHBOARD_STATS
            ),
        },
    )

    inline_css, html_block = (
        build_results_summary_html(
            PROJECT_ROOT,
            execution_metrics.DASHBOARD_STATS,
        )
    )

    inline_css = _codificar_ascii_seguro(
        inline_css
    )
    html_block = _codificar_ascii_seguro(
        html_block
    )

    if inline_css:
        prefix.append(
            f"<style>{inline_css}</style>"
        )

        logger.info(
            "CSS customizado injetado no relatório HTML",
            extra={
                "event": "html_css_injected",
                "stats": (
                    execution_metrics
                    .DASHBOARD_STATS
                ),
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
    terminalreporter.write_line(
        f"Total:             {stats['total']}"
    )
    terminalreporter.write_line(
        f"Passou:            {stats['passed']}"
    )
    terminalreporter.write_line(
        f"Falhou:            {stats['failed']}"
    )
    terminalreporter.write_line(
        f"Falha na execução: {stats['error']}"
    )
    terminalreporter.write_line(
        f"Pulados:           {stats['skipped']}"
    )
    terminalreporter.write_line(
        f"Sucesso:           "
        f"{stats['success_rate']}%"
    )
    terminalreporter.write_line(
        f"Relatório:         {report_path}"
    )

    logger.info(
        "Resumo final do dashboard",
        extra={
            "event": "dashboard_summary",
            "stats": stats,
            "report_path": report_path,
        },
    )