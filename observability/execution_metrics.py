from collections import defaultdict

from qa_report.dashboard import calcular_taxa_sucesso

from utils.logger import get_logger

logger = get_logger("execution_metrics")


# === Estrutura das métricas ===
def _new_stats_dict() -> dict:
    """
    Retorna a estrutura padrão das métricas exibidas no dashboard.
    """
    return {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "success_rate": 0.0,
        # Falhas e erros de testes do smoke: decidem o CRÍTICO.
        "criticas": 0,
        # Um item por teste pulado: nodeid, título, fluxo e motivo.
        "pulados": [],
        # Tempo de cada teste somando as fases (preparação, chamada e
        # finalização): {nodeid: {"titulo", "fluxo", "segundos"}}.
        "duracoes": {},
        # Pares (rótulo, valor) da identificação da execução; preenchido
        # pelo plugin ao gerar o report (observability.contexto_execucao).
        "contexto": [],
        # Testes manuais previstos (observability.testes_manuais); só no
        # make evidencias, preenchido pelo plugin ao gerar o report.
        "testes_manuais_previstos": [],
        "por_fluxo": defaultdict(
            lambda: {
                "ok": 0,
                "fail": 0,
                "error": 0,
                "skip": 0,
                "critico": 0,
                "duration": 0.0,
            }
        ),
    }


# === Métricas globais ===
DASHBOARD_STATS = _new_stats_dict()

# Testes do smoke que falharam (contados uma vez cada em "criticas").
_nodeids_criticos: set[str] = set()

# Nome do fluxo por arquivo de teste. Arquivo fora da lista usa o próprio
# nome (test_ferias.py -> "ferias"): tela nova já ganha a sua linha no
# dashboard, sem cair em "outros".
_FLUXO_POR_ARQUIVO = {
    "test_e2e": "jornada e2e",
    "test_registro_sem_foto": "registro de ponto",
    "test_ponto": "tela ponto",
    "test_status": "status das marcações",
    "test_registro_geo": "registro com geo delimitação",
    "test_informe_rendimentos": "informe de rendimentos",
    "test_estado_humor": "estado de humor",
    "test_ass_espelho": "assinatura do espelho",
    "test_sobre_aplicativo": "sobre o aplicativo",
    "test_dados_pessoais": "dados pessoais",
    "test_privacidade": "privacidade",
    "test_alterar_pin": "alterar pin",
    "test_alterar_senha_sistema": "alterar senha do sistema",
    "test_zerar_dados": "zerar dados",
}

# Pastas em que o fluxo é a pasta, não cada arquivo.
_FLUXO_POR_PASTA = {
    "api": "api",
    "unit": "unitários",
}


# === Identificação do fluxo ===
def extract_fluxo(
    nodeid: str,
) -> str:
    """
    Identifica o fluxo do teste pelo arquivo em que ele está.

    O nome do teste não entra na conta: test_primeiro_acesso_home_e_
    lembrete é da jornada e2e, não de um fluxo "home".

    Retorna "outros" quando o nodeid não tem arquivo reconhecível.
    """
    caminho = nodeid.split("::", 1)[0].replace("\\", "/")
    partes = caminho.split("/")
    arquivo = partes[-1].removesuffix(".py").lower()

    if len(partes) > 1 and partes[-2].lower() in _FLUXO_POR_PASTA:
        return _FLUXO_POR_PASTA[partes[-2].lower()]

    if arquivo in _FLUXO_POR_ARQUIVO:
        return _FLUXO_POR_ARQUIVO[arquivo]

    nome = arquivo.removeprefix("test_").replace("_", " ").strip()

    return nome or "outros"


def execucao_usa_app() -> bool:
    """
    True se algum teste da execução usa o app (não é só API/unitário).
    """
    sem_app = set(_FLUXO_POR_PASTA.values())

    return any(fluxo not in sem_app for fluxo in DASHBOARD_STATS["por_fluxo"])


# === Título legível ===
def extract_titulo(
    nodeid: str,
    docstring: str | None = None,
) -> str:
    """
    Nome do teste para quem não é do time de automação.

    Usa o primeiro parágrafo do docstring do teste; sem docstring, o
    nome da função sem o prefixo test_. O parâmetro de um teste
    parametrizado ("[caso]") é mantido no fim.
    """
    nome = nodeid.split("::")[-1]
    funcao, _, parametro = nome.partition("[")
    sufixo = f" [{parametro}" if parametro else ""

    paragrafo = (docstring or "").strip().split("\n\n", 1)[0]
    titulo = " ".join(paragrafo.split()).rstrip(".")

    if not titulo:
        titulo = funcao.removeprefix("test_").replace("_", " ").capitalize()

    return f"{titulo}{sufixo}"


# === Motivo do pulo ===
def extract_skip_reason(
    report,
) -> str:
    """
    Extrai o motivo informado em pytest.skip / mark.skip / xfail.
    """
    falha_esperada = getattr(report, "wasxfail", None)

    if falha_esperada is not None:
        return f"Falha esperada: {falha_esperada}".rstrip(": ")

    longrepr = getattr(report, "longrepr", None)

    # Em skip, o pytest entrega (arquivo, linha, "Skipped: motivo").
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        motivo = str(longrepr[2])
    else:
        motivo = str(longrepr or "")

    return motivo.removeprefix("Skipped: ").strip() or "Motivo não informado."


# === Extração de falhas ===
def extract_error_message(
    report,
) -> str:
    """
    Extrai a mensagem mais relevante do relatório gerado pelo Pytest.

    Prioriza linhas identificadas como erro pelo traceback e limita
    a mensagem alternativa a 500 caracteres.
    """
    longrepr = (
        getattr(
            report,
            "longreprtext",
            "",
        )
        or ""
    )

    if not longrepr:
        return "Falha sem detalhes disponíveis."

    lines = [line.strip() for line in longrepr.splitlines() if line.strip()]

    if not lines:
        return "Falha sem detalhes disponíveis."

    for line in reversed(lines):
        if "E   " in line:
            return line.replace(
                "E   ",
                "",
            ).strip()

    return lines[-1][:500]


# === Duração ===
def registrar_duracao(
    nodeid: str,
    segundos: float,
    titulo: str = "",
) -> None:
    """
    Soma o tempo de uma fase do teste ao teste e ao seu fluxo.

    A preparação entra na conta: é tempo que a execução gasta com o
    teste (ex.: relançar o app ou refazer o primeiro acesso).
    """
    segundos = max(0.0, float(segundos or 0))
    fluxo = extract_fluxo(nodeid)

    duracao = DASHBOARD_STATS["duracoes"].setdefault(
        nodeid,
        {
            "titulo": titulo or extract_titulo(nodeid),
            "fluxo": fluxo,
            "segundos": 0.0,
        },
    )
    duracao["segundos"] += segundos
    DASHBOARD_STATS["por_fluxo"][fluxo]["duration"] += segundos


# === Controle das métricas ===
def reset_dashboard_stats() -> None:
    """
    Reinicia as métricas globais sem substituir sua referência.
    """
    DASHBOARD_STATS.clear()
    DASHBOARD_STATS.update(_new_stats_dict())
    _nodeids_criticos.clear()

    logger.debug(
        "Métricas do dashboard reiniciadas",
        extra={
            "event": "dashboard_stats_reset",
            "stats": dict(DASHBOARD_STATS),
        },
    )


def update_dashboard_stats(
    nodeid: str,
    outcome: str,
    motivo: str = "",
    titulo: str = "",
    smoke: bool = False,
) -> None:
    """
    Atualiza as métricas gerais e por fluxo após cada teste.

    'motivo' só é usado quando o teste foi pulado (lista de ressalvas);
    'titulo' vai para as ressalvas; 'smoke' marca a
    falha ou o erro como crítico.
    """
    fluxo = extract_fluxo(nodeid)

    logger.debug(
        "Iniciando atualização das métricas do dashboard",
        extra={
            "event": "dashboard_stats_update",
            "nodeid": nodeid,
            "outcome": outcome,
            "fluxo": fluxo,
        },
    )

    if outcome == "passed":
        DASHBOARD_STATS["passed"] += 1
        DASHBOARD_STATS["por_fluxo"][fluxo]["ok"] += 1

    elif outcome == "failed":
        DASHBOARD_STATS["failed"] += 1
        DASHBOARD_STATS["por_fluxo"][fluxo]["fail"] += 1

    elif outcome == "error":
        DASHBOARD_STATS["error"] += 1
        DASHBOARD_STATS["por_fluxo"][fluxo]["error"] += 1

    # Uma vez por teste: falhar na chamada e quebrar no teardown não
    # conta dois testes do smoke.
    if (
        smoke
        and outcome in ("failed", "error")
        and nodeid not in _nodeids_criticos
    ):
        _nodeids_criticos.add(nodeid)
        DASHBOARD_STATS["criticas"] += 1
        DASHBOARD_STATS["por_fluxo"][fluxo]["critico"] += 1

    if outcome == "skipped":
        DASHBOARD_STATS["skipped"] += 1
        DASHBOARD_STATS["por_fluxo"][fluxo]["skip"] += 1
        DASHBOARD_STATS["pulados"].append(
            {
                "nodeid": nodeid,
                "titulo": titulo or extract_titulo(nodeid),
                "fluxo": fluxo,
                "motivo": motivo or "Motivo não informado.",
            }
        )

    total = (
        DASHBOARD_STATS["passed"]
        + DASHBOARD_STATS["failed"]
        + DASHBOARD_STATS["error"]
        + DASHBOARD_STATS["skipped"]
    )

    DASHBOARD_STATS["total"] = total
    DASHBOARD_STATS["success_rate"] = calcular_taxa_sucesso(
        DASHBOARD_STATS["passed"],
        DASHBOARD_STATS["failed"],
        DASHBOARD_STATS["error"],
    )

    logger.debug(
        "Métricas do dashboard atualizadas",
        extra={
            "event": "dashboard_stats_updated",
            "total": DASHBOARD_STATS["total"],
            "passed": DASHBOARD_STATS["passed"],
            "failed": DASHBOARD_STATS["failed"],
            "error": DASHBOARD_STATS["error"],
            "skipped": DASHBOARD_STATS["skipped"],
            "success_rate": DASHBOARD_STATS["success_rate"],
        },
    )
