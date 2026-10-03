import os
from collections.abc import Iterator

import pytest

from pages.onboarding_page import OnboardingPage
from tests.support.assertions import (
    validar_avanco_para_login_apos_correcao,
    validar_popup_sistema_nao_encontrado,
)
from tests.support.flows import (
    acessar_tela_login,
    abrir_tela_configurar_aplicativo,
)


# === Ciclo de vida do app no módulo ===
@pytest.fixture(autouse=True)
def reiniciar_app_entre_cenarios(driver_onboarding) -> Iterator[None]:
    """Reabre o app Android antes do cenário e encerra ao final."""
    app_package = os.getenv(
        "ANDROID_APP_PACKAGE",
        "br.com.ifractal.Stou",
    ).strip()

    try:
        driver_onboarding.activate_app(app_package)
    except Exception:
        pass

    yield

    try:
        driver_onboarding.terminate_app(app_package)
    except Exception:
        pass


# === Helpers dos cenários ===
def _informar_sistema_invalido(
    driver,
    sistema_invalido: str,
    mensagem_esperada: str,
) -> OnboardingPage:
    """
    Informa um sistema inválido e valida o popup apresentado.
    """
    onboarding_page = abrir_tela_configurar_aplicativo(driver)

    onboarding_page.informar_nome_sistema_e_avancar(
        sistema_invalido,
    )

    validar_popup_sistema_nao_encontrado(
        onboarding_page=onboarding_page,
        mensagem_esperada=mensagem_esperada,
    )

    return onboarding_page


# === Onboarding: sistema inválido ===
@pytest.mark.regression
def test_sistema_invalido(
    driver_onboarding,
    test_data,
):
    """
    Valida a exibição do popup ao informar um sistema inválido.

    Fronteira: Onboarding -> permanece em Onboarding.
    """
    _informar_sistema_invalido(
        driver=driver_onboarding,
        sistema_invalido=test_data["APP_SISTEMA_INVALIDO"],
        mensagem_esperada=test_data["MSG_SISTEMA_INVALIDO"],
    )


# === Onboarding: sistema válido ===
@pytest.mark.smoke
def test_sistema_valido(
    driver_login,
    app_system,
):
    """
    Valida o avanço para o login ao informar um sistema válido.

    Fronteira: Onboarding -> Login.
    """
    login_page = acessar_tela_login(
        driver=driver_login,
        nome_sistema=app_system,
    )

    assert login_page.validar_tela_login(), (
        "A tela de login não foi exibida após informar "
        "um sistema válido."
    )


# === Onboarding: correção do sistema ===
@pytest.mark.smoke
def test_sistema_corrigido(
    driver_login,
    app_system,
    test_data,
):
    """
    Valida a correção do sistema após uma tentativa inválida.

    Fronteira: Onboarding -> Login.
    """
    onboarding_page = _informar_sistema_invalido(
        driver=driver_login,
        sistema_invalido=test_data["APP_SISTEMA_INVALIDO"],
        mensagem_esperada=test_data["MSG_SISTEMA_INVALIDO"],
    )

    onboarding_page.corrigir_nome_sistema_e_avancar(
        app_system,
    )

    validar_avanco_para_login_apos_correcao(
        driver=driver_login,
        onboarding_page=onboarding_page,
    )