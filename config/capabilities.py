import os
from pathlib import Path

from appium.options.android import UiAutomator2Options

from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_error, log_event


logger = get_logger("capabilities")

VALID_ANDROID_TARGETS = {"emulator", "real"}
VALID_APP_SOURCES = {"apk", "package"}


# === Helpers de ambiente ===
def _get_env(env_name: str, default: str = "") -> str:
    return os.getenv(env_name, default).strip()


def _get_required_env(env_name: str) -> str:
    value = _get_env(env_name)
    if value:
        return value

    log_error(
        logger,
        "Variável obrigatória não configurada",
        event="required_env_not_found",
        env_name=env_name,
    )
    raise ValueError(
        f"{env_name} não configurado. "
        "Adicione a variável ao arquivo config/env.yaml."
    )


def _get_bool_env(env_name: str, default: str = "false") -> bool:
    value = _get_env(env_name, default).lower()
    if value not in {"true", "false"}:
        raise ValueError(
            f"{env_name} deve possuir o valor 'true' ou 'false'. "
            f"Valor atual: {value!r}."
        )
    return value == "true"


def _get_int_env(env_name: str, default: int, minimum: int | None = None) -> int:
    raw_value = _get_env(env_name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{env_name} deve possuir um valor inteiro. "
            f"Valor atual: {raw_value!r}."
        ) from exc

    if minimum is not None and value < minimum:
        raise ValueError(
            f"{env_name} deve ser maior ou igual a {minimum}. "
            f"Valor atual: {value}."
        )
    return value


# === Resolução do alvo ===
def _get_android_target() -> str:
    target = _get_env("ANDROID_TARGET", "emulator").lower()
    if target in VALID_ANDROID_TARGETS:
        return target
    raise ValueError(
        "ANDROID_TARGET inválido. Use 'emulator' ou 'real'."
    )


def _get_app_source() -> str:
    source = _get_env("APP_SOURCE", "apk").lower()
    if source in VALID_APP_SOURCES:
        return source
    raise ValueError(
        "APP_SOURCE inválido. Use 'apk' ou 'package'."
    )


def is_emulator() -> bool:
    return _get_android_target() == "emulator"


def get_app_package() -> str:
    return _get_env("ANDROID_APP_PACKAGE", "br.com.ifractal.Stou")


# === App/APK ===
def _get_apk_path() -> str:
    project_root = Path(__file__).resolve().parent.parent
    configured = _get_env("APP_PATH")
    apk_path = Path(
        configured or project_root / "app" / "ifPontoCell.apk"
    ).expanduser().resolve()

    if not apk_path.is_file():
        log_error(
            logger,
            "APK não encontrado",
            event="apk_not_found",
            path=str(apk_path),
        )
        raise FileNotFoundError(
            f"APK não encontrado em: {apk_path}. "
            "Adicione o arquivo ou ajuste APP_PATH."
        )

    if apk_path.suffix.lower() != ".apk":
        raise ValueError(
            f"APP_PATH deve apontar para um arquivo .apk: {apk_path}"
        )

    return str(apk_path)


# === Devices ===
def _validate_device_config(device: dict) -> None:
    missing = [
        field
        for field in ("name", "udid")
        if not str(device.get(field, "")).strip()
    ]
    if missing:
        raise ValueError(
            "Configuração do device incompleta. "
            f"Campos obrigatórios ausentes: {', '.join(missing)}."
        )


def _resolve_device(options: UiAutomator2Options, device: dict | None) -> None:
    if device is not None:
        _validate_device_config(device)
        options.set_capability("appium:deviceName", str(device["name"]).strip())
        options.set_capability("appium:udid", str(device["udid"]).strip())

        os_version = str(device.get("os_version", "")).strip()
        if os_version:
            options.set_capability("appium:platformVersion", os_version)
        return

    udid = _get_env("ANDROID_UDID")
    if udid:
        options.set_capability("appium:udid", udid)

    device_name = _get_env("ANDROID_DEVICE_NAME")
    if device_name:
        options.set_capability("appium:deviceName", device_name)

    platform_version = _get_env("ANDROID_PLATFORM_VERSION")
    if platform_version:
        options.set_capability("appium:platformVersion", platform_version)


# === Capabilities públicas ===
def get_android_options(
    profile: LaunchProfile,
    device: dict | None = None,
) -> UiAutomator2Options:
    options = UiAutomator2Options()

    options.set_capability("platformName", "Android")
    options.set_capability("appium:automationName", "UiAutomator2")

    app_package = get_app_package()
    app_activity = _get_env(
        "ANDROID_APP_ACTIVITY",
        "br.com.ifractal.stou.view.MainActivity",
    )

    options.set_capability("appium:appPackage", app_package)
    options.set_capability("appium:appActivity", app_activity)
    options.set_capability(
        "appium:appWaitActivity",
        _get_env("ANDROID_APP_WAIT_ACTIVITY", "*"),
    )

    _resolve_device(options, device)

    source = _get_app_source()
    if source == "apk":
        options.set_capability("appium:app", _get_apk_path())

    options.set_capability(
        "appium:noReset",
        _get_bool_env("ANDROID_NO_RESET", "false"),
    )
    options.set_capability(
        "appium:fullReset",
        _get_bool_env("ANDROID_FULL_RESET", "false"),
    )
    options.set_capability(
        "appium:autoGrantPermissions",
        _get_bool_env("ANDROID_AUTO_GRANT_PERMISSIONS", "true"),
    )
    options.set_capability(
        "appium:disableWindowAnimation",
        _get_bool_env("ANDROID_DISABLE_WINDOW_ANIMATION", "true"),
    )
    options.set_capability(
        "appium:ignoreHiddenApiPolicyError",
        _get_bool_env("ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR", "true"),
    )
    options.set_capability(
        "appium:newCommandTimeout",
        _get_int_env("ANDROID_NEW_COMMAND_TIMEOUT", 120, minimum=1),
    )
    options.set_capability(
        "appium:waitForIdleTimeout",
        _get_int_env("ANDROID_WAIT_FOR_IDLE_TIMEOUT", 500, minimum=0),
    )

    # O framework controla o ciclo de vida pelo AppSession.
    options.set_capability("appium:autoLaunch", True)

    log_event(
        logger,
        "Capabilities Android montadas",
        event="android_capabilities_built",
        target=_get_android_target(),
        app_source=source,
        app_package=app_package,
        app_activity=app_activity,
        udid=options.capabilities.get("appium:udid"),
        cold_start=profile.cold_start,
    )

    return options
