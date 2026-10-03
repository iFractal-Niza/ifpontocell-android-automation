"""
Helpers de sessão (tests.fixtures.sessoes) que não dependem do Appium:
resolução de UDID/appPackage e o teardown defensivo.
"""

from unittest.mock import Mock

import pytest
from selenium.common.exceptions import WebDriverException

from config.settings import Settings
from tests.fixtures import sessoes

ENV = {"ANDROID_UDID": "UDID-ENV", "ANDROID_APP_PACKAGE": "pacote.env"}


def _driver(capabilities: dict | None = None) -> Mock:
    driver = Mock()
    driver.capabilities = capabilities or {}
    return driver


def _resolver(driver, device=None, env=ENV):
    return sessoes._resolver_contexto_android(
        driver_instance=driver,
        device_config=device,
        settings=Settings.from_env(env),
    )


# === Resolução de UDID e appPackage ===
def test_capabilities_do_appium_tem_prioridade():
    driver = _driver(
        {"appium:udid": "UDID-APPIUM", "appium:appPackage": "pacote.appium"}
    )

    assert _resolver(driver, device={"udid": "UDID-DEVICE"}) == (
        "UDID-APPIUM",
        "pacote.appium",
    )


def test_device_config_antes_do_env():
    assert _resolver(_driver(), device={"udid": "UDID-DEVICE"}) == (
        "UDID-DEVICE",
        "pacote.env",
    )


def test_env_como_ultimo_recurso():
    assert _resolver(_driver()) == ("UDID-ENV", "pacote.env")


def test_emulador_sem_udid_e_aceito():
    # Com um emulador só, o Appium escolhe o device conectado.
    assert _resolver(_driver(), env={}) == ("", "br.com.ifractal.Stou")


# === Teardown ===
@pytest.fixture(autouse=True)
def logger_silencioso(monkeypatch):
    monkeypatch.setattr(sessoes, "logger", Mock())


def test_teardown_encerra_app_e_sessao():
    driver = _driver()

    sessoes.finalizar_driver(driver, fixture_name="f", app_package="b")

    driver.terminate_app.assert_called_once_with("b")
    driver.quit.assert_called_once()


def test_falha_ao_encerrar_app_nao_impede_quit():
    driver = _driver()
    driver.terminate_app.side_effect = WebDriverException("app já fechado")

    sessoes.finalizar_driver(driver, fixture_name="f", app_package="b")

    driver.quit.assert_called_once()


def test_falha_no_quit_nao_propaga():
    # Teardown não pode mascarar o resultado do teste.
    driver = _driver()
    driver.quit.side_effect = WebDriverException("sessão perdida")

    sessoes.finalizar_driver(driver, fixture_name="f", app_package="b")


def test_sem_package_so_encerra_sessao():
    driver = _driver()

    sessoes.finalizar_driver(driver, fixture_name="f", app_package="")

    driver.terminate_app.assert_not_called()
    driver.quit.assert_called_once()


def test_sem_driver_nao_faz_nada():
    sessoes.finalizar_driver(None, fixture_name="f", app_package="b")
