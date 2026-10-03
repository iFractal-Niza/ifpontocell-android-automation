"""
Alterar a senha do sistema: tela Alterar Senha (menu do perfil ->
ALTERAR SENHA), aba SENHA SISTEMA. É a senha de login no servidor: vale
para o usuário em qualquer aparelho.

Smoke (entram no make smoke e, por ele, nos merges) e regressão. Os três
juntos: são encadeados.

Encadeados na mesma aba: o CT031 termina nela, o CT032 continua dali
(a senha atual já está preenchida: digita só a nova e a confirmação) e
o CT033 também. Rodando sozinho, cada um entra pelo menu.

Os negativos não trocam a senha (o sistema recusa antes). A troca
completa é REAL, no servidor: troca para APP_PASSWORD_NOVA (env.<device>.yaml),
prova que vale (Zerar Dados + primeiro acesso com a nova) e volta à
original. Se parar no meio, a fixture restauracao_da_senha devolve a
original.
"""

import pytest

from pages.alterar_senha.alterar_senha_sistema_page import (
    AlterarSenhaSistemaPage,
)
from pages.home_page import HomePage
from pages.zerar_dados.zerar_dados_page import ZerarDadosPage
from tests.support.flows import realizar_primeiro_acesso


def _aba_aberta_ou_pelo_menu(request, sessao):
    """
    (page, continuando): a aba SENHA SISTEMA já aberta (deixada pelo
    teste anterior, com a senha atual preenchida) ou aberta pelo menu.

    A home_autenticada só é pedida quando a aba não está aberta: ela
    relança o app fora da Home, o que desfaria o encadeamento.
    """
    pagina = AlterarSenhaSistemaPage(sessao.driver)

    if pagina.esta_aberta(timeout=pagina.SHORT_TIMEOUT):
        pagina.mostrar_senhas()
        return pagina, True

    request.getfixturevalue("home_autenticada")
    pagina.acessar()

    return pagina, False


@pytest.mark.ct("CT031")
@pytest.mark.smoke
@pytest.mark.regression
def test_alterar_senha_sistema_nova_igual_a_atual_e_recusada(
    home_autenticada,
    app_password,
):
    """
    Valida que a nova senha igual à atual é recusada, com o alerta "A
    senha atual não pode ser igual a anterior.", sem trocar a senha.

    Fronteira: Home -> ALTERAR SENHA -> SENHA SISTEMA -> atual, nova e
    confirmação iguais à senha atual -> SALVAR -> alerta -> OK -> continua
    na aba (fica nela para o CT032).
    """
    pagina = AlterarSenhaSistemaPage(home_autenticada.driver)
    pagina.acessar()

    pagina.preencher(app_password, app_password, app_password)
    pagina.salvar_esperando_alerta(
        pagina.MENSAGEM_NOVA_IGUAL_A_ATUAL,
        acao="salvar a nova senha igual à atual",
    )

    assert pagina.esta_aberta(timeout=pagina.DEFAULT_TIMEOUT), (
        "Depois do alerta, o app saiu da aba SENHA SISTEMA."
    )


@pytest.mark.ct("CT032")
@pytest.mark.smoke
@pytest.mark.regression
def test_alterar_senha_sistema_confirmacao_divergente_e_recusada(
    request,
    app_session_e2e_registro_ponto,
    app_password,
):
    """
    Valida que a confirmação diferente da nova senha é recusada (alertas
    "Senha não confere." e "Confirmação de senha não conferem"), sem
    trocar a senha.

    A nova senha é derivada da atual (diferente dela, para não cair no
    alerta de senha igual) e nunca é salva: o sistema recusa antes.

    Fronteira: aba SENHA SISTEMA (deixada pelo CT031, ou Home -> ALTERAR
    SENHA -> SENHA SISTEMA -> senha atual) -> nova e confirmação
    diferentes -> SALVAR -> alertas -> OK -> continua na aba (fica nela
    para o CT033).
    """
    pagina, continuando = _aba_aberta_ou_pelo_menu(
        request, app_session_e2e_registro_ponto
    )

    nova, confirmacao = f"{app_password}Aa1", f"{app_password}Aa2"

    if continuando:
        pagina.preencher_nova(nova, confirmacao)
    else:
        pagina.preencher(app_password, nova, confirmacao)

    pagina.salvar()

    mensagens = pagina.fechar_alertas_contendo(pagina.TRECHO_NAO_CONFERE)

    assert any("não confere" in mensagem for mensagem in mensagens), (
        "Com a confirmação diferente da nova senha, o app não avisou que a "
        f"senha não confere. Alertas vistos: {mensagens}."
    )

    assert pagina.esta_aberta(timeout=pagina.DEFAULT_TIMEOUT), (
        "Depois dos alertas, o app saiu da aba SENHA SISTEMA."
    )


@pytest.mark.ct("CT033")
@pytest.mark.smoke
@pytest.mark.regression
def test_alterar_senha_sistema_entrar_com_a_nova_e_restaurar(
    request,
    app_session_e2e_registro_ponto,
    app_system,
    app_user,
    app_password,
    app_pin,
    senha_nova,
    celular_api,
    monitor_nome_pessoa,
    restauracao_da_senha,
):
    """
    Valida a troca da senha do sistema: a senha nova passa a valer no
    login (depois de Zerar Dados), e a original é restaurada no fim.

    Fronteira: aba SENHA SISTEMA (deixada pelo CT032, ou Home -> ALTERAR
    SENHA -> SENHA SISTEMA -> original) -> nova e confirmação certas
    -> SALVAR -> "Senha alterada com sucesso." -> OK -> Home -> ZERAR
    DADOS -> SIM -> primeiro acesso com a senha nova -> Home -> SENHA
    SISTEMA -> nova -> original -> SALVAR -> sucesso -> Home.
    """
    driver = app_session_e2e_registro_ponto.driver
    pagina, continuando = _aba_aberta_ou_pelo_menu(
        request, app_session_e2e_registro_ponto
    )

    restauracao_da_senha.pode_estar_trocada = True

    if continuando:
        pagina.preencher_nova(senha_nova, senha_nova)
    else:
        pagina.preencher(app_password, senha_nova, senha_nova)

    pagina.salvar_esperando_alerta(
        pagina.MENSAGEM_SUCESSO, acao="salvar a senha nova"
    )

    assert HomePage(driver).esta_na_home(timeout=pagina.LONG_TIMEOUT), (
        "Depois da troca da senha, o app não voltou à Home."
    )

    # Prova que a senha nova vale no servidor: zera e entra com ela.
    zerar = ZerarDadosPage(driver)
    zerar.abrir_confirmacao()
    zerar.confirmar()

    assert zerar.voltou_ao_primeiro_acesso(timeout=zerar.LONG_TIMEOUT * 2), (
        "Depois de zerar os dados, o app não voltou ao primeiro acesso."
    )

    home = realizar_primeiro_acesso(
        driver=driver,
        nome_sistema=app_system,
        usuario=app_user,
        senha=senha_nova,
        pin=app_pin,
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
    )

    assert home.validar_home(), (
        "O primeiro acesso com a senha nova não chegou à Home."
    )

    # Volta à senha original, usada pelos demais testes.
    pagina.acessar()
    pagina.preencher(senha_nova, app_password, app_password)
    pagina.salvar_esperando_alerta(
        pagina.MENSAGEM_SUCESSO, acao="restaurar a senha original"
    )
    restauracao_da_senha.pode_estar_trocada = False

    assert HomePage(driver).esta_na_home(timeout=pagina.LONG_TIMEOUT), (
        "Depois de restaurar a senha original, o app não voltou à Home."
    )
