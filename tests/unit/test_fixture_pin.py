"""
PIN novo do teste de Alterar Senha (tests.fixtures.pin.ler_pin_novo), lido
de APP_PIN_NOVO no env.<device>.yaml.
"""

from config.settings import CredenciaisApp
from tests.fixtures.pin import ler_pin_invalido, ler_pin_novo


def test_pin_novo_configurado():
    assert ler_pin_novo("2222", "1111") == ("2222", "")


def test_pin_novo_ausente_pula_com_o_motivo():
    pin, motivo = ler_pin_novo("", "1111")

    assert pin == ""
    assert "APP_PIN_NOVO não configurado no config/env.<device>.yaml" in motivo


def test_pin_novo_igual_ao_atual_pula():
    pin, motivo = ler_pin_novo("1111", "1111")

    assert pin == ""
    assert "igual ao APP_PIN" in motivo


def test_settings_le_app_pin_novo_do_env():
    credenciais = CredenciaisApp.from_env(
        {"APP_PIN": "1111", "APP_PIN_NOVO": "2222"}
    )

    assert (credenciais.pin, credenciais.pin_novo) == ("1111", "2222")


def test_pin_invalido_configurado():
    assert ler_pin_invalido({"APP_PIN_INVALIDO": "3333"}, "1111", "2222") == (
        "3333",
        "",
    )


def test_pin_invalido_igual_ao_novo_pula():
    # Caso real: APP_PIN_INVALIDO era 2222, igual ao APP_PIN_NOVO.
    pin, motivo = ler_pin_invalido(
        {"APP_PIN_INVALIDO": "2222"}, "1111", "2222"
    )

    assert pin == ""
    assert "diferente do APP_PIN e do APP_PIN_NOVO" in motivo


def test_pin_invalido_ausente_pula():
    assert ler_pin_invalido({}, "1111", "2222")[0] == ""


# === Senha nova do sistema (tests.fixtures.senha_sistema) ===
def test_senha_nova_configurada():
    from tests.fixtures.senha_sistema import ler_senha_nova

    assert ler_senha_nova("Nova123", "Atual123") == ("Nova123", "")


def test_senha_nova_ausente_ou_igual_pula():
    from tests.fixtures.senha_sistema import ler_senha_nova

    assert "não configurada" in ler_senha_nova("", "Atual123")[1]
    assert "igual à APP_PASSWORD" in ler_senha_nova("Atual123", "Atual123")[1]


def test_settings_le_app_password_nova_do_env():
    credenciais = CredenciaisApp.from_env({"APP_PASSWORD_NOVA": "Nova123"})

    assert credenciais.senha_nova == "Nova123"
