"""
Leitura e validação da configuração (config.settings).

Os testes passam o ambiente como dict para from_env(env), sem tocar em
os.environ.
"""

import pytest

from config.settings import (
    APP_PACKAGE_PADRAO,
    PROJECT_ROOT,
    ApiConfig,
    ConfiguracaoInvalida,
    CredenciaisApp,
    GeoDelimitacao,
    Localizacao,
    Settings,
    ler_android_target,
)

DEVICE_REAL = {
    "ANDROID_TARGET": "real",
    "APP_SOURCE": "package",
    "ANDROID_UDID": "R58N12ABCDE",
}


def _erros(env: dict) -> list[str]:
    with pytest.raises(ConfiguracaoInvalida) as erro:
        Settings.from_env(env)

    return erro.value.erros


# === Defaults ===
def test_ambiente_vazio_usa_defaults_de_emulador():
    settings = Settings.from_env({})

    assert settings.android_target == "emulator"
    assert settings.is_emulator
    assert settings.app_source == "package"
    assert settings.apk_path == PROJECT_ROOT / "app" / "ifPontoCell.apk"
    assert settings.app.package == APP_PACKAGE_PADRAO
    assert settings.app.wait_activity == "*"
    assert settings.device.udid == ""
    assert settings.localizacao is None
    assert settings.execucao.appium_port == 4723
    assert settings.execucao.auto_grant_permissions is True
    assert settings.execucao.disable_window_animation is True
    assert settings.execucao.system_port is None


def test_valores_sao_normalizados():
    settings = Settings.from_env(
        {"ANDROID_TARGET": "  EMULATOR ", "ANDROID_UDID": " emulator-5554 "}
    )

    assert settings.android_target == "emulator"
    assert settings.device.udid == "emulator-5554"


# === Booleanos ===
@pytest.mark.parametrize("valor", ["true", "1", "yes", "on", "TRUE"])
def test_booleanos_verdadeiros(valor):
    settings = Settings.from_env({"ANDROID_NO_RESET": valor})

    assert settings.execucao.no_reset is True


@pytest.mark.parametrize("valor", ["false", "0", "no", "off"])
def test_booleanos_falsos(valor):
    settings = Settings.from_env({"ANDROID_AUTO_GRANT_PERMISSIONS": valor})

    assert settings.execucao.auto_grant_permissions is False


def test_booleano_invalido_e_erro():
    assert any(
        "ANDROID_NO_RESET" in erro
        for erro in _erros({"ANDROID_NO_RESET": "sim"})
    )


# === Inteiros ===
@pytest.mark.parametrize("valor", ["abc", "0", "-5"])
def test_inteiro_invalido_ou_abaixo_do_minimo(valor):
    erros = _erros({"ANDROID_NEW_COMMAND_TIMEOUT": valor})

    assert any("ANDROID_NEW_COMMAND_TIMEOUT" in erro for erro in erros)


def test_system_port_opcional_e_lido():
    settings = Settings.from_env({"ANDROID_SYSTEM_PORT": "8201"})

    assert settings.execucao.system_port == 8201


def test_system_port_invalido_e_erro():
    assert any(
        "ANDROID_SYSTEM_PORT" in erro
        for erro in _erros({"ANDROID_SYSTEM_PORT": "porta"})
    )


# === Alvo e origem do app ===
def test_android_target_invalido():
    assert any(
        "ANDROID_TARGET inválido" in erro
        for erro in _erros({"ANDROID_TARGET": "ios"})
    )


def test_app_source_invalido():
    assert any(
        "APP_SOURCE inválido" in erro for erro in _erros({"APP_SOURCE": "app"})
    )


def test_apk_exige_arquivo_apk():
    erros = _erros({"APP_SOURCE": "apk", "APP_PATH": "/tmp/ifPontoCell.app"})

    assert any(
        "APP_PATH deve apontar para um arquivo .apk" in e for e in erros
    )


def test_package_nao_confere_o_apk():
    settings = Settings.from_env(
        {"APP_SOURCE": "package", "APP_PATH": "/tmp/qualquer.app"}
    )

    assert settings.app_source == "package"


def test_app_path_configurado():
    settings = Settings.from_env({"APP_PATH": "/tmp/Outro.apk"})

    assert settings.apk_path.name == "Outro.apk"


# === Celular (device real) ===
def test_device_real_completo():
    settings = Settings.from_env(DEVICE_REAL)

    assert not settings.is_emulator
    assert settings.device.udid == "R58N12ABCDE"


def test_device_real_exige_udid():
    erros = _erros({"ANDROID_TARGET": "real"})

    assert any("ANDROID_UDID" in erro for erro in erros)


def test_erros_sao_acumulados():
    with pytest.raises(ConfiguracaoInvalida) as erro:
        Settings.from_env(
            {"ANDROID_TARGET": "x", "ANDROID_NO_RESET": "talvez"}
        )

    mensagem = str(erro.value)

    assert "ANDROID_TARGET" in mensagem
    assert "ANDROID_NO_RESET" in mensagem


# === Localização simulada ===
def test_localizacao_habilitada():
    settings = Settings.from_env(
        {
            "ANDROID_LOCATION_ENABLED": "true",
            "ANDROID_LOCATION_LATITUDE": "-23.6167",
            "ANDROID_LOCATION_LONGITUDE": "-46.6372",
        }
    )

    assert settings.localizacao == Localizacao(-23.6167, -46.6372)


def test_localizacao_desligada_com_coordenadas_e_sinalizada():
    settings = Settings.from_env(
        {
            "ANDROID_LOCATION_ENABLED": "false",
            "ANDROID_LOCATION_LATITUDE": "-23.6167",
        }
    )

    assert settings.localizacao is None
    assert settings.localizacao_desligada_com_coordenadas


def test_localizacao_desligada_nao_valida_coordenadas():
    settings = Settings.from_env(
        {
            "ANDROID_LOCATION_ENABLED": "false",
            "ANDROID_LOCATION_LATITUDE": "abc",
        }
    )

    assert settings.localizacao is None


def test_localizacao_vale_tambem_no_device_real():
    settings = Settings.from_env(
        {
            **DEVICE_REAL,
            "ANDROID_LOCATION_ENABLED": "true",
            "ANDROID_LOCATION_LATITUDE": "-23.6167",
            "ANDROID_LOCATION_LONGITUDE": "-46.6372",
        }
    )

    assert settings.localizacao is not None


def test_localizacao_habilitada_sem_coordenadas_e_erro():
    erros = _erros({"ANDROID_LOCATION_ENABLED": "true"})

    assert any("ANDROID_LOCATION_LATITUDE" in erro for erro in erros)


@pytest.mark.parametrize(
    ("latitude", "longitude", "mensagem"),
    [
        ("91", "0", "ANDROID_LOCATION_LATITUDE deve estar entre -90 e 90"),
        (
            "0",
            "-181",
            "ANDROID_LOCATION_LONGITUDE deve estar entre -180 e 180",
        ),
        ("abc", "0", "ANDROID_LOCATION_LATITUDE deve ser uma coordenada"),
    ],
)
def test_coordenadas_invalidas(latitude, longitude, mensagem):
    erros = _erros(
        {
            "ANDROID_LOCATION_ENABLED": "true",
            "ANDROID_LOCATION_LATITUDE": latitude,
            "ANDROID_LOCATION_LONGITUDE": longitude,
        }
    )

    assert any(mensagem in erro for erro in erros)


# === Grupos sem validação ===
def test_api_e_credenciais_nunca_levantam():
    # Vazios são aceitos: a obrigatoriedade é checada por quem usa.
    assert ApiConfig.from_env({}).base_url == ""
    assert CredenciaisApp.from_env({}).pin == ""


def test_api_e_credenciais_sao_lidas():
    env = {
        "API_BASE_URL": "https://api",
        "MONITOR_NOME_PESSOA": "TesterN95",
        "APP_SYSTEM": "exemplo",
        "APP_PIN": "1234",
    }

    settings = Settings.from_env(env)

    assert settings.api.base_url == "https://api"
    assert settings.api.monitor_nome_pessoa == "TesterN95"
    assert settings.credenciais.sistema == "exemplo"
    assert settings.credenciais.pin == "1234"


# === Resolver leve do alvo ===
def test_ler_android_target_ignora_outros_erros():
    # is_emulator() não pode falhar por causa de outra variável.
    assert ler_android_target(
        {"ANDROID_TARGET": "real", "ANDROID_NO_RESET": "x"}
    ) == ("real")


def test_ler_android_target_invalido():
    with pytest.raises(ConfiguracaoInvalida, match="ANDROID_TARGET"):
        ler_android_target({"ANDROID_TARGET": "ios"})


# === Geo delimitação (ANDROID_GEO_*) ===
GEO = {
    "ANDROID_GEO_DENTRO_LATITUDE": "-23.5505",
    "ANDROID_GEO_DENTRO_LONGITUDE": "-46.6333",
    "ANDROID_GEO_FORA_LATITUDE": "-22.9068",
    "ANDROID_GEO_FORA_LONGITUDE": "-43.1729",
}


def test_geo_com_as_quatro_coordenadas():
    geo = Settings.from_env(GEO).geo

    assert geo == GeoDelimitacao(
        dentro=Localizacao(-23.5505, -46.6333),
        fora=Localizacao(-22.9068, -43.1729),
    )


def test_geo_sem_coordenadas_e_opcional():
    assert Settings.from_env({}).geo is None


def test_geo_pela_metade_e_erro():
    env = dict(GEO)
    del env["ANDROID_GEO_FORA_LONGITUDE"]

    erros = _erros(env)

    assert any("ANDROID_GEO_FORA_LONGITUDE" in erro for erro in erros)


def test_geo_com_coordenada_invalida_e_erro():
    erros = _erros({**GEO, "ANDROID_GEO_FORA_LATITUDE": "95"})

    assert any("ANDROID_GEO_FORA_LATITUDE" in erro for erro in erros)


def test_geo_vale_tambem_no_device_real():
    assert Settings.from_env({**DEVICE_REAL, **GEO}).geo is not None


# === Jornada do usuário (tela Ponto) ===
def test_jornada_configurada():
    settings = Settings.from_env({"APP_JORNADA": "08:00 12:00 13:00 18:00"})

    assert settings.credenciais.jornada == ("08:00", "12:00", "13:00", "18:00")


def test_jornada_vazia_nao_e_erro():
    assert Settings.from_env({}).credenciais.jornada == ()


def test_jornada_fora_do_formato_e_erro_de_configuracao():
    assert any(
        "APP_JORNADA" in erro for erro in _erros({"APP_JORNADA": "8h 12h"})
    )
