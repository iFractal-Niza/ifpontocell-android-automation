"""
Localização simulada no emulador e no celular (driver.set_location do
UiAutomator2; no celular, pelo app Appium Settings como provedor de
localização fictícia).

A interpretação do env.<device>.yaml (flag, coordenadas, limites) é do
config.settings.Settings; aqui só se aplica o resultado ao driver.
"""

from selenium.common.exceptions import WebDriverException

from config.settings import Localizacao, Settings
from utils.logger import get_logger

logger = get_logger("localizacao")


def aplicar_localizacao_simulada(driver, settings: Settings) -> None:
    """
    Aplica a localização configurada no env.<device>.yaml (emulador ou
    celular). Ignorada com ANDROID_LOCATION_ENABLED desligado.

    Aplicada na criação da sessão. Para trocar de coordenada no meio
    de um teste (ex.: dentro e fora da geo delimitação), use
    definir_localizacao(). No celular, a sessão desfaz ao terminar
    (desfazer_localizacao_simulada): senão o aparelho segue com ela.
    """
    localizacao = settings.localizacao

    if localizacao is None:
        # Coordenadas preenchidas com a flag desligada quase sempre é
        # esquecimento: sem o aviso, o teste roda sem localização e
        # nada indica o motivo.
        if settings.localizacao_desligada_com_coordenadas:
            logger.warning(
                "Localização simulada desabilitada, mas "
                "ANDROID_LOCATION_LATITUDE/ANDROID_LOCATION_LONGITUDE estão "
                "preenchidas no env.<device>.yaml. Defina "
                'ANDROID_LOCATION_ENABLED: "true" para aplicá-las.'
            )
        else:
            logger.info("Localização simulada desabilitada")
        return

    definir_localizacao(driver, localizacao)


def definir_localizacao(driver, localizacao: Localizacao) -> None:
    """
    Define a localização simulada agora, com a sessão aberta.
    """
    try:
        driver.set_location(localizacao.latitude, localizacao.longitude, 0)

    except WebDriverException as error:
        raise RuntimeError(
            "Não foi possível aplicar a localização simulada. No celular, "
            "confira em Opções do desenvolvedor se o app de localização "
            "fictícia é o Appium Settings; no emulador, se o UiAutomator2 "
            "Driver está atualizado."
        ) from error

    logger.info(
        "Localização simulada aplicada: "
        f"latitude={localizacao.latitude}, "
        f"longitude={localizacao.longitude}"
    )


def desfazer_localizacao_simulada(driver) -> None:
    """
    Celular: devolve o GPS de verdade. Não derruba o encerramento se
    falhar (só avisa).
    """
    try:
        driver.execute_script("mobile: resetGeolocation", {})
    except WebDriverException as error:
        logger.warning(
            "Não foi possível desfazer a localização simulada no celular; "
            "desligue o app de localização fictícia nas Opções do "
            f"desenvolvedor: {error.msg}"
        )
        return

    logger.info("Localização simulada desfeita: GPS de verdade de volta")
