from collections import defaultdict

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
        "por_fluxo": defaultdict(
            lambda: {
                "ok": 0,
                "fail": 0,
                "error": 0,
                "skip": 0,
            }
        ),
    }


# === Métricas globais ===
DASHBOARD_STATS = _new_stats_dict()

_FLUXO_KEYWORDS = [
    ("login", "login"),
    ("onboarding", "onboarding"),
    ("unlock", "unlock"),
    ("home", "home"),
    ("e2e", "e2e"),
    ("bloqueio", "integration"),
    ("autorizacao", "integration"),
]


# === Identificação do fluxo ===
def extract_fluxo(
    nodeid: str,
) -> str:
    """
    Identifica o fluxo do teste com base em seu nodeid.

    Retorna "outros" quando nenhuma palavra-chave conhecida
    é encontrada.
    """
    nome = nodeid.lower()

    for keyword, fluxo in _FLUXO_KEYWORDS:
        if keyword in nome:
            return fluxo

    return "outros"


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

    lines = [
        line.strip()
        for line in longrepr.splitlines()
        if line.strip()
    ]

    if not lines:
        return "Falha sem detalhes disponíveis."

    for line in reversed(lines):
        if "E   " in line:
            return line.replace(
                "E   ",
                "",
            ).strip()

    return lines[-1][:500]


# === Controle das métricas ===
def reset_dashboard_stats() -> None:
    """
    Reinicia as métricas globais sem substituir sua referência.
    """
    DASHBOARD_STATS.clear()
    DASHBOARD_STATS.update(
        _new_stats_dict()
    )

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
) -> None:
    """
    Atualiza as métricas gerais e por fluxo após cada teste.
    """
    fluxo = extract_fluxo(
        nodeid
    )

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

    elif outcome == "skipped":
        DASHBOARD_STATS["skipped"] += 1
        DASHBOARD_STATS["por_fluxo"][fluxo]["skip"] += 1

    total = (
        DASHBOARD_STATS["passed"]
        + DASHBOARD_STATS["failed"]
        + DASHBOARD_STATS["error"]
        + DASHBOARD_STATS["skipped"]
    )

    DASHBOARD_STATS["total"] = total
    DASHBOARD_STATS["success_rate"] = (
        round(
            DASHBOARD_STATS["passed"]
            / total
            * 100,
            2,
        )
        if total
        else 0.0
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
            "success_rate": DASHBOARD_STATS[
                "success_rate"
            ],
        },
    )