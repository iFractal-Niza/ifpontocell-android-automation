from time import monotonic

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.timeouts import FLOW_TIMEOUT
from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.onboarding_page import OnboardingPage
from pages.unlock_page import UnlockPage
from utils.exceptions import (
    AlertaInesperado,
    ConexaoIndisponivel,
    LoginRejeitadoInesperado,
    SistemaRejeitadoInesperado,
)


# === Helpers internos ===
def _elemento_presente(
    driver,
    locator: tuple[str, str],
) -> bool:
    """
    Verifica presença sem aplicar wait explícito.

    Usado somente para sondagens de estado conhecidas, evitando
    consumir LONG_TIMEOUT em verificações negativas.
    """
    return bool(
        driver.find_elements(*locator)
    )


def _verificar_sistema_nao_rejeitado(
    onboarding_page: OnboardingPage,
    nome_sistema: str,
) -> None:
    """
    Verifica ativamente se o popup de sistema não encontrado apareceu
    após informar um nome de sistema que deveria ser válido.

    Presença do popup aqui é falha real (o sistema deveria ser aceito)
    e é levantada como tal, em vez de deixar o app seguir para um
    TimeoutException genérico ao esperar a tela de login.
    """
    if onboarding_page.popup_sem_conexao_esta_visivel():
        mensagem_popup = (
            onboarding_page.obter_mensagem_popup_sem_conexao()
        )

        raise ConexaoIndisponivel(
            "O app exibiu o alerta de conexão indisponível ao "
            f"informar o sistema (sistema={nome_sistema!r}, "
            f"popup={mensagem_popup!r}). "
            "Verifique: (1) a rede do emulador/device Android, "
            "(2) se o backend de homologação está acessível.",
            tela="OnboardingPage",
            elemento="popup_sem_conexao",
            acao="informar_nome_sistema_e_avancar",
        )

    if onboarding_page.popup_sistema_nao_encontrado_esta_visivel():
        mensagem_popup = (
            onboarding_page.obter_mensagem_popup_sistema_nao_encontrado()
        )

        raise SistemaRejeitadoInesperado(
            "O app rejeitou um nome de sistema que deveria ser válido "
            f"(sistema={nome_sistema!r}, popup={mensagem_popup!r}). "
            "Verifique: (1) o nome do sistema em config/env.yaml, "
            "(2) se o backend de homologação está no ar, "
            "(3) se há um bug de validação de sistema no app.",
            tela="OnboardingPage",
            elemento="popup_sistema_nao_encontrado",
            acao="informar_nome_sistema_e_avancar",
        )

    mensagem_desconhecida = (
        onboarding_page.obter_mensagem_alerta_inesperado()
    )

    if mensagem_desconhecida is not None:
        raise AlertaInesperado(
            "O app exibiu um alerta não reconhecido ao informar o "
            f"sistema (sistema={nome_sistema!r}, "
            f"popup={mensagem_desconhecida!r}). Esse popup ainda não "
            "tem locator específico — adicione um se ele se repetir.",
            tela="OnboardingPage",
            elemento="alerta_desconhecido",
            acao="informar_nome_sistema_e_avancar",
        )


def _aguardar_tela_login(
    driver,
    login_page: LoginPage,
) -> LoginPage:
    WebDriverWait(
        driver,
        FLOW_TIMEOUT,
        poll_frequency=0.2,
    ).until(
        EC.visibility_of_element_located(
            login_page.CAMPO_LOGIN,
        ),
        message=(
            f"O campo de login não ficou visível em {FLOW_TIMEOUT}s "
            "ao tentar posicionar a execução na tela de login."
        ),
    )

    assert login_page.validar_tela_login(), (
        "A execução não chegou à tela de login "
        "após o tratamento do estado inicial."
    )

    return login_page


def _ativar_celular_primeiro_acesso(
    celular_api,
    monitor_nome_pessoa: str | None,
    codigos_anteriores: set[int] | None,
) -> int:
    """Ativa pela API o celular criado no primeiro acesso atual."""
    if celular_api is None:
        raise AssertionError(
            "O cliente MonitorCelularClient não foi informado. "
            "Passe a fixture celular_api para realizar_unlock()."
        )

    nome_pessoa = (
        monitor_nome_pessoa or ""
    ).strip()

    if not nome_pessoa:
        raise AssertionError(
            "MONITOR_NOME_PESSOA não foi configurado. "
            "Preencha a variável em config/env.yaml."
        )

    return (
        celular_api
        .aguardar_e_ativar_celular_mais_recente(
            nome_pessoa=nome_pessoa,
            codigos_anteriores=codigos_anteriores,
            timeout=60,
            poll_interval=2,
        )
    )




# === Estado inicial ===
def garantir_tela_login(
    driver,
    nome_sistema: str,
    app_pin: str | None = None,
) -> LoginPage:
    """
    Posiciona a execução na tela de login sem submeter credenciais.

    Limitação:
    - O reset da sessão autenticada ainda não foi implementado.
    """
    onboarding_page = OnboardingPage(driver)
    login_page = LoginPage(driver)
    unlock_page = UnlockPage(driver)
    home_page = HomePage(driver)

    # Sondagem imediata para não consumir timeout em cold start.
    if _elemento_presente(
        driver,
        login_page.CAMPO_LOGIN,
    ):
        return _aguardar_tela_login(
            driver=driver,
            login_page=login_page,
        )

    esta_no_onboarding = (
        onboarding_page.esta_na_tela_boas_vindas()
        or onboarding_page.esta_na_tela_informacoes_importantes()
        or onboarding_page.esta_na_tela_configurar_aplicativo()
    )

    if esta_no_onboarding:
        onboarding_page.preparar_fluxo_inicial(
            permitir_notificacoes=False,
        )

        onboarding_page.informar_nome_sistema_e_avancar(
            nome_sistema,
        )

        _verificar_sistema_nao_rejeitado(
            onboarding_page=onboarding_page,
            nome_sistema=nome_sistema,
        )

        return _aguardar_tela_login(
            driver=driver,
            login_page=login_page,
        )

    if (
        app_pin
        and unlock_page.esta_na_tela_unlock(
            timeout=unlock_page.SHORT_TIMEOUT,
        )
    ):
        unlock_page.desbloquear_com_pin(
            app_pin
        )

        if home_page.esta_na_home(
            timeout=home_page.SHORT_TIMEOUT,
        ):
            raise AssertionError(
                "Após desbloquear com PIN, o app acessou a Home, "
                "mas o reset da sessão autenticada ainda não foi "
                "implementado."
            )

    if home_page.esta_na_home(
        timeout=home_page.SHORT_TIMEOUT,
    ):
        raise AssertionError(
            "O app abriu autenticado na Home, mas o reset "
            "da sessão ainda não foi implementado."
        )

    return _aguardar_tela_login(
        driver=driver,
        login_page=login_page,
    )


# === Onboarding ===
def abrir_tela_configurar_aplicativo(
    driver,
) -> OnboardingPage:
    onboarding_page = OnboardingPage(driver)

    onboarding_page.preparar_fluxo_inicial(
        permitir_notificacoes=False,
    )

    assert onboarding_page.validar_tela_configurar_aplicativo(), (
        "A tela 'Configurar Aplicativo' não foi exibida."
    )

    return onboarding_page


def acessar_tela_login(
    driver,
    nome_sistema: str,
) -> LoginPage:
    onboarding_page = abrir_tela_configurar_aplicativo(
        driver,
    )

    login_page = LoginPage(driver)

    onboarding_page.informar_nome_sistema_e_avancar(
        nome_sistema,
    )

    _verificar_sistema_nao_rejeitado(
        onboarding_page=onboarding_page,
        nome_sistema=nome_sistema,
    )

    return _aguardar_tela_login(
        driver=driver,
        login_page=login_page,
    )


# === Login ===
def tentar_login(
    driver,
    nome_sistema: str,
    usuario: str,
    senha: str,
    app_pin: str | None = None,
) -> LoginPage:
    login_page = garantir_tela_login(
        driver=driver,
        nome_sistema=nome_sistema,
        app_pin=app_pin,
    )

    login_page.realizar_login(
        login=usuario,
        senha=senha,
    )

    return login_page


def realizar_login(
    driver,
    nome_sistema: str,
    usuario: str,
    senha: str,
    app_pin: str | None = None,
) -> UnlockPage:
    """
    Executa login válido até a tela de criação do PIN.

    Após o envio das credenciais, verifica ativamente se o popup de
    erro de login apareceu. Presença do popup aqui é falha real (a
    credencial deveria ser válida) e é levantada como tal, em vez de
    deixar o app seguir para um TimeoutException com mensagem vazia
    ao esperar a tela de criação do PIN.

    A espera pela tela de PIN é feita diretamente no locator exclusivo
    da criação, evitando chamadas repetidas de esta_na_tela_criar_pin().
    """
    login_page = tentar_login(
        driver=driver,
        nome_sistema=nome_sistema,
        usuario=usuario,
        senha=senha,
        app_pin=app_pin,
    )

    if login_page.popup_sem_conexao_esta_visivel():
        mensagem_popup = login_page.obter_mensagem_popup_sem_conexao()

        raise ConexaoIndisponivel(
            "O app exibiu o alerta de conexão indisponível ao "
            f"submeter o login (usuário={usuario!r}, "
            f"popup={mensagem_popup!r}). "
            "Verifique: (1) a rede do emulador/device Android, "
            "(2) se o backend de homologação está acessível.",
            tela="LoginPage",
            elemento="popup_sem_conexao",
            acao="realizar_login",
        )

    if login_page.popup_erro_login_esta_visivel():
        mensagem_popup = login_page.obter_mensagem_erro_login()

        raise LoginRejeitadoInesperado(
            "O app rejeitou um login que deveria ser válido "
            f"(usuário={usuario!r}, popup={mensagem_popup!r}). "
            "Verifique: (1) a credencial em config/env.yaml, "
            "(2) se o backend de homologação está no ar, "
            "(3) se há um bug de validação de login no app.",
            tela="LoginPage",
            elemento="popup_erro_login",
            acao="realizar_login",
        )

    mensagem_desconhecida = login_page.obter_mensagem_alerta_inesperado()

    if mensagem_desconhecida is not None:
        raise AlertaInesperado(
            "O app exibiu um alerta não reconhecido durante o login "
            f"(usuário={usuario!r}, popup={mensagem_desconhecida!r}). "
            "Esse popup ainda não tem locator específico — adicione "
            "um se ele se repetir.",
            tela="LoginPage",
            elemento="alerta_desconhecido",
            acao="realizar_login",
        )

    unlock_page = UnlockPage(driver)

    unlock_page.tratar_popup_salvar_senha_se_existir()

    WebDriverWait(
        driver,
        FLOW_TIMEOUT,
        poll_frequency=0.2,
    ).until(
        EC.visibility_of_element_located(
            unlock_page.TEXTO_CRIAR_PIN,
        ),
        message=(
            "A tela de criação de PIN não apareceu em "
            f"{FLOW_TIMEOUT}s após o login com usuário={usuario!r}, "
            "e nenhum popup de erro de login foi detectado."
        ),
    )

    return unlock_page


# === Unlock ===
def realizar_unlock(
    driver,
    pin: str,
    tratar_popups_home: bool = True,
    *,
    celular_api=None,
    monitor_nome_pessoa: str | None = None,
    codigos_anteriores: set[int] | None = None,
) -> HomePage:
    """
    Finaliza o primeiro acesso a partir da criação do PIN.

    Fluxo Android:
    1. Localiza e ativa pela API o celular criado no login atual.
    2. Cria e confirma o PIN pelo teclado numberN.
    3. Aguarda a Home.
    4. Trata os popups conhecidos do primeiro acesso.

    Pré-condição:
    - Driver posicionado na tela de criação do PIN.

    Fronteira:
    ativação pela API -> criação do PIN -> confirmação do PIN -> Home.
    """
    unlock_page = UnlockPage(driver)
    home_page = HomePage(driver)

    # === Ativação do celular criado pela execução ===
    _ativar_celular_primeiro_acesso(
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
        codigos_anteriores=codigos_anteriores,
    )

    unlock_page.configurar_pin(
        pin
    )

    home_page.aguardar_primeiro_acesso_pronto()

    if tratar_popups_home:
        home_page.tratar_popups_home_se_existirem()

        assert home_page.validar_home(), (
            "A Home não foi exibida após a ativação do celular "
            "e configuração do PIN."
        )

        return home_page

    chegou_ao_primeiro_acesso = (
        home_page.popup_lembrete_esta_visivel(
            timeout=home_page.SHORT_TIMEOUT,
        )
        or home_page.esta_na_home(
            timeout=home_page.SHORT_TIMEOUT,
        )
    )

    assert chegou_ao_primeiro_acesso, (
        "A Home e o popup de lembrete não foram exibidos "
        "após a ativação do celular e configuração do PIN."
    )

    return home_page


# === Primeiro acesso ===
def realizar_primeiro_acesso(
    driver,
    nome_sistema: str,
    usuario: str,
    senha: str,
    pin: str,
    tratar_popups_home: bool = True,
    *,
    celular_api=None,
    monitor_nome_pessoa: str | None = None,
) -> HomePage:
    """
    Executa a jornada de primeiro acesso até a Home.

    Captura os códigos existentes antes do login, ativa o novo celular
    pela API e conclui a criação do PIN no Android.
    """
    if celular_api is None:
        raise AssertionError(
            "O cliente MonitorCelularClient não foi informado. "
            "Passe a fixture celular_api para "
            "realizar_primeiro_acesso()."
        )

    nome_pessoa = (
        monitor_nome_pessoa or ""
    ).strip()

    if not nome_pessoa:
        raise AssertionError(
            "MONITOR_NOME_PESSOA não foi configurado. "
            "Preencha a variável em config/env.yaml."
        )

    codigos_anteriores = (
        celular_api
        .obter_codigos_celular_por_nome_pessoa(
            nome_pessoa
        )
    )

    realizar_login(
        driver=driver,
        nome_sistema=nome_sistema,
        usuario=usuario,
        senha=senha,
    )

    return realizar_unlock(
        driver=driver,
        pin=pin,
        tratar_popups_home=tratar_popups_home,
        celular_api=celular_api,
        monitor_nome_pessoa=nome_pessoa,
        codigos_anteriores=codigos_anteriores,
    )

# === Sessão autenticada ===
def garantir_home_desbloqueada(
    driver,
    pin: str,
) -> HomePage:
    """
    Posiciona na Home a partir de uma sessão já autenticada.

    Não relança o app: opera sobre o estado atual da sessão.

    Estados aceitos:
    - Tela de desbloqueio por PIN: desbloqueia e valida a Home.
    - Home já aberta: apenas trata os popups.

    Um popup (Opinião, Melhoria) pode cobrir a tela a ponto de nem
    unlock nem Home serem reconhecidos — por isso limpa popups antes
    de cada checagem de estado, repetindo dentro do orçamento de
    POPUP_RESOLUTION_TIMEOUT em vez de desistir na primeira tentativa.

    Fronteira:
    unlock com PIN -> Home.
    """
    unlock_page = UnlockPage(driver)
    home_page = HomePage(driver)

    limite = monotonic() + home_page.POPUP_RESOLUTION_TIMEOUT

    while True:
        while (
            home_page.tratar_popup_opiniao_se_existir()
            or home_page.tratar_popup_melhoria_se_existir()
        ):
            pass

        if unlock_page.esta_na_tela_unlock(
            timeout=unlock_page.LONG_TIMEOUT,
        ):
            unlock_page.desbloquear_com_pin(pin)

            home_page.tratar_popup_atualizacao_se_existir()
            home_page.tratar_popups_home_se_existirem()

            assert home_page.esta_na_home(
                timeout=home_page.LONG_TIMEOUT,
            ), (
                "A Home não foi exibida após desbloquear "
                "o aplicativo com o PIN."
            )

            return home_page

        if home_page.esta_na_home(
            timeout=home_page.SHORT_TIMEOUT,
        ):
            home_page.tratar_popup_atualizacao_se_existir()
            home_page.tratar_popups_home_se_existirem()

            assert home_page.validar_home(), (
                "A Home deixou de ficar disponível durante "
                "o tratamento dos popups iniciais."
            )

            return home_page

        if monotonic() >= limite:
            raise AssertionError(
                "O app não abriu na tela de desbloqueio por PIN "
                "nem em uma Home autenticada."
            )