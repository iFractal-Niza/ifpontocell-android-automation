from pages.login_page import LoginPage
from pages.onboarding_page import OnboardingPage


# === Assertions de login ===
def validar_erro_login(
    login_page: LoginPage,
    mensagem_esperada: str,
) -> None:
    """
    Valida o popup exibido após uma tentativa de login inválida.

    Confirma a exibição e a mensagem do popup, fecha-o e verifica
    que a tela de login permanece disponível.
    """
    assert login_page.validar_popup_erro_login(), (
        "O popup de erro de login não foi exibido."
    )

    mensagem_atual = login_page.obter_mensagem_erro_login()

    assert mensagem_atual == mensagem_esperada, (
        "Mensagem de erro de login incorreta. "
        f"Esperado: '{mensagem_esperada}' | "
        f"Obtido: '{mensagem_atual}'"
    )

    login_page.clicar_ok_popup_erro_login()

    assert login_page.validar_tela_login(), (
        "A tela de login não permaneceu disponível "
        "após fechar o popup de erro."
    )


def validar_login_sem_popup_erro(
    login_page: LoginPage,
) -> None:
    """
    Valida que nenhum popup de erro seja exibido após um login válido.

    Caso o popup seja apresentado indevidamente, retorna a mensagem
    exibida para facilitar o diagnóstico da falha.
    """
    if not login_page.validar_popup_erro_login():
        return

    mensagem_atual = login_page.obter_mensagem_erro_login()

    raise AssertionError(
        "Um popup de erro foi exibido indevidamente "
        "após o login válido. "
        f"Mensagem apresentada: '{mensagem_atual}'"
    )


# === Assertions de onboarding ===
def validar_popup_sistema_nao_encontrado(
    onboarding_page: OnboardingPage,
    mensagem_esperada: str,
) -> None:
    """
    Valida o popup exibido quando o sistema não é encontrado.

    Confirma a exibição e a mensagem do popup, fecha-o e verifica
    que a tela de configuração permanece disponível.
    """
    assert onboarding_page.validar_popup_sistema_nao_encontrado(), (
        "O popup de sistema não encontrado não foi exibido."
    )

    mensagem_atual = (
        onboarding_page
        .obter_mensagem_popup_sistema_nao_encontrado()
    )

    assert mensagem_atual == mensagem_esperada, (
        "Mensagem incorreta no popup de sistema não encontrado. "
        f"Esperado: '{mensagem_esperada}' | "
        f"Obtido: '{mensagem_atual}'"
    )

    onboarding_page.clicar_ok_popup_sistema_nao_encontrado()

    assert onboarding_page.validar_tela_configurar_aplicativo(), (
        "A tela 'Configurar Aplicativo' não permaneceu disponível "
        "após fechar o popup."
    )


def validar_avanco_para_login_apos_correcao(
    driver,
    onboarding_page: OnboardingPage,
) -> None:
    """
    Valida o avanço para o login após corrigir o nome do sistema.

    Confirma que o popup de sistema não encontrado não reaparece
    e que a tela de login é exibida.
    """
    if onboarding_page.validar_popup_sistema_nao_encontrado():
        mensagem_atual = (
            onboarding_page
            .obter_mensagem_popup_sistema_nao_encontrado()
        )

        raise AssertionError(
            "O popup de sistema não encontrado foi exibido novamente "
            "após corrigir o nome do sistema. "
            f"Mensagem apresentada: '{mensagem_atual}'"
        )

    login_page = LoginPage(driver)

    assert login_page.validar_tela_login(), (
        "A tela de login não foi exibida após corrigir "
        "o nome do sistema."
    )