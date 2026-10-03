"""
Aplicação da localização simulada no driver (core.localizacao). A
validação das coordenadas é do Settings: ver test_settings.py.
"""

from unittest.mock import Mock

import pytest
from selenium.common.exceptions import WebDriverException

from config.settings import Localizacao, Settings
from core import localizacao


@pytest.fixture
def driver():
    return Mock()


@pytest.fixture
def logger(monkeypatch):
    # O logger do projeto não propaga para o caplog (propagate=False).
    falso = Mock()
    monkeypatch.setattr(localizacao, "logger", falso)
    return falso


@pytest.fixture
def emulador(ambiente):
    ambiente["ANDROID_TARGET"] = "emulator"
    return ambiente


def _aplicar(driver):
    localizacao.aplicar_localizacao_simulada(driver, Settings.from_env())


def test_habilitada_aplica_coordenadas_como_float(emulador, driver, logger):
    emulador["ANDROID_LOCATION_ENABLED"] = "true"
    emulador["ANDROID_LOCATION_LATITUDE"] = "-23.6167"
    emulador["ANDROID_LOCATION_LONGITUDE"] = "-46.6372"

    _aplicar(driver)

    driver.set_location.assert_called_once_with(-23.6167, -46.6372, 0)


def test_desabilitada_sem_coordenadas_so_informa(emulador, driver, logger):
    emulador["ANDROID_LOCATION_ENABLED"] = "false"

    _aplicar(driver)

    driver.set_location.assert_not_called()
    logger.warning.assert_not_called()


def test_desabilitada_com_coordenadas_avisa(emulador, driver, logger):
    # Caso real (iOS): coordenadas preenchidas e a flag esquecida em false.
    emulador["ANDROID_LOCATION_ENABLED"] = "false"
    emulador["ANDROID_LOCATION_LATITUDE"] = "-23.6167"
    emulador["ANDROID_LOCATION_LONGITUDE"] = "-46.6372"

    _aplicar(driver)

    driver.set_location.assert_not_called()
    logger.warning.assert_called_once()


def test_device_real_tambem_aplica(ambiente, driver, logger):
    # No celular, sem a localização simulada, vale o GPS de verdade:
    # fora da geo do usuário, o registro de ponto avisa e o teste falha.
    ambiente.update(
        {
            "ANDROID_TARGET": "real",
            "ANDROID_UDID": "R58N12ABCDE",
            "APP_SOURCE": "package",
            "ANDROID_LOCATION_ENABLED": "true",
            "ANDROID_LOCATION_LATITUDE": "-23.6167",
            "ANDROID_LOCATION_LONGITUDE": "-46.6372",
        }
    )

    _aplicar(driver)

    driver.set_location.assert_called_once_with(-23.6167, -46.6372, 0)


def test_desfazer_devolve_o_gps_de_verdade(driver, logger):
    localizacao.desfazer_localizacao_simulada(driver)

    driver.execute_script.assert_called_once_with(
        "mobile: resetGeolocation", {}
    )


def test_desfazer_com_erro_so_avisa(driver, logger):
    # No encerramento da sessão: não pode derrubar o teardown.
    driver.execute_script.side_effect = WebDriverException("sem suporte")

    localizacao.desfazer_localizacao_simulada(driver)

    logger.warning.assert_called_once()


def test_falha_do_driver_vira_erro_explicativo(emulador, driver, logger):
    emulador["ANDROID_LOCATION_ENABLED"] = "true"
    emulador["ANDROID_LOCATION_LATITUDE"] = "0"
    emulador["ANDROID_LOCATION_LONGITUDE"] = "0"
    driver.set_location.side_effect = WebDriverException("sem suporte")

    with pytest.raises(RuntimeError, match="Appium Settings"):
        _aplicar(driver)


def test_definir_localizacao_no_meio_da_sessao(driver, logger):
    # Usado pelos testes de geo delimitação para ir de dentro para fora
    # da área com a sessão aberta.
    localizacao.definir_localizacao(
        driver, Localizacao(latitude=-22.9068, longitude=-43.1729)
    )

    driver.set_location.assert_called_once_with(-22.9068, -43.1729, 0)
