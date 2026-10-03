"""
Onboarding: sistema inválido e a correção até o login.

Primeiro elo da corrente do primeiro acesso (Onboarding -> Login ->
Unlock -> E2E), na sessão compartilhada da suíte: quem cria a sessão
sobe o app limpo (primeiro_acesso) e com o lembrete do primeiro acesso
liberado para o E2E (exibir_lembrete). Rodando sozinho, ou com o app
logado (APP_SOURCE=package, que não reinstala), o teste leva o app de volta ao
onboarding zerando os dados pelo próprio app.
"""

import pytest

from pages.autenticacao.onboarding_page import OnboardingPage
from tests.support.assertions import (
    validar_avanco_para_login_apos_correcao,
    validar_popup_sistema_nao_encontrado,
)
from tests.support.flows import (
    abrir_tela_configurar_aplicativo,
    levar_ao_onboarding,
)

pytestmark = [pytest.mark.primeiro_acesso, pytest.mark.exibir_lembrete]


# === Encadeamento ===
# O CT001 termina na tela "Configurar Aplicativo" com o popup fechado, e
# a correção continua dali. Sozinha (make smoke, --ct), ou se o CT001
# parou no meio, a correção refaz o passo inválido por conta própria.
@pytest.fixture(scope="module")
def estado_onboarding() -> dict:
    return {"configurar_aberta": False}


@pytest.fixture
def ir_ao_onboarding(
    app_session_e2e_registro_ponto,
    _credenciais_app,
    celular_api,
    monitor_nome_pessoa,
    estado_primeiro_acesso,
):
    def ir() -> None:
        levar_ao_onboarding(
            app_session_e2e_registro_ponto.driver,
            _credenciais_app,
            celular_api,
            monitor_nome_pessoa,
            estado_primeiro_acesso,
        )

    return ir


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


@pytest.mark.ct("CT001")
# === Onboarding: sistema inválido ===
@pytest.mark.regression
def test_sistema_invalido(
    app_session_e2e_registro_ponto,
    ir_ao_onboarding,
    estado_onboarding,
    test_data,
):
    """
    Valida a exibição do popup de erro ao informar um sistema inválido.

    Fronteira: Onboarding -> permanece em Onboarding.
    """
    ir_ao_onboarding()

    _informar_sistema_invalido(
        driver=app_session_e2e_registro_ponto.driver,
        sistema_invalido=test_data["APP_SISTEMA_INVALIDO"],
        mensagem_esperada=test_data["MSG_SISTEMA_INVALIDO"],
    )

    estado_onboarding["configurar_aberta"] = True


@pytest.mark.ct("CT002")
# === Onboarding: correção do sistema ===
@pytest.mark.smoke
def test_sistema_corrigido(
    app_session_e2e_registro_ponto,
    ir_ao_onboarding,
    estado_onboarding,
    app_system,
    test_data,
):
    """
    Valida a correção do sistema após uma tentativa inválida e o avanço
    para o login.

    Continua da tela em que o CT001 parou; sozinho, faz antes o passo
    inválido. Também cobre o sistema válido: a correção é informar o
    sistema certo e avançar. Termina no login (o CT003 continua dali).

    Fronteira: Onboarding -> Login.
    """
    driver = app_session_e2e_registro_ponto.driver

    if estado_onboarding["configurar_aberta"]:
        onboarding_page = OnboardingPage(driver)
    else:
        ir_ao_onboarding()

        onboarding_page = _informar_sistema_invalido(
            driver=driver,
            sistema_invalido=test_data["APP_SISTEMA_INVALIDO"],
            mensagem_esperada=test_data["MSG_SISTEMA_INVALIDO"],
        )

    estado_onboarding["configurar_aberta"] = False

    onboarding_page.corrigir_nome_sistema_e_avancar(
        app_system,
    )

    validar_avanco_para_login_apos_correcao(
        driver=driver,
        onboarding_page=onboarding_page,
    )
