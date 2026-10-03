"""
E2E: primeiro acesso até a Home, o lembrete e os Ajustes.

Último elo da corrente do primeiro acesso (Onboarding -> Login ->
Unlock -> E2E), na sessão compartilhada: continua do lembrete deixado
pelo CT006 (ou da criação do PIN, quando o CT006 não roda, como no
smoke). Rodando sozinho, faz o primeiro acesso inteiro antes, zerando
pelo próprio app se ele já estiver logado (ex.: APP_SOURCE=package).
"""

import pytest

from pages.ajustes.settings_page import SettingsPage
from pages.home_page import HomePage
from tests.support.flows import (
    concluir_primeiro_acesso,
    levar_a_criacao_do_pin,
)


@pytest.mark.ct("CT007")
# === E2E: primeiro acesso, Home e configuração do lembrete ===
@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.regression
# O teste valida o popup de lembrete, suprimido por padrão nas sessões.
@pytest.mark.exibir_lembrete
# Valida o primeiro acesso: pede instalação limpa (as telas sobem mornas).
@pytest.mark.primeiro_acesso
def test_primeiro_acesso_home_e_lembrete(
    driver_e2e,
    _credenciais_app,
    celular_api,
    monitor_nome_pessoa,
    estado_primeiro_acesso,
):
    """
    Valida a jornada de primeiro acesso, a chegada à Home e a
    ativação do lembrete de registro de ponto.

    Fronteira:
    (Onboarding -> Login -> PIN, pelos elos anteriores ou aqui mesmo)
    -> Home
    -> popup de lembrete
    -> menu lateral
    -> Ajustes do Aplicativo
    -> Home.

    Responsabilidade:
    Provar que a aplicação chega a uma Home estável depois do primeiro
    acesso e que a ativação realizada no popup do primeiro acesso é
    refletida nos Ajustes do Aplicativo.

    Pré-condições externas:
    - Localização configurada para o emulador/device Android.
    - Appium disponível.
    - Dados de autenticação e API válidos.
    """
    home_page = HomePage(driver_e2e)

    if not home_page.popup_lembrete_esta_visivel(
        timeout=home_page.SHORT_TIMEOUT
    ):
        # Sem o lembrete na tela (o CT006 não rodou antes): do ponto em
        # que o app está até a Home, sem tratar o lembrete.
        levar_a_criacao_do_pin(
            driver_e2e,
            _credenciais_app,
            celular_api,
            monitor_nome_pessoa,
            estado_primeiro_acesso,
        )

        home_page = concluir_primeiro_acesso(
            driver_e2e,
            _credenciais_app,
            celular_api,
            monitor_nome_pessoa,
            estado_primeiro_acesso,
            tratar_popups_home=False,
        )

    # === Popup de lembrete do primeiro acesso ===
    home_page.clicar_ativar_popup_lembrete(
        timeout=home_page.LONG_TIMEOUT,
    )

    home_page.tratar_popups_home_se_existirem(
        tratar_lembrete=False,
    )

    assert not home_page.popup_atualizacao_esta_visivel(), (
        "O alerta de atualização permaneceu bloqueando a Home."
    )

    assert home_page.validar_home(), (
        "A Home não foi exibida após ativar o lembrete."
    )

    # === Configuração do lembrete nos Ajustes ===
    home_page.abrir_menu()

    settings_page = SettingsPage(driver_e2e)
    settings_page.acessar_ajustes_aplicativo()

    assert settings_page.validar_lembrete_registro_ponto_habilitado(), (
        "A opção 'Lembrete para registro do ponto' "
        "não foi habilitada após selecionar 'ATIVAR'."
    )

    # === Retorno à Home ===
    settings_page.voltar_para_home()

    assert home_page.esta_na_home(
        timeout=home_page.LONG_TIMEOUT,
    ), "A Home não foi exibida após retornar dos Ajustes do Aplicativo."
