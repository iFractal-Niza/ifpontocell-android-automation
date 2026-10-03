import pytest

from config.capabilities import get_android_options
from core.launch_profile import LaunchProfile


@pytest.fixture
def apk_falso(tmp_path):
    apk = tmp_path / "ifPontoCell.apk"
    apk.write_bytes(b"")
    return apk


@pytest.fixture
def emulador(ambiente, apk_falso):
    ambiente["ANDROID_TARGET"] = "emulator"
    ambiente["APP_SOURCE"] = "apk"
    ambiente["APP_PATH"] = str(apk_falso)
    return ambiente


@pytest.fixture
def device_real(ambiente):
    ambiente["ANDROID_TARGET"] = "real"
    ambiente["APP_SOURCE"] = "package"
    ambiente["ANDROID_UDID"] = "R58N12ABCDE"
    return ambiente


def _caps(profile=None, device=None) -> dict:
    return get_android_options(
        profile or LaunchProfile(),
        device=device,
    ).capabilities


def test_emulador_usa_apk_local_e_defaults(emulador, apk_falso):
    caps = _caps()

    assert caps["platformName"] == "Android"
    assert caps["appium:automationName"] == "UiAutomator2"
    assert caps["appium:app"] == str(apk_falso.resolve())
    assert caps["appium:appPackage"] == "br.com.ifractal.Stou"
    assert caps["appium:appWaitActivity"] == "*"
    assert caps["appium:autoGrantPermissions"] is True
    assert caps["appium:disableWindowAnimation"] is True
    assert "appium:udid" not in caps
    assert "appium:systemPort" not in caps


def test_apk_inexistente_falha(emulador, tmp_path):
    emulador["APP_PATH"] = str(tmp_path / "nao_existe.apk")

    with pytest.raises(FileNotFoundError, match="APK não encontrado"):
        _caps()


def test_package_nao_envia_app(emulador):
    emulador["APP_SOURCE"] = "package"

    assert "appium:app" not in _caps()


def test_device_config_sobrepoe_env_no_paralelo(emulador):
    caps = _caps(
        device={
            "name": "Pixel 7",
            "os_version": "14",
            "udid": "emulator-5556",
            "system_port": 8202,
        }
    )

    assert caps["appium:deviceName"] == "Pixel 7"
    assert caps["appium:platformVersion"] == "14"
    assert caps["appium:udid"] == "emulator-5556"
    assert caps["appium:systemPort"] == 8202


def test_device_config_incompleto_falha(emulador):
    with pytest.raises(ValueError, match="udid"):
        _caps(device={"name": "Pixel 7"})


def test_cold_start_limpa_os_dados(emulador):
    emulador["ANDROID_NO_RESET"] = "true"

    caps = _caps(LaunchProfile(cold_start=True))

    assert caps["appium:noReset"] is False
    assert caps["appium:fullReset"] is False


def test_sem_cold_start_respeita_env(emulador):
    emulador["ANDROID_NO_RESET"] = "true"

    caps = _caps(LaunchProfile(cold_start=False))

    assert caps["appium:noReset"] is True


def test_booleano_invalido_falha(emulador):
    emulador["ANDROID_AUTO_GRANT_PERMISSIONS"] = "sim"

    with pytest.raises(ValueError, match="ANDROID_AUTO_GRANT_PERMISSIONS"):
        _caps()


def test_device_real_com_package(device_real):
    caps = _caps()

    assert caps["appium:udid"] == "R58N12ABCDE"
    assert "appium:app" not in caps


def test_device_real_tem_system_port_proprio(device_real):
    # Emulador e celular no mesmo Appium: portas do UiAutomator2
    # diferentes, como o WebDriverAgent no iOS (8100 e 8101).
    device_real["ANDROID_SYSTEM_PORT"] = "8201"

    assert _caps()["appium:systemPort"] == 8201


def test_device_real_exige_udid(device_real):
    del device_real["ANDROID_UDID"]

    with pytest.raises(ValueError, match="ANDROID_UDID"):
        _caps()


def test_android_target_invalido_falha(ambiente):
    ambiente["ANDROID_TARGET"] = "ios"

    with pytest.raises(ValueError, match="ANDROID_TARGET inválido"):
        _caps()


# === Animações ===
def test_animacoes_podem_ser_mantidas(emulador):
    emulador["ANDROID_DISABLE_WINDOW_ANIMATION"] = "false"

    assert _caps()["appium:disableWindowAnimation"] is False


# === Sessão morna ===
def test_manter_estado_forca_no_reset(emulador):
    emulador["ANDROID_NO_RESET"] = "false"

    caps = _caps(LaunchProfile(manter_estado=True))

    assert caps["appium:noReset"] is True
    assert caps["appium:fullReset"] is False


def test_manter_estado_em_device_real(device_real):
    caps = _caps(LaunchProfile(manter_estado=True))

    assert caps["appium:noReset"] is True
