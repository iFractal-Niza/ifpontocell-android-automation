"""
Alterar PIN: tela Alterar Senha (menu do perfil -> ALTERAR SENHA), aba
SENHA 4 DÍGITOS. (A aba SENHA SISTEMA, a senha de autenticação geral, é
outro teste.)

Os negativos vêm primeiro e não trocam o PIN. Os três são encadeados na
tela Alterar Senha: o CT028 termina nela pedindo a senha atual, o CT029
continua dali e termina nela de novo (depois do aviso de repetição
divergente), e o CT030 continua dali. Rodando sozinho, cada um entra pelo
menu. O CT de troca muda o PIN,
confere o desbloqueio com o novo (e a recusa do antigo) e volta ao
original — que é o que todos os outros testes usam. Se falhar no meio, a
fixture restauracao_do_pin devolve o original.

Configuração: APP_PIN_NOVO no config/env.<device>.yaml, com o mesmo dígito
repetido, como o APP_PIN (ex.: "2222"). O PIN errado/divergente é o
APP_PIN_INVALIDO do test_data.yaml (ex.: "3333"), diferente dos dois.
"""

import pytest

from pages.alterar_senha.alterar_pin_page import AlterarPinPage
from pages.autenticacao.unlock_page import UnlockPage
from pages.home_page import HomePage


def _tela_aberta_ou_pelo_menu(request, sessao) -> AlterarPinPage:
    """
    A tela Alterar Senha pedindo um PIN (a senha atual ou a nova): a que
    já está aberta (deixada pelo teste anterior) ou aberta pelo menu a
    partir da Home.

    A home_autenticada só é pedida quando a tela não está aberta: ela
    relança o app se não estiver na Home, o que desfaria o encadeamento.
    """
    pagina = AlterarPinPage(sessao.driver)

    if pagina.aguardar_pedido_de_pin(timeout=pagina.SHORT_TIMEOUT):
        return pagina

    request.getfixturevalue("home_autenticada")
    pagina.acessar()

    return pagina


@pytest.mark.ct("CT028")
@pytest.mark.regression
def test_alterar_pin_senha_atual_errada_e_recusada(
    home_autenticada,
    app_session_e2e_registro_ponto,
    pin_invalido,
):
    """
    Valida que um PIN errado como senha atual é recusado: a tela continua
    pedindo a senha atual, sem ir para a criação da nova.

    Fronteira: Home -> ALTERAR SENHA -> SENHA 4 DÍGITOS -> PIN errado ->
    continua em "Digite a senha atual" (fica nela para o CT029).
    """
    pagina = AlterarPinPage(app_session_e2e_registro_ponto.driver)
    pagina.acessar()

    # A checagem espera o app limpar os dígitos (~2s) e termina com a
    # tela pedindo a senha atual de novo: o CT029 continua daqui.
    assert pagina.senha_atual_foi_recusada(pin_invalido), (
        f"O PIN errado ({pin_invalido}) foi aceito como senha atual."
    )


@pytest.mark.ct("CT029")
@pytest.mark.regression
def test_alterar_pin_confirmacao_divergente_reinicia(
    request,
    app_session_e2e_registro_ponto,
    app_pin,
    pin_novo,
    pin_invalido,
    restauracao_do_pin,
):
    """
    Valida que repetir um PIN diferente do novo é recusado: o app pede
    para tentar novamente e continua pedindo o PIN. (Que o PIN não mudou
    fica provado pelo CT030, que troca o PIN usando o original como
    senha atual.)

    Fronteira: tela pedindo a senha atual (deixada pelo CT028, ou Home
    -> ALTERAR SENHA -> SENHA 4 DÍGITOS) -> PIN atual -> novo PIN ->
    repetição divergente -> aviso "Confirmação de senha não conferem /
    Favor tentar novamente", esperando o PIN (fica na tela para o
    CT030).
    """
    sessao = app_session_e2e_registro_ponto
    pagina = _tela_aberta_ou_pelo_menu(request, sessao)

    pagina.informar_senha_atual(app_pin)
    pagina.teclado.criar_pin(pin_novo)

    restauracao_do_pin.pode_estar_trocado = True
    pagina.teclado.confirmar_pin(pin_invalido)

    assert pagina.repeticao_divergente_recusada(timeout=pagina.LONG_TIMEOUT), (
        "Com a repetição divergente, o app deveria pedir para tentar "
        "novamente."
    )

    # O aviso fica na tela esperando o PIN: o CT030 continua daqui.

    restauracao_do_pin.pode_estar_trocado = False


@pytest.mark.ct("CT030")
@pytest.mark.regression
def test_alterar_pin_desbloquear_com_o_novo_e_restaurar(
    request,
    app_session_e2e_registro_ponto,
    app_pin,
    pin_novo,
    restauracao_do_pin,
):
    """
    Valida a troca do PIN de 4 dígitos: o PIN antigo deixa de abrir o
    app, o novo abre, e o PIN original é restaurado no fim.

    Fronteira: tela Alterar Senha (deixada pelo CT029, ou Home -> ALTERAR
    SENHA -> SENHA 4 DÍGITOS) -> PIN atual (se pedido) -> novo PIN ->
    repetir -> Home -> relançar -> PIN antigo recusado ->
    PIN novo -> Home -> ALTERAR SENHA -> novo -> original -> repetir ->
    Home.
    """
    sessao = app_session_e2e_registro_ponto
    pagina = _tela_aberta_ou_pelo_menu(request, sessao)

    restauracao_do_pin.pode_estar_trocado = True
    pagina.alterar_pin(app_pin, pin_novo)

    # O PIN antigo não abre mais o app; o novo abre.
    sessao.relaunch()
    unlock = UnlockPage(sessao.driver)

    assert unlock.pin_foi_recusado(app_pin), (
        "Depois da troca, o PIN antigo ainda desbloqueou o app."
    )

    unlock.desbloquear_com_pin(pin_novo)

    home = HomePage(sessao.driver)
    home.dispensar_popups_sobrepostos()

    assert home.esta_na_home(timeout=home.LONG_TIMEOUT), (
        "A Home não foi exibida após desbloquear com o PIN novo."
    )

    # Volta ao PIN original, usado pelos demais testes.
    pagina.acessar()
    pagina.alterar_pin(pin_novo, app_pin)
    restauracao_do_pin.pode_estar_trocado = False
