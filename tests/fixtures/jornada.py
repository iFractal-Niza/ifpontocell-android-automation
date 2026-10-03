"""
Sessão de app compartilhada pela suíte inteira: a corrente do primeiro
acesso (Onboarding, Login, Unlock, E2E) e os testes que partem da Home
autenticada (registro de ponto, Holerite, Informe, Estado de Humor...).
"""

import pytest

from core.privacy_services import CAMERA, LOCATION
from pages.autenticacao.unlock_page import UnlockPage
from pages.home_page import HomePage
from tests.fixtures.sessoes import criar_app_session, finalizar_driver
from tests.support.flows import (
    garantir_home_desbloqueada,
    realizar_primeiro_acesso,
)
from utils.logger import get_logger

logger = get_logger("fixtures.jornada")


# === Jornada E2E e registro de ponto ===
@pytest.fixture(scope="session")
def _estado_sessao_e2e_registro_ponto():
    """
    Mantém uma única AppSession entre o E2E e o registro de ponto.

    A sessão é criada pelo primeiro teste que solicitar a fixture e
    finalizada somente ao término da execução do Pytest.
    """
    estado = {
        "session": None,
    }

    try:
        yield estado

    finally:
        session = estado["session"]

        if session is not None:
            finalizar_driver(
                session.driver,
                fixture_name="app_session_e2e_registro_ponto",
                app_package=session.app_package,
            )


def _marcar_sem_foto_antes_de_abrir(
    celular_api,
    monitor_nome_pessoa: str,
) -> None:
    """
    Sessão morna: marca sem_foto no celular atual antes do app subir,
    para ele já ler a configuração no launch (sem relançar depois).

    Sem celular cadastrado ainda (emulador limpo), não há o que marcar:
    o primeiro acesso da home_autenticada marca sem_foto no celular que
    logar (flows._marcar_sem_foto_antes_unlock).
    """
    try:
        codigo = celular_api.obter_codigo_celular_por_nome_pessoa(
            monitor_nome_pessoa
        )
    except ValueError:
        logger.info(
            "Nenhum celular cadastrado ainda; sem_foto será marcado no "
            "primeiro acesso"
        )
        return

    celular_api.definir_sem_foto(codigo, sem_foto=True)


@pytest.fixture(scope="function")
def app_session_e2e_registro_ponto(
    request,
    device_config,
    _estado_sessao_e2e_registro_ponto,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Compartilha o mesmo driver entre:

    1. test_e2e.py, que prepara primeiro acesso, PIN e autorização.
    2. Os demais testes que partem da Home autenticada (registro de
       ponto, Holerite, Informe, Estado de Humor), que reutilizam o
       estado persistido.

    Quem cria a sessão decide como o app sobe: com
    @pytest.mark.primeiro_acesso, instalação limpa; sem ele, sessão
    morna (app como a execução anterior deixou).

    A criação permanece function-scoped para que o LaunchProfile seja
    resolvido com os markers do teste que inicia a jornada.
    """
    session = _estado_sessao_e2e_registro_ponto["session"]

    if session is None:
        # Quem cria a sessão decide como o app sobe. O teste que valida
        # o primeiro acesso (E2E) pede instalação limpa; os demais
        # (telas, registro) sobem mornos — app instalado e logado da
        # execução anterior — e a home_autenticada só desbloqueia com o
        # PIN, ou faz o primeiro acesso se o app não estiver logado.
        primeiro_acesso = (
            request.node.get_closest_marker("primeiro_acesso") is not None
        )

        # No primeiro acesso, o sem_foto é marcado antes do PIN
        # (flows._marcar_sem_foto_antes_unlock).
        if not primeiro_acesso:
            _marcar_sem_foto_antes_de_abrir(celular_api, monitor_nome_pessoa)

        session = criar_app_session(
            request=request,
            device_config=device_config,
            cold_start=primeiro_acesso,
            manter_estado=not primeiro_acesso,
            permissions=frozenset(
                {
                    LOCATION,
                    CAMERA,
                }
            ),
        )

        _estado_sessao_e2e_registro_ponto["session"] = session

        logger.info(
            "Sessão compartilhada criada "
            f"({'instalação limpa' if primeiro_acesso else 'morna'}) "
            f"por {request.node.name}"
        )

    else:
        logger.info("Sessão compartilhada reutilizada pelo registro de ponto")

    return session


def _esta_autenticado(
    home_page: HomePage,
    unlock_page: UnlockPage,
    timeout: float,
) -> bool:
    """
    Home ou tela de PIN visíveis: o app está logado.

    Um popup (Opinião, Melhoria, espelho pendente) pode estar na frente
    e obscurecer a Home; trata antes de checar, com checagem
    imediata (pode não haver Home nenhuma ainda, só a tela de PIN).
    """
    home_page.dispensar_popups_sobrepostos()

    return home_page.esta_na_home(timeout=timeout) or (
        unlock_page.esta_na_tela_unlock(timeout=timeout)
    )


def _garantir_home_autenticada(
    session,
    credenciais,
    celular_api,
    monitor_nome_pessoa: str,
    motivo: str,
):
    """
    Deixa a sessão compartilhada na Home autenticada.

    1. Home ou PIN visíveis: só desbloqueia com o PIN.
    2. Nenhum dos dois: relança o app uma vez e checa de novo. Algo
       pode estar na frente de um app já logado — um teste anterior que
       falhou no meio, ou o próprio sistema (ex.: um diálogo do Android
       que tira o app da frente). Sem isso, a fixture concluía
       "não logado" e tentava um primeiro acesso numa sessão logada,
       derrubando em cascata os testes seguintes.
    3. Ainda nada: o app de fato não está logado (emulador limpo);
       realiza o primeiro acesso completo.
    """
    driver = session.driver

    home_page = HomePage(driver)
    unlock_page = UnlockPage(driver)

    autenticado = _esta_autenticado(
        home_page,
        unlock_page,
        timeout=home_page.SHORT_TIMEOUT,
    )

    if not autenticado:
        logger.warning(
            "Nem Home nem tela de PIN reconhecidas; relançando o app "
            f"antes de concluir que não está logado ({motivo})"
        )

        session.relaunch()

        # O app acabou de subir: dá mais tempo para a tela de PIN.
        autenticado = _esta_autenticado(
            home_page,
            unlock_page,
            timeout=home_page.LONG_TIMEOUT,
        )

    if autenticado:
        return garantir_home_desbloqueada(
            driver=driver,
            pin=credenciais["pin"],
        )

    logger.info(
        f"Sessão sem autenticação; realizando primeiro acesso ({motivo})"
    )

    return realizar_primeiro_acesso(
        driver=driver,
        nome_sistema=credenciais["sistema"],
        usuario=credenciais["usuario"],
        senha=credenciais["senha"],
        pin=credenciais["pin"],
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
    )


@pytest.fixture
def _credenciais_app(app_system, app_user, app_password, app_pin) -> dict:
    return {
        "sistema": app_system,
        "usuario": app_user,
        "senha": app_password,
        "pin": app_pin,
    }


@pytest.fixture(scope="session")
def estado_primeiro_acesso() -> dict:
    """
    O que a corrente do primeiro acesso (Onboarding -> Login -> Unlock ->
    E2E) sabe entre um teste e outro (ver flows, "Primeiro acesso em
    corrente").

    No iOS guarda os códigos de celular de antes do login, para a
    ativação pela API. No Android o celular sobe ativo e o estado fica
    vazio; a fixture continua para a corrente ter a mesma assinatura do
    iOS (telas portadas de lá funcionam sem mudança).
    """
    return {}


@pytest.fixture(scope="session")
def marcacoes_registradas() -> list[str]:
    """
    Horários (HH:MM) das marcações que o registro de ponto fez nesta
    execução, na ordem: a aba STATUS confere a mais recente.
    """
    return []


@pytest.fixture(scope="function")
def home_autenticada(
    app_session_e2e_registro_ponto,
    _credenciais_app,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Home autenticada na sessão compartilhada, para telas que partem da
    Home (Holerite, Informe, Estado de Humor...).
    """
    return _garantir_home_autenticada(
        session=app_session_e2e_registro_ponto,
        credenciais=_credenciais_app,
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
        motivo="home autenticada",
    )


@pytest.fixture(scope="function")
def home_para_marcacao(
    app_session_e2e_registro_ponto,
    _credenciais_app,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Home autenticada para um teste de registro sem foto.

    O sem_foto=True do celular — a marcação deste usuário não deve
    exigir foto, mesmo que a configuração GLOBAL exija reconhecimento
    facial (eixos independentes, ver MonitorCelularClient) — é marcado
    antes do app ler a configuração: na ativação do celular (primeiro
    acesso) ou antes de abrir a sessão morna. Por isso o registro começa
    direto na Home, sem relançar o app.
    """
    return _garantir_home_autenticada(
        session=app_session_e2e_registro_ponto,
        credenciais=_credenciais_app,
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
        motivo="registro sem foto",
    )


@pytest.fixture(scope="function")
def driver_e2e(
    app_session_e2e_registro_ponto,
):
    return app_session_e2e_registro_ponto.driver


@pytest.fixture(scope="function")
def driver_registro_ponto(
    app_session_e2e_registro_ponto,
):
    return app_session_e2e_registro_ponto.driver
