"""
Login: negativos e o login válido até a criação do PIN.

Elo da corrente do primeiro acesso (Onboarding -> Login -> Unlock ->
E2E), na sessão compartilhada: continua do login deixado pelo CT002, e
o CT005 deixa o app na criação do PIN para o CT006. Rodando sozinho, o
teste leva o app ao login (zerando pelo próprio app se estiver logado).
"""

import pytest

from tests.support.assertions import validar_erro_login
from tests.support.flows import (
    fazer_login_ate_criar_pin,
    levar_a_tela_login,
    tentar_login,
)

pytestmark = [pytest.mark.primeiro_acesso, pytest.mark.exibir_lembrete]


@pytest.fixture
def ir_ao_login(
    app_session_e2e_registro_ponto,
    _credenciais_app,
    celular_api,
    monitor_nome_pessoa,
    estado_primeiro_acesso,
):
    """
    Leva o app à tela de login (vindo de qualquer etapa).

    Devolve a função em vez de já executar: chamada dentro do teste, uma
    falha nesse caminho entra no vídeo (que grava só o corpo do teste,
    não o setup).
    """

    def ir():
        return levar_a_tela_login(
            app_session_e2e_registro_ponto.driver,
            _credenciais_app,
            celular_api,
            monitor_nome_pessoa,
            estado_primeiro_acesso,
        )

    return ir


@pytest.mark.ct("CT003")
# === Login: cenários negativos ===
@pytest.mark.regression
def test_login_invalido(
    ir_ao_login,
    app_session_e2e_registro_ponto,
    app_system,
    app_password,
    test_data,
):
    """
    Valida erro ao informar login inválido.

    Fronteira: Login -> permanece em Login.
    """
    usuario_invalido = test_data["APP_LOGIN_INVALIDO"]
    mensagem_esperada = test_data["MSG_LOGIN_INVALIDO"]

    ir_ao_login()

    login_page = tentar_login(
        driver=app_session_e2e_registro_ponto.driver,
        nome_sistema=app_system,
        usuario=usuario_invalido,
        senha=app_password,
    )

    validar_erro_login(
        login_page=login_page,
        mensagem_esperada=mensagem_esperada,
    )


@pytest.mark.ct("CT004")
@pytest.mark.regression
def test_senha_invalida(
    ir_ao_login,
    app_user,
    test_data,
):
    """
    Valida a visualização da senha e o erro ao informar senha inválida.

    Fronteira: Login -> permanece em Login.
    """
    senha_invalida = test_data["APP_SENHA_INVALIDA"]
    mensagem_esperada = test_data["MSG_LOGIN_INVALIDO"]

    login_page = ir_ao_login()

    login_page.preencher_login(app_user)
    login_page.preencher_senha(senha_invalida)

    assert login_page.senha_esta_oculta(), (
        "O campo de senha deveria iniciar com o conteúdo oculto."
    )

    login_page.clicar_ver_senha()

    assert login_page.senha_esta_visivel(), (
        "A senha não ficou visível após acionar o botão de visualização."
    )

    assert login_page.obter_valor_campo_senha() == senha_invalida, (
        "A senha exibida não corresponde ao valor informado."
    )

    login_page.clicar_ver_senha()

    assert login_page.senha_esta_oculta(), (
        "A senha não voltou a ficar oculta após acionar novamente o botão."
    )

    login_page.clicar_entrar()

    validar_erro_login(
        login_page=login_page,
        mensagem_esperada=mensagem_esperada,
    )


@pytest.mark.ct("CT005")
# === Login: cenário positivo ===
@pytest.mark.smoke
def test_credenciais_validas(
    ir_ao_login,
    app_session_e2e_registro_ponto,
    _credenciais_app,
    celular_api,
    monitor_nome_pessoa,
    estado_primeiro_acesso,
):
    """
    Valida login com credenciais válidas até a tela de criação do PIN.

    Termina na criação do PIN (o CT006 continua dali).

    Fronteira: Login -> PIN.
    """
    ir_ao_login()

    unlock_page = fazer_login_ate_criar_pin(
        app_session_e2e_registro_ponto.driver,
        _credenciais_app,
        celular_api,
        monitor_nome_pessoa,
        estado_primeiro_acesso,
    )

    assert unlock_page.validar_tela_criar_pin(), (
        "A tela de criação de PIN não foi exibida após o login "
        "com credenciais válidas."
    )
