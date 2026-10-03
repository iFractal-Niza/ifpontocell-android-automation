"""
Evidências sob demanda: prints tirados pelo próprio teste num momento
escolhido, anexados ao report qualquer que seja o resultado (aprovado,
pulado ou reprovado).

Uso típico: antes de pular por falta de massa, registrar a tela que
motivou o skip (ex.: lista com todos os espelhos assinados) — o print
automático do report só existe em falha e, no skip, a tela já teria
voltado para a Home.
"""

import os

from selenium.common.exceptions import WebDriverException

from observability import pastas
from utils.file_utils import build_screenshot_path
from utils.logger import get_logger

logger = get_logger("evidencias")

SCREENSHOTS_DIR = os.path.join(pastas.REPORTS_DIR, "screenshots")

# nodeid do teste -> [(caminho do print, descrição)]
_evidencias: dict[str, list[tuple[str, str]]] = {}


def _nodeid_atual() -> str:
    # O pytest mantém "caminho::teste (call)" durante a execução.
    atual = os.environ.get("PYTEST_CURRENT_TEST", "")
    return atual.rsplit(" (", 1)[0]


def capturar_evidencia(driver, descricao: str) -> str | None:
    """
    Tira um print da tela atual e o associa ao teste em execução.

    Retorna o caminho do arquivo, ou None se não foi possível capturar
    (a falha na evidência nunca derruba o teste).
    """
    nodeid = _nodeid_atual()
    registradas = _evidencias.setdefault(nodeid, [])
    nome_teste = nodeid.split("::")[-1] or "evidencia"

    caminho = build_screenshot_path(
        SCREENSHOTS_DIR,
        nome_teste,
        context=f"evidencia_{len(registradas) + 1}",
    )

    try:
        salvo = driver.save_screenshot(caminho)
    except WebDriverException:
        logger.exception(
            "Não foi possível capturar a evidência",
            extra={"event": "evidence_capture_failed", "descricao": descricao},
        )
        return None

    if not salvo:
        return None

    registradas.append((caminho, descricao))

    logger.info(
        f"Evidência capturada: {descricao}",
        extra={"event": "evidence_captured", "path": caminho},
    )

    return caminho


def retirar_evidencias(nodeid: str) -> list[tuple[str, str]]:
    """Evidências registradas para o teste (e as remove do registro)."""
    return _evidencias.pop(nodeid, [])
