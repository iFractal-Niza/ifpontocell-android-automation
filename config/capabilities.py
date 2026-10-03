"""
Tradução da configuração (config.settings.Settings) em capabilities do
Appium/UiAutomator2.

Não lê variáveis de ambiente: leitura, defaults e validação de formato
ficam no Settings.
"""

from appium.options.android import UiAutomator2Options

from config.settings import Settings, ler_android_target
from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_error, log_event

logger = get_logger("capabilities")


# === Resolvers públicos de ambiente ===
def is_emulator() -> bool:
    """
    Indica se a execução é em emulador.

    Lê só o ANDROID_TARGET: é consultado em vários pontos que não devem
    falhar por causa de outra variável inválida.
    """
    return ler_android_target() == "emulator"


# === Validações ===
def _validar_apk_local(settings: Settings) -> str:
    """
    O APK precisa existir no disco no momento de montar a sessão.
    """
    apk_path = settings.apk_path

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

    return str(apk_path)


def _validate_device_config(device: dict) -> None:
    required_fields = {
        "name",
        "udid",
    }

    missing_fields = sorted(
        field
        for field in required_fields
        if not str(device.get(field, "")).strip()
    )

    if not missing_fields:
        return

    fields = ", ".join(missing_fields)

    log_error(
        logger,
        "Configuração de device incompleta",
        event="invalid_device_config",
        missing_fields=fields,
    )

    raise ValueError(
        f"Configuração do device incompleta. "
        f"Campos obrigatórios ausentes: {fields}."
    )


# === Capabilities base ===
def _set_base_capabilities(
    options: UiAutomator2Options,
    settings: Settings,
) -> None:
    options.set_capability("platformName", "Android")
    options.set_capability("appium:automationName", "UiAutomator2")

    options.set_capability("appium:appPackage", settings.app.package)
    options.set_capability("appium:appActivity", settings.app.activity)
    options.set_capability(
        "appium:appWaitActivity", settings.app.wait_activity
    )


# === Capabilities do device ===
def _set_device_capabilities(
    options: UiAutomator2Options,
    settings: Settings,
    device: dict | None = None,
) -> None:
    """
    Emulador ou celular: env.<device>.yaml ou, na execução paralela, a
    entrada do devices.yaml.
    """
    if device is not None:
        _validate_device_config(device)

        device_name = str(device["name"]).strip()
        udid = str(device["udid"]).strip()
        platform_version = str(device.get("os_version", "")).strip()

        options.set_capability("appium:deviceName", device_name)
        options.set_capability("appium:udid", udid)

        if platform_version:
            options.set_capability("appium:platformVersion", platform_version)

        if device.get("system_port"):
            options.set_capability(
                "appium:systemPort", int(device["system_port"])
            )

        log_event(
            logger,
            "Capabilities do device carregadas via device config",
            event="device_capabilities_from_device",
            device_name=device_name,
            os_version=platform_version,
            udid=udid,
            appium_port=device.get("appium_port"),
        )
        return

    config = settings.device

    if config.udid:
        options.set_capability("appium:udid", config.udid)

    if config.device_name:
        options.set_capability("appium:deviceName", config.device_name)

    if config.platform_version:
        options.set_capability(
            "appium:platformVersion", config.platform_version
        )

    if settings.execucao.system_port is not None:
        options.set_capability(
            "appium:systemPort", settings.execucao.system_port
        )


# === Origem do app ===
def _set_app_source_capabilities(
    options: UiAutomator2Options,
    settings: Settings,
) -> None:
    if settings.app_source == "package":
        log_event(
            logger,
            "Capabilities carregadas com o app já instalado",
            event="capabilities_loaded",
            platform="android",
            android_target=settings.android_target,
            app_source="package",
            app_package=settings.app.package,
        )
        return

    apk_path = _validar_apk_local(settings)

    options.set_capability("appium:app", apk_path)

    log_event(
        logger,
        "Capabilities carregadas com APK local",
        event="capabilities_loaded",
        platform="android",
        android_target=settings.android_target,
        app_source="apk",
        app_path=apk_path,
    )


# === Estratégia de execução ===
def _set_execution_capabilities(
    options: UiAutomator2Options,
    settings: Settings,
    profile: LaunchProfile,
) -> None:
    execucao = settings.execucao

    if profile.manter_estado:
        # Sessão morna: app instalado e logado da execução anterior.
        options.set_capability("appium:noReset", True)
        options.set_capability("appium:fullReset", False)
    elif profile.cold_start:
        # noReset=false limpa os dados do app (pm clear) antes da sessão:
        # vale também para APP_SOURCE=package, que não é desinstalado.
        options.set_capability("appium:noReset", False)
        options.set_capability("appium:fullReset", False)
    else:
        options.set_capability("appium:noReset", execucao.no_reset)
        options.set_capability("appium:fullReset", execucao.full_reset)

    options.set_capability(
        "appium:autoGrantPermissions", execucao.auto_grant_permissions
    )
    options.set_capability(
        "appium:disableWindowAnimation", execucao.disable_window_animation
    )
    options.set_capability(
        "appium:ignoreHiddenApiPolicyError",
        execucao.ignore_hidden_api_policy_error,
    )
    options.set_capability(
        "appium:newCommandTimeout", execucao.new_command_timeout
    )
    options.set_capability(
        "appium:waitForIdleTimeout", execucao.wait_for_idle_timeout
    )

    # O app sobe com a sessão; relaunch é do AppSession.
    options.set_capability("appium:autoLaunch", True)


# === Construção das opções Android ===
def get_android_options(
    profile: LaunchProfile,
    device: dict | None = None,
    settings: Settings | None = None,
) -> UiAutomator2Options:
    """
    Monta as capabilities Android a partir do perfil de lançamento.

    Args:
        profile:
            Estado em que o app deve subir: cold start ou sessão morna.
            Permissões não viram capability própria: o
            autoGrantPermissions concede as do manifest na instalação.

        device:
            Configuração do devices.yaml na execução paralela.
            Quando None, usa o env.<device>.yaml.

        settings:
            Configuração já carregada. Quando None, lê do ambiente
            (levanta ConfiguracaoInvalida se houver erro de formato).
    """
    try:
        settings = settings or Settings.from_env()

        options = UiAutomator2Options()

        _set_base_capabilities(options, settings)

        _set_device_capabilities(options, settings, device=device)

        _set_app_source_capabilities(options, settings)

        _set_execution_capabilities(options, settings, profile)

        log_event(
            logger,
            "Capabilities Android montadas com sucesso",
            event="capabilities_ready",
            platform="android",
            cold_start=profile.cold_start,
            manter_estado=profile.manter_estado,
            android_target=settings.android_target,
            app_source=settings.app_source,
            app_package=settings.app.package,
            app_activity=settings.app.activity,
            device_name=options.capabilities.get("appium:deviceName"),
            platform_version=options.capabilities.get(
                "appium:platformVersion"
            ),
            udid=options.capabilities.get("appium:udid"),
            app=options.capabilities.get("appium:app"),
            no_reset=options.capabilities.get("appium:noReset"),
            full_reset=options.capabilities.get("appium:fullReset"),
            system_port=options.capabilities.get("appium:systemPort"),
        )

        return options

    except Exception as exc:
        log_error(
            logger,
            "Erro ao montar capabilities",
            event="capabilities_error",
            error=str(exc),
        )
        raise
