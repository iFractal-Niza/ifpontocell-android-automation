import os
from pathlib import Path
from time import perf_counter

import pytest
import yaml
from selenium.common.exceptions import WebDriverException

from api.ifponto_api_client import MonitorCelularClient
from core.app_session import AppSession
from core.driver_factory import create_driver
from core.privacy_services import CAMERA, LOCATION
from pages.home_page import HomePage
from pages.unlock_page import UnlockPage
from tests.support.profile_resolver import resolver_profile
from tests.support.flows import (
    garantir_home_desbloqueada,
    realizar_primeiro_acesso,
)
from utils.logger import get_logger


# === Paths e configuração base ===
PROJECT_ROOT = os.path.dirname(
    os.path.abspath(__file__)
)

pytest_plugins = [
    "observability.pytest_report",
]

logger = get_logger("conftest")


# === Configuração global do ambiente ===
def load_yaml_env() -> None:
    """
    Carrega as variáveis do env.yaml para o ambiente.

    Centraliza configurações do app, API, Android e massa de teste.
    """
    # Override por env var; por padrão, env.yaml dentro do projeto
    # (config/), não versionado (.gitignore).
    project_root = Path(__file__).resolve().parent

    env_path = Path(
        os.getenv(
            "IFPONTO_ENV_FILE",
            project_root / "config" / "env.yaml",
        )
    ).expanduser().resolve()

    if not env_path.is_file():
        logger.warning(
            "Arquivo env.yaml não encontrado em "
            f"{env_path}. Defina IFPONTO_ENV_FILE ou crie "
            "o arquivo antes de executar a suíte."
        )
        return

    with env_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not data:
        logger.warning(
            "Arquivo env.yaml está vazio. "
            "Preencha as configurações antes da execução."
        )
        return

    for key, value in data.items():
        os.environ[key] = str(value)

    logger.info(
        "Variáveis de ambiente carregadas com sucesso"
    )


def pytest_configure(config) -> None:
    """
    Carrega o ambiente antes da coleta.

    Executado como hook e não em tempo de import para que a ordem de
    carregamento não dependa de qual conftest o pytest importa primeiro.
    """
    load_yaml_env()


# === Devices da execução paralela ===
def _load_devices() -> list[dict]:
    """
    Carrega a lista de devices Android do devices.yaml.
    """
    path = os.path.join(
        PROJECT_ROOT,
        "config",
        "devices.yaml",
    )

    if not os.path.exists(path):
        return []

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file) or {}

    return data.get("emulators", data.get("devices", []))


@pytest.fixture(scope="session")
def device_config(request) -> dict | None:
    """
    Retorna o device usado pelo worker atual.

    Comportamento:
    - Execução sequencial: usa as variáveis de ambiente.
    - Execução paralela: usa devices.yaml.
    """
    worker_id = os.getenv(
        "PYTEST_XDIST_WORKER",
        "",
    )

    if not worker_id:
        return None

    devices = _load_devices()

    if not devices:
        logger.warning(
            "devices.yaml não encontrado ou vazio. "
            "Usando variáveis de ambiente."
        )
        return None

    markers = {
        marker.name
        for marker in request.node.iter_markers()
    }

    for device in devices:
        device_marks = set(
            device.get("marks", [])
        )

        matching_marks = markers & device_marks

        if matching_marks:
            logger.info(
                "Device selecionado por mark: "
                f"{device['name']} "
                f"(worker={worker_id}, "
                f"marks={matching_marks})"
            )
            return device

    index = (
        int(worker_id.replace("gw", ""))
        % len(devices)
    )

    device = devices[index]

    logger.info(
        "Device selecionado por round-robin: "
        f"{device['name']} "
        f"(worker={worker_id}, index={index})"
    )

    return device


# === Helpers do driver ===
def _aplicar_localizacao_android(driver_instance) -> None:
    """Aplica a localização configurada no device Android, quando habilitada."""
    enabled = os.getenv("ANDROID_LOCATION_ENABLED", "false").strip().lower() in {
        "true", "1", "yes", "on"
    }
    if not enabled:
        logger.info("Localização Android desabilitada")
        return

    lat_raw = os.getenv("ANDROID_LOCATION_LATITUDE", "").strip()
    lon_raw = os.getenv("ANDROID_LOCATION_LONGITUDE", "").strip()
    if not lat_raw or not lon_raw:
        raise RuntimeError(
            "ANDROID_LOCATION_ENABLED=true exige ANDROID_LOCATION_LATITUDE e "
            "ANDROID_LOCATION_LONGITUDE no env.yaml."
        )
    try:
        latitude = float(lat_raw)
        longitude = float(lon_raw)
    except ValueError as error:
        raise RuntimeError("As coordenadas Android devem ser numéricas.") from error
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise RuntimeError("Coordenadas Android fora do intervalo válido.")
    try:
        driver_instance.set_location(latitude, longitude, 0)
    except WebDriverException as error:
        raise RuntimeError(
            "Não foi possível aplicar a localização no Android. Verifique permissões "
            "do device/emulador e o UiAutomator2 Driver."
        ) from error
    logger.info(
        "Localização Android aplicada: latitude=%s, longitude=%s",
        latitude, longitude,
    )


def _resolver_contexto_android(
    driver_instance,
    device_config: dict | None,
) -> tuple[str, str]:
    """Resolve UDID e appPackage usados pela sessão Android."""
    capabilities = driver_instance.capabilities or {}
    device = device_config or {}
    udid = str(
        capabilities.get("appium:udid")
        or capabilities.get("udid")
        or device.get("udid")
        or os.getenv("ANDROID_UDID", "")
    ).strip()
    app_package = str(
        capabilities.get("appium:appPackage")
        or capabilities.get("appPackage")
        or os.getenv("ANDROID_APP_PACKAGE", os.getenv("APP_PACKAGE", "br.com.ifractal.Stou"))
    ).strip()
    if not app_package:
        raise RuntimeError(
            "Não foi possível resolver o appPackage. Configure ANDROID_APP_PACKAGE no env.yaml."
        )
    return udid, app_package


def _finalizar_driver(
    driver_instance,
    fixture_name: str,
) -> None:
    """
    Finaliza o app e a sessão Appium de forma segura.

    O emulador/device permanece disponível e o app permanece instalado.
    """
    if not driver_instance:
        return

    app_package = os.getenv(
        "ANDROID_APP_PACKAGE",
        os.getenv("APP_PACKAGE", "br.com.ifractal.Stou"),
    ).strip()

    inicio = perf_counter()

    try:
        logger.info(
            f"Iniciando teardown: {fixture_name}"
        )

        if app_package:
            try:
                driver_instance.terminate_app(
                    app_package
                )

                logger.info(
                    "App finalizado antes do quit: "
                    f"{fixture_name}"
                )

            except WebDriverException:
                logger.exception(
                    "Falha ao finalizar app antes do quit: "
                    f"{fixture_name}"
                )

        driver_instance.quit()

        duracao = round(
            perf_counter() - inicio,
            2,
        )

        logger.info(
            f"Driver finalizado: {fixture_name} "
            f"({duracao}s)"
        )

    except Exception:
        duracao = round(
            perf_counter() - inicio,
            2,
        )

        logger.exception(
            f"Falha ao finalizar driver: {fixture_name} "
            f"({duracao}s)"
        )


# === Criação da sessão de app ===
def _criar_app_session(
    request,
    device_config: dict | None,
    cold_start: bool,
    permissions: frozenset[str] = frozenset(),
):
    """
    Cria a sessão Appium e entrega um AppSession preparado.

    Etapas:
    1. Resolve o LaunchProfile do teste atual.
    2. Cria a sessão Appium com as capabilities do perfil.
    3. Aplica a localização Android configurada.
    4. Prepara a sessão preservando o estado necessário ao teste.
    """
    profile = resolver_profile(
        request,
        cold_start=cold_start,
        permissions=permissions,
    )

    logger.info(
        f"Criando driver: {request.fixturename} "
        f"(cold_start={cold_start}, "
        f"launch_arguments={list(profile.arguments)})"
    )

    driver_instance = create_driver(
        profile=profile,
        device=device_config,
    )

    try:
        _aplicar_localizacao_android(
            driver_instance
        )

        device_udid, app_package = (
            _resolver_contexto_android(
                driver_instance=driver_instance,
                device_config=device_config,
            )
        )

        session = AppSession(
            driver=driver_instance,
            app_package=app_package,
            device_udid=device_udid,
            profile=profile,
        )

        session.preparar()

        return session

    except Exception:
        try:
            driver_instance.quit()

        except Exception:
            logger.exception(
                "Falha ao finalizar o driver após erro "
                "na configuração inicial da sessão"
            )

        raise


def _sessao_de_app(
    request,
    device_config: dict | None,
    cold_start: bool,
    permissions: frozenset[str] = frozenset(),
):
    """
    Generator compartilhado pelas fixtures de sessão.
    """
    session = _criar_app_session(
        request=request,
        device_config=device_config,
        cold_start=cold_start,
        permissions=permissions,
    )

    try:
        yield session

    finally:
        _finalizar_driver(
            session.driver,
            fixture_name=request.fixturename,
        )


# === Fixtures de sessão ===
@pytest.fixture
def app_session(request, device_config):
    """
    Sessão de app padrão, com isolamento por teste.
    """
    yield from _sessao_de_app(
        request=request,
        device_config=device_config,
        cold_start=False,
    )


@pytest.fixture(scope="module")
def app_session_onboarding(request, device_config):
    """
    Sessão com cold start para onboarding.

    Escopo de módulo: markers declarados na função de teste não são
    visíveis aqui. Use pytestmark no módulo para captura simulada.
    """
    yield from _sessao_de_app(
        request=request,
        device_config=device_config,
        cold_start=True,
    )


@pytest.fixture(scope="function")
def app_session_login(request, device_config):
    """
    Sessão com cold start e isolamento por cenário de login.
    """
    yield from _sessao_de_app(
        request=request,
        device_config=device_config,
        cold_start=True,
    )


@pytest.fixture(scope="module")
def app_session_unlock(request, device_config):
    """
    Sessão com cold start para os testes de unlock.
    """
    yield from _sessao_de_app(
        request=request,
        device_config=device_config,
        cold_start=True,
    )


@pytest.fixture(scope="module")
def app_session_home(request, device_config):
    """
    Sessão com cold start para os testes da Home.
    """
    yield from _sessao_de_app(
        request=request,
        device_config=device_config,
        cold_start=True,
    )


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
            _finalizar_driver(
                session.driver,
                fixture_name="app_session_e2e_registro_ponto",
            )


@pytest.fixture(scope="function")
def app_session_e2e_registro_ponto(
    request,
    device_config,
    _estado_sessao_e2e_registro_ponto,
):
    """
    Compartilha o mesmo driver entre:

    1. test_e2e.py, que prepara primeiro acesso, PIN e primeiro acesso Android.
    2. test_registro_sem_foto.py, que reutiliza o estado persistido.

    A criação permanece function-scoped para que o LaunchProfile seja
    resolvido com os markers do teste que inicia a jornada.
    """
    session = _estado_sessao_e2e_registro_ponto["session"]

    if session is None:
        session = _criar_app_session(
            request=request,
            device_config=device_config,
            cold_start=True,
            permissions=frozenset({
                LOCATION,
                CAMERA,
            }),
        )

        _estado_sessao_e2e_registro_ponto["session"] = session

        logger.info(
            "Sessão compartilhada criada para E2E e registro de ponto"
        )

    else:
        logger.info(
            "Sessão compartilhada reutilizada pelo registro de ponto"
        )

    return session


@pytest.fixture(scope="function")
def home_para_marcacao(
    app_session_e2e_registro_ponto,
    _estado_sessao_e2e_registro_ponto,
    app_system,
    app_user,
    app_password,
    app_pin,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Prepara a Home autenticada para um teste de registro sem foto.

    Autossuficiente: se a sessão compartilhada ainda não passou pelo
    primeiro acesso (registro rodando isolado), realiza a jornada
    completa até a Home antes de seguir.

    Garante sem_foto=True no cadastro do celular via API — a
    marcação deste usuário não deve exigir foto, mesmo que a
    configuração GLOBAL exija reconhecimento facial para o sistema
    todo (eixos independentes — ver MonitorCelularClient).

    O app só reflete essa config numa comunicação nova com o
    backend, não na sessão já em execução — por isso relança e
    reestabelece a Home *depois* de escrever sem_foto. Faz isso uma
    única vez por sessão compartilhada (guardado em
    _estado_sessao_e2e_registro_ponto): uma vez sincronizado, o app
    mantém o estado pelo resto da sessão, e repetir o relançamento
    a cada teste seria custo sem ganho.
    """
    session = app_session_e2e_registro_ponto
    driver = session.driver

    home_page = HomePage(driver)
    unlock_page = UnlockPage(driver)

    # Um popup (Opinião, Melhoria) pode ter ficado pairando do teste
    # anterior — sem tratar antes, os elementos da Home ficam
    # obscurecidos e esta_na_home() retorna False, levando o fixture
    # a tentar um primeiro acesso do zero numa sessão já autenticada.
    # Checagem imediata (não a janela de polling de
    # tratar_popups_home_se_existirem): pode não haver Home nenhuma
    # ainda (tela de unlock), então não faz sentido esperar por ela.
    while (
        home_page.tratar_popup_opiniao_se_existir()
        or home_page.tratar_popup_melhoria_se_existir()
    ):
        pass

    ja_autenticado = (
        home_page.esta_na_home(
            timeout=home_page.SHORT_TIMEOUT,
        )
        or unlock_page.esta_na_tela_unlock(
            timeout=unlock_page.SHORT_TIMEOUT,
        )
    )

    if not ja_autenticado:
        logger.info(
            "Sessão sem autenticação; realizando primeiro acesso "
            "para o registro sem foto"
        )

        home = realizar_primeiro_acesso(
            driver=driver,
            nome_sistema=app_system,
            usuario=app_user,
            senha=app_password,
            pin=app_pin,
            celular_api=celular_api,
            monitor_nome_pessoa=monitor_nome_pessoa,
        )
    else:
        home = garantir_home_desbloqueada(
            driver=driver,
            pin=app_pin,
        )

    if not _estado_sessao_e2e_registro_ponto.get(
        "sem_foto_configurado"
    ):
        codigo_celular = (
            celular_api.obter_codigo_celular_por_nome_pessoa(
                monitor_nome_pessoa
            )
        )
        celular_api.definir_sem_foto(codigo_celular, sem_foto=True)

        session.relaunch()

        home = garantir_home_desbloqueada(
            driver=driver,
            pin=app_pin,
        )

        _estado_sessao_e2e_registro_ponto[
            "sem_foto_configurado"
        ] = True

    return home


# === Fixtures de driver (compatibilidade) ===
# Mantidas para que os testes existentes continuem recebendo o driver
# diretamente. Testes novos devem usar as fixtures app_session_*, que
# expõem relaunch() e troca de captura simulada.
@pytest.fixture
def driver(app_session):
    return app_session.driver


@pytest.fixture(scope="module")
def driver_onboarding(app_session_onboarding):
    return app_session_onboarding.driver


@pytest.fixture(scope="function")
def driver_login(app_session_login):
    return app_session_login.driver


@pytest.fixture(scope="module")
def driver_unlock(app_session_unlock):
    return app_session_unlock.driver


@pytest.fixture(scope="module")
def driver_home(app_session_home):
    return app_session_home.driver


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


# === Massa de teste ===
@pytest.fixture
def test_data():
    """
    Carrega dados de teste do test_data.yaml.
    """

    project_root = Path(__file__).resolve().parent

    test_data_path = Path(
        os.getenv(
            "TEST_DATA_FILE",
            project_root / "config" / "test_data.yaml",
        )
    ).expanduser().resolve()

    if not test_data_path.is_file():
        raise FileNotFoundError(
            f"Arquivo de dados de teste não encontrado em: {test_data_path}"
        )

    with test_data_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# === API ===
@pytest.fixture(scope="module")
def celular_api():
    """
    Retorna o cliente da API de controle de celular.

    O escopo de módulo permite reutilizar a mesma sessão HTTP
    durante os fluxos de preparação e execução do módulo.
    """
    client = MonitorCelularClient(
        base_url=os.getenv(
            "API_BASE_URL",
            "",
        ),
        user=os.getenv(
            "API_USER",
            "",
        ),
        token_original=os.getenv(
            "API_TOKEN",
            "",
        ),
    )

    try:
        yield client

    finally:
        client.session.close()

        logger.info(
            "Sessão da API de celulares finalizada"
        )


# === Contexto ===
@pytest.fixture(scope="session")
def monitor_nome_pessoa() -> str:
    """
    Nome utilizado para localizar o celular criado pelo login atual.
    """
    nome_pessoa = os.getenv(
        "MONITOR_NOME_PESSOA",
        "",
    ).strip()

    if not nome_pessoa:
        raise RuntimeError(
            "MONITOR_NOME_PESSOA não foi configurado "
            "em config/env.yaml."
        )

    return nome_pessoa


# === Dados do app ===
@pytest.fixture(scope="session")
def app_system():
    """
    Nome do sistema utilizado no onboarding.
    """
    return os.getenv("APP_SYSTEM")


@pytest.fixture(scope="session")
def app_user():
    """
    Usuário válido do app.
    """
    return os.getenv("APP_USER")


@pytest.fixture(scope="session")
def app_password():
    """
    Senha válida do app.
    """
    return os.getenv("APP_PASSWORD")


@pytest.fixture(scope="session")
def app_pin():
    """
    PIN válido para autenticação.
    """
    return os.getenv("APP_PIN")


@pytest.fixture(scope="session")
def app_pin_invalido():
    """
    PIN inválido para cenários negativos.
    """
    return os.getenv("APP_PIN_INVALIDO")