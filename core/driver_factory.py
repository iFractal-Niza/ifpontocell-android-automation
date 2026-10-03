import subprocess

from appium import webdriver
from selenium.common.exceptions import WebDriverException

from config.capabilities import get_android_options
from config.settings import Settings
from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_error, log_event

logger = get_logger("driver_factory")


# === Helpers do device ===
def _cleanup_android_app(
    device_udid: str | None,
    app_package: str,
    app_source: str,
) -> None:
    """
    Desinstala o app antes da sessão quando o APK será reinstalado.

    Uso:
    - Fluxos que precisam iniciar do zero (cold start).

    Com APP_SOURCE=package o app não é desinstalado (não haveria de onde
    reinstalar): o noReset=false do cold start limpa os dados dele.
    A ausência prévia do app não bloqueia a criação da sessão.
    """
    if app_source != "apk" or not app_package:
        log_event(
            logger,
            "Cold start sem desinstalação: APP_SOURCE não é apk",
            event="android_cleanup_skipped",
            app_source=app_source,
            app_package=app_package,
        )
        return

    comando = ["adb"]

    if device_udid:
        comando += ["-s", device_udid]

    comando += ["uninstall", app_package]

    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )

        log_event(
            logger,
            "Limpeza do app Android executada",
            event="android_app_cleanup",
            udid=device_udid,
            app_package=app_package,
            return_code=resultado.returncode,
            stdout=resultado.stdout.strip(),
            stderr=resultado.stderr.strip(),
        )

    except subprocess.TimeoutExpired as erro:
        log_error(
            logger,
            "Timeout ao desinstalar o app Android",
            event="android_app_cleanup_timeout",
            udid=device_udid,
            app_package=app_package,
            error=str(erro),
            remediation=(
                "Verifique se o device responde em 'adb devices' "
                "(emulador iniciado, celular desbloqueado)."
            ),
        )

    except OSError as erro:
        log_error(
            logger,
            "Não foi possível executar o adb",
            event="android_app_cleanup_os_error",
            udid=device_udid,
            app_package=app_package,
            error=str(erro),
            remediation=(
                "Verifique se o Android SDK platform-tools está no PATH "
                "(make doctor)."
            ),
        )


def _resolve_appium_server(
    device: dict | None,
    settings: Settings,
) -> str:
    """
    Resolve a URL do servidor Appium.

    Prioridade:
    1. Porta definida no device usado na execução paralela.
    2. APPIUM_PORT (padrão 4723).
    """
    if device and "appium_port" in device:
        port = int(device["appium_port"])
    else:
        port = settings.execucao.appium_port

    return f"http://127.0.0.1:{port}"


# === Driver factory ===
def create_driver(
    profile: LaunchProfile,
    device: dict | None = None,
    settings: Settings | None = None,
) -> webdriver.Remote:
    """
    Cria e retorna uma sessão Appium para execução Android.

    Args:
        profile:
            Estado em que o app deve subir: cold start ou sessão morna.

        device:
            Configuração carregada do devices.yaml na execução
            paralela. Quando None, usa o env.<device>.yaml.

        settings:
            Configuração já carregada. Quando None, lê do ambiente.

    Responsabilidades:
    - Resolver o servidor Appium.
    - Montar capabilities a partir do perfil.
    - Desinstalar o app no cold start (APP_SOURCE=apk).
    - Criar a sessão Appium.

    Relaunch do app é responsabilidade do AppSession.
    """
    appium_server = "<não resolvido>"

    try:
        settings = settings or Settings.from_env()

        appium_server = _resolve_appium_server(device, settings)

        options = get_android_options(
            profile=profile,
            device=device,
            settings=settings,
        )

        capabilities = options.capabilities

        app_package = str(
            capabilities.get("appium:appPackage") or settings.app.package
        ).strip()

        udid_value = capabilities.get("appium:udid") or capabilities.get(
            "udid"
        )

        udid = str(udid_value).strip() if udid_value else None

        if profile.cold_start:
            _cleanup_android_app(
                device_udid=udid,
                app_package=app_package,
                app_source=settings.app_source,
            )

        log_event(
            logger,
            "Preparando sessão Appium para Android",
            event="driver_prepare",
            platform="android",
            automation_name="UiAutomator2",
            cold_start=profile.cold_start,
            manter_estado=profile.manter_estado,
            is_emulator=settings.is_emulator,
            app_source=settings.app_source,
            permissions=sorted(profile.permissions),
            app_package=app_package,
            device_name=capabilities.get("appium:deviceName"),
            platform_version=capabilities.get("appium:platformVersion"),
            app=capabilities.get("appium:app"),
            udid=udid,
            appium_server=appium_server,
        )

        log_event(
            logger,
            "Iniciando sessão Appium",
            event="driver_start",
            platform="android",
            appium_server=appium_server,
            capabilities=capabilities,
        )

        driver = webdriver.Remote(
            command_executor=appium_server,
            options=options,
        )

        driver.implicitly_wait(0)

        log_event(
            logger,
            "Sessão Appium iniciada com sucesso",
            event="driver_started",
            platform="android",
            cold_start=profile.cold_start,
            appium_server=appium_server,
            session_id=driver.session_id,
        )

        return driver

    except WebDriverException as erro:
        log_error(
            logger,
            "Falha ao criar sessão Appium",
            event="driver_start_error",
            platform="android",
            cold_start=profile.cold_start,
            appium_server=appium_server,
            error=str(erro),
            remediation=(
                "Verifique: Appium /status, driver uiautomator2, "
                "'adb devices', appPackage/appActivity e o APK "
                "configurado."
            ),
        )
        raise

    except Exception as erro:
        log_error(
            logger,
            "Erro inesperado ao criar driver",
            event="driver_unexpected_error",
            platform="android",
            cold_start=profile.cold_start,
            appium_server=appium_server,
            error=str(erro),
        )
        raise
