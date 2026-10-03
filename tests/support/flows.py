from time import monotonic, sleep

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.timeouts import FLOW_TIMEOUT
from pages.autenticacao.login_page import LoginPage
from pages.autenticacao.onboarding_page import OnboardingPage
from pages.autenticacao.unlock_page import UnlockPage
from pages.home_page import HomePage
from pages.zerar_dados.zerar_dados_page import ZerarDadosPage
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
    return bool(driver.find_elements(*locator))


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
        mensagem_popup = onboarding_page.obter_mensagem_popup_sem_conexao()

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
            "Verifique: (1) o nome do sistema em config/env.<device>.yaml, "
            "(2) se o backend de homologação está no ar, "
            "(3) se há um bug de validação de sistema no app.",
            tela="OnboardingPage",
            elemento="popup_sistema_nao_encontrado",
            acao="informar_nome_sistema_e_avancar",
        )

    mensagem_desconhecida = onboarding_page.obter_mensagem_alerta_inesperado()

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


def _marcar_sem_foto_antes_unlock(
    celular_api,
    monitor_nome_pessoa: str | None,
) -> int:
    """
    Marca sem_foto=True no celular que acabou de logar (registro de
    comunicação mais recente), antes da criação e confirmação do PIN.

    No Android o celular sobe ativo (emulador e celular): não há a
    ativação pela API que o iOS faz no simulador
    (_ativar_celular_antes_unlock), nem a espera por um registro novo.

    Feito aqui, antes do PIN, o app já encontra a configuração no
    backend ao chegar à Home e o registro de ponto não precisa relançar
    o app para aplicá-la; sem ela, o registro pediria foto e
    reconhecimento facial. Não afeta os testes que não registram ponto.
    """
    if celular_api is None:
        raise AssertionError(
            "O cliente MonitorCelularClient não foi informado. "
            "Passe a fixture celular_api para realizar_unlock()."
        )

    nome_pessoa = (monitor_nome_pessoa or "").strip()

    if not nome_pessoa:
        raise AssertionError(
            "MONITOR_NOME_PESSOA não foi configurado. "
            "Preencha a variável em config/env.<device>.yaml."
        )

    codigo = celular_api.obter_codigo_celular_por_nome_pessoa(nome_pessoa)

    celular_api.definir_sem_foto(codigo, sem_foto=True)

    return codigo


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

    if app_pin and unlock_page.esta_na_tela_unlock(
        timeout=unlock_page.SHORT_TIMEOUT,
    ):
        unlock_page.desbloquear_com_pin(app_pin)

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
            "Verifique: (1) a credencial em config/env.<device>.yaml, "
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
) -> HomePage:
    """
    Finaliza o primeiro acesso a partir da criação do PIN.

    Fluxo Android:
    1. Marca sem_foto pela API no celular que acabou de logar (ele já
       sobe ativo: sem a ativação do iOS).
    2. Cria e confirma o PIN pelo teclado numberN.
    3. Aguarda a Home.
    4. Trata os popups conhecidos do primeiro acesso.

    Pré-condição:
    - Driver posicionado na tela de criação do PIN.

    Fronteira:
    sem_foto pela API -> criação do PIN -> confirmação do PIN -> Home.
    """
    unlock_page = UnlockPage(driver)
    home_page = HomePage(driver)

    _marcar_sem_foto_antes_unlock(
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
    )

    unlock_page.configurar_pin(pin)

    home_page.aguardar_primeiro_acesso_pronto()

    if tratar_popups_home:
        home_page.tratar_popups_home_se_existirem()

        assert home_page.validar_home(), (
            "A Home não foi exibida após a ativação do celular "
            "e configuração do PIN."
        )

        return home_page

    chegou_ao_primeiro_acesso = home_page.popup_lembrete_esta_visivel(
        timeout=home_page.SHORT_TIMEOUT,
    ) or home_page.esta_na_home(
        timeout=home_page.SHORT_TIMEOUT,
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
    Executa a jornada de primeiro acesso até a Home: login, sem_foto
    pela API no celular que logou, criação e confirmação do PIN.
    """
    if celular_api is None:
        raise AssertionError(
            "O cliente MonitorCelularClient não foi informado. "
            "Passe a fixture celular_api para "
            "realizar_primeiro_acesso()."
        )

    nome_pessoa = (monitor_nome_pessoa or "").strip()

    if not nome_pessoa:
        raise AssertionError(
            "MONITOR_NOME_PESSOA não foi configurado. "
            "Preencha a variável em config/env.<device>.yaml."
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
        home_page.dispensar_popups_sobrepostos()

        # Timeout curto nas duas sondagens: o laço alterna entre elas
        # até o limite, então esperar LONG pelo unlock só atrasava o
        # caso comum (app já na Home).
        if unlock_page.esta_na_tela_unlock(
            timeout=unlock_page.SHORT_TIMEOUT,
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


# === Primeiro acesso em corrente ===
# Os testes do primeiro acesso (Onboarding, Login, Unlock, E2E) usam a
# mesma sessão e continuam de onde o anterior parou: sistema -> login ->
# criação do PIN -> Home com o lembrete. Rodando sozinho (ou se o
# anterior parou no meio), cada um leva o app à sua etapa por estas
# funções. Já logado, o app volta ao começo pelo próprio ZERAR DADOS:
# funciona no emulador e no celular (onde não há reinstalação).
ETAPA_ONBOARDING = "onboarding"
ETAPA_LOGIN = "login"
ETAPA_CRIAR_PIN = "criar_pin"
ETAPA_LOGADO = "logado"

# Quanto esperar o app mostrar alguma tela conhecida (ex.: logo depois
# de subir).
TEMPO_PARA_RECONHECER_ETAPA = 15


def etapa_do_primeiro_acesso(
    driver,
    timeout: float = TEMPO_PARA_RECONHECER_ETAPA,
) -> str | None:
    """
    Em que etapa do primeiro acesso o app está, pelas telas visíveis:
    onboarding (boas-vindas, informações, configurar sistema), login,
    criação do PIN, ou logado (PIN de desbloqueio, Home, lembrete).
    None se nenhuma aparecer no timeout.
    """
    home_page = HomePage(driver)
    sondagens = (
        (
            ETAPA_ONBOARDING,
            (
                OnboardingPage.TELA_BOAS_VINDAS,
                OnboardingPage.TELA_INFORMACOES_IMPORTANTES,
                OnboardingPage.TELA_CONFIGURAR_APLICATIVO,
            ),
        ),
        (ETAPA_LOGIN, (LoginPage.CAMPO_LOGIN,)),
        # As telas de PIN dividem o contêiner e o teclado: criação,
        # confirmação e desbloqueio vão pela instrução (text_instrucao).
        (
            ETAPA_CRIAR_PIN,
            (UnlockPage.TEXTO_CRIAR_PIN, UnlockPage.TEXTO_CONFIRMAR_PIN),
        ),
        (
            ETAPA_LOGADO,
            (UnlockPage.TEXTO_TELA_UNLOCK, HomePage.POPUP_LEMBRETE_MENSAGEM),
        ),
    )
    limite = monotonic() + timeout

    while True:
        for etapa, locators in sondagens:
            if any(_elemento_presente(driver, loc) for loc in locators):
                return etapa

        if home_page._home_esta_pronta_imediatamente():
            return ETAPA_LOGADO

        if monotonic() >= limite:
            return None

        sleep(0.5)


def zerar_dados_pelo_app(driver, pin: str) -> None:
    """
    Logado -> Home (desbloqueando, se preciso) -> menu do perfil ->
    ZERAR DADOS -> SIM -> primeiro acesso.
    """
    garantir_home_desbloqueada(driver=driver, pin=pin)

    pagina = ZerarDadosPage(driver)
    pagina.abrir_confirmacao()
    pagina.confirmar()

    assert pagina.voltou_ao_primeiro_acesso(timeout=pagina.LONG_TIMEOUT * 2), (
        "Depois de zerar os dados para recomeçar o primeiro acesso, o app "
        "não voltou ao onboarding."
    )


def levar_ao_onboarding(
    driver,
    credenciais: dict,
    celular_api,
    monitor_nome_pessoa: str,
    estado: dict,
) -> None:
    """
    Deixa o app no onboarding. Na tela de login ou de criação do PIN,
    conclui o primeiro acesso antes; logado, zera os dados pelo app.
    """
    etapa = etapa_do_primeiro_acesso(driver)

    if etapa == ETAPA_ONBOARDING:
        return

    if etapa is None:
        raise AssertionError(
            "Nenhuma tela do primeiro acesso (onboarding, login, PIN) nem "
            "a Home foi reconhecida: não dá para recomeçar o primeiro "
            "acesso a partir daqui."
        )

    if etapa == ETAPA_LOGIN:
        fazer_login_ate_criar_pin(
            driver, credenciais, celular_api, monitor_nome_pessoa, estado
        )
        etapa = ETAPA_CRIAR_PIN

    if etapa == ETAPA_CRIAR_PIN:
        concluir_primeiro_acesso(
            driver,
            credenciais,
            celular_api,
            monitor_nome_pessoa,
            estado,
            tratar_popups_home=True,
        )

    zerar_dados_pelo_app(driver, credenciais["pin"])


def levar_a_tela_login(
    driver,
    credenciais: dict,
    celular_api,
    monitor_nome_pessoa: str,
    estado: dict,
) -> LoginPage:
    """Deixa o app na tela de login (vindo de qualquer etapa)."""
    if etapa_do_primeiro_acesso(driver) != ETAPA_LOGIN:
        levar_ao_onboarding(
            driver, credenciais, celular_api, monitor_nome_pessoa, estado
        )

    return garantir_tela_login(
        driver=driver,
        nome_sistema=credenciais["sistema"],
    )


def fazer_login_ate_criar_pin(
    driver,
    credenciais: dict,
    celular_api,
    monitor_nome_pessoa: str,
    estado: dict,
) -> UnlockPage:
    """
    Da tela de login, login válido até a criação do PIN.

    No iOS, guarda no estado os códigos de celular de antes do login
    para a ativação pela API; no Android o celular sobe ativo e não há
    o que guardar.
    """
    return realizar_login(
        driver=driver,
        nome_sistema=credenciais["sistema"],
        usuario=credenciais["usuario"],
        senha=credenciais["senha"],
    )


def levar_a_criacao_do_pin(
    driver,
    credenciais: dict,
    celular_api,
    monitor_nome_pessoa: str,
    estado: dict,
) -> UnlockPage:
    """Deixa o app na criação do PIN (vindo de qualquer etapa)."""
    if etapa_do_primeiro_acesso(driver) == ETAPA_CRIAR_PIN:
        return UnlockPage(driver)

    levar_a_tela_login(
        driver, credenciais, celular_api, monitor_nome_pessoa, estado
    )

    return fazer_login_ate_criar_pin(
        driver, credenciais, celular_api, monitor_nome_pessoa, estado
    )


def concluir_primeiro_acesso(
    driver,
    credenciais: dict,
    celular_api,
    monitor_nome_pessoa: str,
    estado: dict,
    tratar_popups_home: bool,
) -> HomePage:
    """
    Da criação do PIN até a Home: sem_foto pela API, PIN e confirmação.
    Com tratar_popups_home=False, o lembrete do primeiro acesso fica na
    tela (o E2E o valida).
    """
    return realizar_unlock(
        driver=driver,
        pin=credenciais["pin"],
        tratar_popups_home=tratar_popups_home,
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
    )
