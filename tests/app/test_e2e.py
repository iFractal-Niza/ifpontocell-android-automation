import pytest

from pages.settings_page import SettingsPage
from tests.support.flows import realizar_primeiro_acesso


# === E2E: primeiro acesso, Home e configuração do lembrete ===
@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.regression
def test_primeiro_acesso_home_e_lembrete(
    driver_e2e,
    app_system,
    app_user,
    app_password,
    app_pin,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Valida a jornada de primeiro acesso, a chegada à Home e a
    ativação do lembrete de registro de ponto.

    Fronteira:
    Onboarding
    -> Login
    -> PIN
    -> Home
    -> popup de lembrete
    -> menu lateral
    -> Ajustes do Aplicativo
    -> Home.

    Responsabilidade:
    Provar que a aplicação chega a uma Home estável a partir de
    uma instalação limpa e que a ativação realizada no popup do
    primeiro acesso é refletida nos Ajustes do Aplicativo.

    Pré-condições externas:
    - Localização configurada para o emulador/device Android.
    - Appium disponível.
    - Dados de autenticação e API válidos.

    O celular criado no login é identificado e ativado pela API
    dentro de realizar_primeiro_acesso().
    """
    home_page = realizar_primeiro_acesso(
        driver=driver_e2e,
        nome_sistema=app_system,
        usuario=app_user,
        senha=app_password,
        pin=app_pin,
        tratar_popups_home=False,
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
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
    ), (
        "A Home não foi exibida após retornar "
        "dos Ajustes do Aplicativo."
    )
