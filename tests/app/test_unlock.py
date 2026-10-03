"""
Unlock: confirmação divergente na criação do PIN.

Elo da corrente do primeiro acesso (Onboarding -> Login -> Unlock ->
E2E), na sessão compartilhada: continua da criação do PIN deixada pelo
CT005 e termina na Home com o lembrete do primeiro acesso na tela, para
o CT007. Rodando sozinho, leva o app até a criação do PIN antes.
"""

import pytest

from pages.home_page import HomePage
from tests.support.flows import (
    concluir_primeiro_acesso,
    levar_a_criacao_do_pin,
)

pytestmark = [pytest.mark.primeiro_acesso, pytest.mark.exibir_lembrete]


@pytest.mark.ct("CT006")
# === Unlock: confirmação divergente ===
@pytest.mark.regression
def test_pin_divergente_reinicia_criacao(
    app_session_e2e_registro_ponto,
    _credenciais_app,
    celular_api,
    monitor_nome_pessoa,
    estado_primeiro_acesso,
    app_pin,
    test_data,
):
    """
    Valida que confirmar um PIN diferente do criado reinicia a criação
    do PIN.

    Confirmação com PIN diferente do criado faz o app voltar para a
    criação do PIN; criando e confirmando o PIN certo, chega à Home.

    Fronteira:
    criação do PIN -> confirmação divergente -> criação do PIN ->
    ativação pela API (emulador) -> criação e confirmação corretas ->
    Home com o lembrete do primeiro acesso (fica para o CT007).

    O app não exibe mensagem de erro na divergência: o sinal é a volta
    para "Crie uma senha de 4 dígitos".
    """
    driver = app_session_e2e_registro_ponto.driver
    pin_invalido = test_data["APP_PIN_INVALIDO"]

    assert pin_invalido != app_pin, (
        "APP_PIN_INVALIDO (test_data.yaml) precisa ser diferente de "
        "APP_PIN (env.<device>.yaml) para o cenário de confirmação divergente."
    )

    unlock_page = levar_a_criacao_do_pin(
        driver,
        _credenciais_app,
        celular_api,
        monitor_nome_pessoa,
        estado_primeiro_acesso,
    )

    assert unlock_page.validar_tela_criar_pin(), (
        "A tela de criação do PIN não foi exibida."
    )

    unlock_page.criar_pin(app_pin)
    unlock_page.confirmar_pin(pin_invalido)

    assert unlock_page.esta_na_tela_criar_pin(
        timeout=unlock_page.LONG_TIMEOUT,
    ), (
        "Com a confirmação divergente, o app deveria voltar para a "
        "criação do PIN ('Crie uma senha de 4 dígitos')."
    )

    # Sem tratar os popups: o lembrete do primeiro acesso fica na tela
    # para o CT007 (realizar_unlock já confere que chegou à Home ou ao
    # lembrete).
    concluir_primeiro_acesso(
        driver,
        _credenciais_app,
        celular_api,
        monitor_nome_pessoa,
        estado_primeiro_acesso,
        tratar_popups_home=False,
    )

    home_page = HomePage(driver)

    assert home_page.popup_lembrete_esta_visivel(
        timeout=home_page.SHORT_TIMEOUT
    ) or home_page.esta_na_home(timeout=home_page.SHORT_TIMEOUT), (
        "A Home não foi exibida após criar e confirmar o PIN correto "
        "depois da tentativa divergente."
    )
