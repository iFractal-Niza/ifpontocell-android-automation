import pytest

from tests.support.assertions import validar_erro_login
from tests.support.flows import (
    garantir_tela_login,
    realizar_login,
    tentar_login,
)


# === Login: cenários negativos ===
@pytest.mark.regression
def test_login_invalido(
    driver_login,
    app_system,
    app_password,
    app_pin,
    test_data,
):
    """
    Valida erro ao informar login inválido.

    Fronteira: Login -> permanece em Login.
    """
    usuario_invalido = test_data["APP_LOGIN_INVALIDO"]
    mensagem_esperada = test_data["MSG_LOGIN_INVALIDO"]

    login_page = tentar_login(
        driver=driver_login,
        nome_sistema=app_system,
        usuario=usuario_invalido,
        senha=app_password,
        app_pin=app_pin,
    )

    validar_erro_login(
        login_page=login_page,
        mensagem_esperada=mensagem_esperada,
    )


@pytest.mark.regression
def test_senha_invalida(
    driver_login,
    app_system,
    app_user,
    app_pin,
    test_data,
):
    """
    Valida a visualização da senha e o erro ao informar senha inválida.

    Fronteira: Login -> permanece em Login.
    """
    senha_invalida = test_data["APP_SENHA_INVALIDA"]
    mensagem_esperada = test_data["MSG_LOGIN_INVALIDO"]

    login_page = garantir_tela_login(
        driver=driver_login,
        nome_sistema=app_system,
        app_pin=app_pin,
    )

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


# === Login: cenário positivo ===
@pytest.mark.smoke
def test_credenciais_validas(
    driver_login,
    app_system,
    app_user,
    app_password,
    app_pin,
):
    """
    Valida login com credenciais válidas até a tela de criação do PIN.

    Fronteira: Login -> PIN.
    """
    unlock_page = realizar_login(
        driver=driver_login,
        nome_sistema=app_system,
        usuario=app_user,
        senha=app_password,
        app_pin=app_pin,
    )

    assert unlock_page.validar_tela_criar_pin(), (
        "A tela de criação de PIN não foi exibida após o login "
        "com credenciais válidas."
    )