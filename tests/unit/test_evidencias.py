"""
Registro de evidências sob demanda (observability.evidencias).
"""

from unittest.mock import Mock

import pytest
from selenium.common.exceptions import WebDriverException

from observability import evidencias

NODEID = "tests/app/test_x.py::test_y"


@pytest.fixture(autouse=True)
def isolar(monkeypatch, tmp_path):
    monkeypatch.setattr(evidencias, "SCREENSHOTS_DIR", str(tmp_path))
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


def test_evidencia_fica_associada_ao_teste_em_execucao(tmp_path):
    caminho = evidencias.capturar_evidencia(_driver(), "lista sem pendentes")

    assert caminho.startswith(str(tmp_path))
    assert evidencias.retirar_evidencias(NODEID) == [
        (caminho, "lista sem pendentes")
    ]


def test_retirar_limpa_o_registro():
    evidencias.capturar_evidencia(_driver(), "a")

    evidencias.retirar_evidencias(NODEID)

    assert evidencias.retirar_evidencias(NODEID) == []


def test_varias_evidencias_nao_se_sobrescrevem():
    primeira = evidencias.capturar_evidencia(_driver(), "a")
    segunda = evidencias.capturar_evidencia(_driver(), "b")

    assert primeira != segunda
    assert len(evidencias.retirar_evidencias(NODEID)) == 2


def test_falha_no_print_nao_derruba_o_teste():
    driver = _driver()
    driver.save_screenshot.side_effect = WebDriverException("sessão perdida")

    assert evidencias.capturar_evidencia(driver, "x") is None
    assert evidencias.retirar_evidencias(NODEID) == []


def test_print_nao_salvo_nao_e_registrado():
    assert evidencias.capturar_evidencia(_driver(salva=False), "x") is None
    assert evidencias.retirar_evidencias(NODEID) == []
