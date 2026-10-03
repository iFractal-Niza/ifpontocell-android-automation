"""
Zerar Dados (menu do perfil -> ZERAR DADOS) e o mesmo apagar pelos
Ajustes do aplicativo (APAGAR DADOS DO APLICATIVO).

Os dois caminhos têm o par NÃO/SIM, como no iOS. No Android o diálogo é
o mesmo nos dois (linearApagarDadosDoApp), mas o botão que o abre é
outro e o SIM pode estar ligado a outra rotina. Em cada par, o NÃO deixa
a tela aberta e o SIM continua dali (rodando sozinho, parte da Home).

O NÃO do menu do perfil fecha o diálogo e deixa o menu aberto: o CT012
termina assim e o CT013 continua dali, tocando em ZERAR DADOS de novo.

O SIM apaga os dados do usuário no aparelho e o app volta ao primeiro
acesso; o teste refaz o primeiro acesso completo (o mesmo fluxo do e2e)
e termina na Home, com o app pronto para os próximos testes. Roda por
último na suíte de tela.
"""

import pytest

from pages.ajustes.apagar_dados_page import ApagarDadosAjustesPage
from pages.zerar_dados.zerar_dados_page import ZerarDadosPage
from tests.support.flows import realizar_primeiro_acesso

TITULO = "Apagar dados do aplicativo"

# Trecho-chave da mensagem (o texto inteiro é longo).
AVISO_IRREVERSIVEL = "não poderá ser revertida ou recuperada posteriormente"


def _refazer_primeiro_acesso(
    driver,
    sistema,
    usuario,
    senha,
    pin,
    celular_api,
    monitor_nome_pessoa,
) -> None:
    """
    Mesmo fluxo do e2e: deixa o app autenticado para os próximos testes.
    No Android o celular sobe ativo: o primeiro acesso só marca sem_foto.
    """
    home = realizar_primeiro_acesso(
        driver=driver,
        nome_sistema=sistema,
        usuario=usuario,
        senha=senha,
        pin=pin,
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
    )

    assert home.validar_home(), (
        "Depois de apagar os dados, o novo primeiro acesso não chegou à Home."
    )


@pytest.mark.ct("CT010")
@pytest.mark.regression
def test_apagar_dados_pelos_ajustes_nao_mantem_os_dados(home_autenticada):
    """
    Valida o APAGAR DADOS DO APLICATIVO dos Ajustes: o diálogo (título e
    aviso de que é irreversível) e que NÃO só fecha o diálogo, sem apagar
    nada.

    Fronteira: Home -> menu lateral -> AJUSTES DO APLICATIVO -> APAGAR
    DADOS DO APLICATIVO -> diálogo -> NÃO -> continua nos Ajustes (fica
    neles para o CT011).
    """
    pagina = ApagarDadosAjustesPage(home_autenticada.driver)
    pagina.abrir_confirmacao()

    assert pagina.titulo() == TITULO, (
        f"Título do diálogo: {pagina.titulo()!r}, esperado {TITULO!r}."
    )

    assert AVISO_IRREVERSIVEL in pagina.mensagem(), (
        "A mensagem do diálogo não avisa que a operação é irreversível."
    )

    pagina.cancelar()

    # Fica nos Ajustes: o SIM (CT011) continua daqui.
    assert pagina.ajustes.esta_na_tela_ajustes(), (
        "Após NÃO no diálogo de apagar dados, o app não continuou nos "
        "Ajustes do aplicativo."
    )


@pytest.mark.ct("CT011")
@pytest.mark.regression
def test_apagar_dados_pelos_ajustes_sim_volta_ao_primeiro_acesso(
    request,
    app_session_e2e_registro_ponto,
    app_system,
    app_user,
    app_password,
    app_pin,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Valida que SIM no APAGAR DADOS DO APLICATIVO dos Ajustes apaga os
    dados, o app volta ao primeiro acesso e um novo primeiro acesso
    completo leva à Home.

    Fronteira: Ajustes do aplicativo (deixados pelo CT010, ou Home ->
    menu lateral -> AJUSTES DO APLICATIVO) -> APAGAR DADOS DO APLICATIVO
    -> diálogo -> SIM -> onboarding -> primeiro acesso -> Home.
    """
    pagina = ApagarDadosAjustesPage(app_session_e2e_registro_ponto.driver)
    ja_nos_ajustes = pagina.ajustes.esta_na_tela_ajustes(
        timeout=pagina.SHORT_TIMEOUT
    )

    # Só pede a Home fora dos Ajustes: a home_autenticada relançaria o
    # app, desfazendo o encadeamento.
    if not ja_nos_ajustes:
        request.getfixturevalue("home_autenticada")

    pagina.abrir_confirmacao(ja_nos_ajustes=ja_nos_ajustes)
    pagina.confirmar()

    assert pagina.voltou_ao_primeiro_acesso(timeout=pagina.LONG_TIMEOUT * 2), (
        "Depois de apagar os dados pelos Ajustes, o app não voltou ao "
        "primeiro acesso (onboarding)."
    )

    _refazer_primeiro_acesso(
        pagina.driver,
        app_system,
        app_user,
        app_password,
        app_pin,
        celular_api,
        monitor_nome_pessoa,
    )


@pytest.mark.ct("CT012")
@pytest.mark.regression
def test_zerar_dados_nao_mantem_os_dados(home_autenticada):
    """
    Valida o diálogo de zerar dados (título e aviso de que é
    irreversível) e que NÃO só fecha o diálogo, sem apagar nada.

    Fronteira: Home -> menu do perfil -> ZERAR DADOS -> diálogo -> NÃO ->
    menu do perfil aberto (fica nele para o CT013).
    """
    pagina = ZerarDadosPage(home_autenticada.driver)
    pagina.abrir_confirmacao()

    assert pagina.titulo() == TITULO, (
        f"Título do diálogo: {pagina.titulo()!r}, esperado {TITULO!r}."
    )

    assert AVISO_IRREVERSIVEL in pagina.mensagem(), (
        "A mensagem do diálogo não avisa que a operação é irreversível."
    )

    pagina.cancelar()

    # O NÃO só fecha o diálogo: o menu do perfil continua aberto (o app
    # não foi para o primeiro acesso). O CT013 continua daqui.
    assert pagina.menu_perfil.esta_aberto(timeout=pagina.DEFAULT_TIMEOUT), (
        "Após NÃO no diálogo de zerar dados, o menu do perfil não "
        "continuou aberto."
    )


@pytest.mark.ct("CT013")
@pytest.mark.regression
def test_zerar_dados_sim_volta_ao_primeiro_acesso(
    request,
    app_session_e2e_registro_ponto,
    app_system,
    app_user,
    app_password,
    app_pin,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Valida que SIM apaga os dados, o app volta ao primeiro acesso e um
    novo primeiro acesso completo leva à Home.

    Fronteira: menu do perfil aberto (deixado pelo CT012, ou Home -> menu
    do perfil) -> ZERAR DADOS -> diálogo -> SIM -> onboarding -> primeiro
    acesso (sistema, login, sem_foto pela API, criação do PIN) -> Home.
    """
    pagina = ZerarDadosPage(app_session_e2e_registro_ponto.driver)

    # Só pede a Home se o menu não estiver aberto: a home_autenticada
    # relança o app fora da Home, o que desfaria o encadeamento.
    if not pagina.menu_perfil.esta_aberto(timeout=pagina.SHORT_TIMEOUT):
        request.getfixturevalue("home_autenticada")

    pagina.abrir_confirmacao()
    pagina.confirmar()

    assert pagina.voltou_ao_primeiro_acesso(timeout=pagina.LONG_TIMEOUT * 2), (
        "Depois de zerar os dados, o app não voltou ao primeiro acesso "
        "(onboarding)."
    )

    _refazer_primeiro_acesso(
        pagina.driver,
        app_system,
        app_user,
        app_password,
        app_pin,
        celular_api,
        monitor_nome_pessoa,
    )
