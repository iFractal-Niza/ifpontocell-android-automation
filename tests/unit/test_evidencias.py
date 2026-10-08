"""
Print das evidências pelo driver do Appium (observability.automacao).
O registro das evidências é do pacote ifponto-observability (testado lá).
"""

from unittest.mock import Mock

import pytest
from qa_observability import evidencias
from selenium.common.exceptions import WebDriverException

NODEID = "tests/app/test_x.py::test_y"


@pytest.fixture(autouse=True)
def isolar(monkeypatch, tmp_path):
    monkeypatch.setattr(
        evidencias.pastas, "screenshots_dir", lambda: str(tmp_path)
    )
    monkeypatch.setattr(evidencias, "logger", Mock())
    # O pytest reescreve PYTEST_CURRENT_TEST a cada fase do próprio teste
    # unitário; fixa o nodeid substituindo a leitura.
    monkeypatch.setattr(evidencias, "_nodeid_atual", lambda: NODEID)
    evidencias._evidencias.clear()
    yield
    evidencias._evidencias.clear()


def _driver(salva: bool = True) -> Mock:
    driver = Mock()
    driver.save_screenshot.return_value = salva
    return driver


def test_evidencia_e_salva_pelo_driver(tmp_path):
    driver = _driver()

    caminho = evidencias.capturar_evidencia(driver, "lista sem pendentes")

    assert caminho.startswith(str(tmp_path))
    driver.save_screenshot.assert_called_once_with(caminho)
    assert evidencias.retirar_evidencias(NODEID) == [
        (caminho, "lista sem pendentes")
    ]


def test_falha_no_print_nao_derruba_o_teste():
    driver = _driver()
    driver.save_screenshot.side_effect = WebDriverException("sessão perdida")

    assert evidencias.capturar_evidencia(driver, "x") is None
    assert evidencias.retirar_evidencias(NODEID) == []


def test_print_nao_salvo_nao_e_registrado():
    assert evidencias.capturar_evidencia(_driver(salva=False), "x") is None
    assert evidencias.retirar_evidencias(NODEID) == []
