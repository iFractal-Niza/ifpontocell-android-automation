import os
import subprocess

from appium import webdriver
from selenium.common.exceptions import WebDriverException

from config.capabilities import get_android_options, get_app_package
from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_error, log_event


DEFAULT_APPIUM_PORT = 4723
logger = get_logger("driver_factory")


def _resolve_appium_server(device: dict | None) -> str:
    if device and "appium_port" in device:
        port = int(device["appium_port"])
    else:
        port = int(os.getenv("APPIUM_PORT", str(DEFAULT_APPIUM_PORT)))

    return f"http://127.0.0.1:{port}"


def _cleanup_android_app(
    device_udid: str | None,
    app_package: str,
    app_source: str,
) -> None:
    """Remove o app antes de cold start quando o APK será reinstalado."""
    if app_source != "apk":
        log_event(
            logger,
            "Cold start sem desinstalação: APP_SOURCE não é apk",
            event="android_cleanup_skipped",
            app_source=app_source,
            app_package=app_package,
        )
        return

    adb = "adb"
    command = [adb]
    if device_udid:
        command += ["-s", device_udid]
    command += ["uninstall", app_package]

    try:
        result = subprocess.run(
            command,
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
            return_code=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        log_error(
            logger,
            "Falha ao limpar app Android antes do cold start",
            event="android_app_cleanup_error",
            udid=device_udid,
            app_package=app_package,
            error=str(error),
            remediation=(
                "Verifique se o adb está no PATH e se o device aparece em "
                "'adb devices'."
            ),
        )
        raise


def create_driver(
    profile: LaunchProfile,
    device: dict | None = None,
) -> webdriver.Remote:
    """Cria uma sessão Appium Android usando UiAutomator2."""
    appium_server = "<não resolvido>"

    try:
        appium_server = _resolve_appium_server(device)
        options = get_android_options(profile=profile, device=device)
        capabilities = options.capabilities

        app_package = str(
            capabilities.get("appium:appPackage")
            or capabilities.get("appPackage")
            or get_app_package()
        ).strip()

        udid_value = (
            capabilities.get("appium:udid")
            or capabilities.get("udid")
        )
        udid = str(udid_value).strip() if udid_value else None
        app_source = os.getenv("APP_SOURCE", "apk").strip().lower()

        if profile.cold_start:
            _cleanup_android_app(
                device_udid=udid,
                app_package=app_package,
                app_source=app_source,
            )

        log_event(
            logger,
            "Preparando sessão Appium para Android",
            event="driver_prepare",
            platform="android",
            automation_name="UiAutomator2",
            cold_start=profile.cold_start,
            app_source=app_source,
            app_package=app_package,
            device_name=capabilities.get("appium:deviceName"),
            platform_version=capabilities.get("appium:platformVersion"),
            udid=udid,
            appium_server=appium_server,
        )

        driver = webdriver.Remote(
            command_executor=appium_server,
            options=options,
        )
        driver.implicitly_wait(0)

        log_event(
            logger,
            "Sessão Appium Android iniciada",
            event="driver_started",
            platform="android",
            appium_server=appium_server,
            session_id=driver.session_id,
        )
        return driver

    except WebDriverException as error:
        log_error(
            logger,
            "Falha ao criar sessão Appium Android",
            event="driver_start_error",
            platform="android",
            appium_server=appium_server,
            error=str(error),
            remediation=(
                "Verifique: Appium /status, driver uiautomator2, 'adb devices', "
                "appPackage/appActivity e o APK configurado."
            ),
        )
        raise
