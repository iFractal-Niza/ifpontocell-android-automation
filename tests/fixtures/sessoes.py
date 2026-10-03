"""
Criação e encerramento das sessões de app (Appium + AppSession) e as
fixtures de sessão por suíte.
"""

from time import perf_counter

import pytest
from selenium.common.exceptions import WebDriverException

from config.capabilities import is_emulator
from config.settings import Settings
from core.app_session import AppSession
from core.driver_factory import create_driver
from core.localizacao import (
    aplicar_localizacao_simulada,
    desfazer_localizacao_simulada,
)
from tests.support.profile_resolver import resolver_profile
from utils.logger import get_logger

logger = get_logger("fixtures.sessoes")


# === Helpers do driver ===
def _resolver_contexto_android(
    driver_instance,
    device_config: dict | None,
    settings: Settings,
) -> tuple[str, str]:
    """
    Resolve o UDID e o appPackage usados pela sessão.

    Prioridade:
    1. Capabilities retornadas pelo Appium.
    2. Configuração do devices.yaml.
    3. Variáveis do env.<device>.yaml.

    O UDID pode ficar vazio no emulador (o Appium usa o único device
    conectado); só o appPackage é obrigatório.
    """
    capabilities = driver_instance.capabilities or {}

    device = device_config or {}

    udid = str(
        capabilities.get("appium:udid")
        or capabilities.get("udid")
        or device.get("udid")
        or settings.device.udid
    ).strip()

    app_package = str(
        capabilities.get("appium:appPackage")
        or capabilities.get("appPackage")
        or settings.app.package
    ).strip()

    if not app_package:
        raise RuntimeError(
            "Não foi possível resolver o appPackage do app. "
            "Configure ANDROID_APP_PACKAGE no env.<device>.yaml."
        )

    return udid, app_package


def finalizar_driver(
    driver_instance,
    fixture_name: str,
    app_package: str,
) -> None:
    """
    Finaliza o app e a sessão Appium de forma segura.

    O emulador permanece aberto e o app permanece instalado. No celular,
    devolve o GPS de verdade antes de encerrar.
    """
    if not driver_instance:
        return

    inicio = perf_counter()

    try:
        logger.info(f"Iniciando teardown: {fixture_name}")

        if app_package:
            try:
                driver_instance.terminate_app(app_package)

                logger.info(f"App finalizado antes do quit: {fixture_name}")

            except WebDriverException:
                logger.exception(
                    f"Falha ao finalizar app antes do quit: {fixture_name}"
                )

        # Celular: a localização simulada não some com a sessão (o
        # Appium Settings segue como provedor de localização fictícia).
        if not is_emulator():
            desfazer_localizacao_simulada(driver_instance)

        driver_instance.quit()

        duracao = round(
            perf_counter() - inicio,
            2,
        )

        logger.info(f"Driver finalizado: {fixture_name} ({duracao}s)")

    except Exception:
        duracao = round(
            perf_counter() - inicio,
            2,
        )

        logger.exception(
            f"Falha ao finalizar driver: {fixture_name} ({duracao}s)"
        )


# === Criação da sessão de app ===
def criar_app_session(
    request,
    device_config: dict | None,
    cold_start: bool,
    permissions: frozenset[str] = frozenset(),
    manter_estado: bool = False,
):
    """
    Cria a sessão Appium e entrega um AppSession preparado.

    Etapas:
    1. Resolve o LaunchProfile do teste atual.
    2. Cria a sessão Appium com as capabilities do perfil.
    3. Aplica a localização simulada.
    4. Prepara a sessão (permissões já concedidas pelo
       autoGrantPermissions).

    A configuração é validada aqui, antes de abrir qualquer sessão:
    erros de formato no env.<device>.yaml aparecem todos juntos.
    """
    settings = Settings.from_env()

    profile = resolver_profile(
        request,
        cold_start=cold_start,
        permissions=permissions,
        manter_estado=manter_estado,
    )

    logger.info(
        f"Criando driver: {request.fixturename} "
        f"(cold_start={cold_start}, manter_estado={manter_estado})"
    )

    driver_instance = create_driver(
        profile=profile,
        device=device_config,
        settings=settings,
    )

    try:
        aplicar_localizacao_simulada(driver_instance, settings)

        udid, app_package = _resolver_contexto_android(
            driver_instance=driver_instance,
            device_config=device_config,
            settings=settings,
        )

        session = AppSession(
            driver=driver_instance,
            app_package=app_package,
            device_udid=udid,
            profile=profile,
        )

        session.preparar()

        return session

    except Exception:
        try:
            driver_instance.quit()

        except Exception:
            logger.exception(
                "Falha ao finalizar o driver após erro "
                "na configuração inicial da sessão"
            )

        raise


def _sessao_de_app(
    request,
    device_config: dict | None,
    cold_start: bool,
    permissions: frozenset[str] = frozenset(),
):
    """
    Generator compartilhado pelas fixtures de sessão.
    """
    session = criar_app_session(
        request=request,
        device_config=device_config,
        cold_start=cold_start,
        permissions=permissions,
    )

    try:
        yield session

    finally:
        finalizar_driver(
            session.driver,
            fixture_name=request.fixturename,
            app_package=session.app_package,
        )


# === Fixtures de sessão ===
@pytest.fixture
def app_session(request, device_config):
    """
    Sessão de app padrão, com isolamento por teste.
    """
    yield from _sessao_de_app(
        request=request,
        device_config=device_config,
        cold_start=False,
    )


@pytest.fixture(scope="module")
def app_session_home(request, device_config):
    """
    Sessão com cold start para os testes da Home.
    """
    yield from _sessao_de_app(
        request=request,
        device_config=device_config,
        cold_start=True,
    )


# === Fixtures de driver (compatibilidade) ===
# Mantidas para que os testes existentes continuem recebendo o driver
# diretamente. Testes novos devem usar as fixtures app_session_*, que
# expõem relaunch().
@pytest.fixture
def driver(app_session):
    return app_session.driver


@pytest.fixture(scope="module")
def driver_home(app_session_home):
    return app_session_home.driver
