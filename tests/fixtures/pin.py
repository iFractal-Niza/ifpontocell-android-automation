"""
Troca do PIN (Alterar PIN, aba 4 dígitos da tela Alterar Senha): o PIN
novo vem do env.<device>.yaml (APP_PIN_NOVO) e uma rede de segurança
devolve o PIN original se o teste falhar no meio.

O PIN fica só no aparelho, mas é o que todos os outros testes usam para
desbloquear: se o app ficar com o PIN novo, a suíte inteira quebra no
desbloqueio. Errar o PIN não bloqueia o app (os dígitos tremem e ele
pede de novo), então dá para descobrir qual PIN vale tentando o novo.
"""

from dataclasses import dataclass

import pytest

from config.settings import CredenciaisApp
from pages.alterar_senha.alterar_pin_page import AlterarPinPage
from pages.autenticacao.unlock_page import UnlockPage
from pages.home_page import HomePage
from utils.logger import get_logger

logger = get_logger("fixture_pin")

CHAVE_PIN_NOVO = "APP_PIN_NOVO"


def ler_pin_novo(pin_novo: str, app_pin: str) -> tuple[str, str]:
    """
    (PIN novo, motivo para pular). Motivo vazio quando o PIN serve.
    """
    pin = (pin_novo or "").strip()

    if not pin:
        return "", (
            f"{CHAVE_PIN_NOVO} não configurado no config/env.<device>.yaml "
            '(ex.: APP_PIN_NOVO: "2222").'
        )

    if pin == app_pin:
        return "", f"{CHAVE_PIN_NOVO} é igual ao APP_PIN: nada a trocar."

    return pin, ""


CHAVE_PIN_INVALIDO = "APP_PIN_INVALIDO"


def ler_pin_invalido(
    test_data: dict | None,
    app_pin: str,
    pin_novo: str,
) -> tuple[str, str]:
    """
    (PIN inválido, motivo para pular), do test_data.yaml — o mesmo usado
    no PIN divergente do primeiro acesso. Tem que ser diferente do
    APP_PIN e do APP_PIN_NOVO, senão o "errado"/"divergente" não é.
    """
    pin = str((test_data or {}).get(CHAVE_PIN_INVALIDO, "") or "").strip()

    if not pin:
        return "", f"{CHAVE_PIN_INVALIDO} não configurado no test_data.yaml."

    if pin in (app_pin, pin_novo):
        return "", (
            f"{CHAVE_PIN_INVALIDO} ({pin}) precisa ser diferente do APP_PIN "
            "e do APP_PIN_NOVO."
        )

    return pin, ""


@pytest.fixture
def pin_invalido(test_data, app_pin, pin_novo) -> str:
    pin, motivo = ler_pin_invalido(test_data, app_pin, pin_novo)

    if motivo:
        pytest.skip(motivo)

    return pin


@pytest.fixture
def pin_novo(app_pin) -> str:
    pin, motivo = ler_pin_novo(CredenciaisApp.from_env().pin_novo, app_pin)

    if motivo:
        pytest.skip(motivo)

    return pin


@dataclass
class EstadoDoPin:
    # True do início da troca até o PIN original ser restaurado pelo
    # próprio teste. Enquanto True, o app pode estar com o PIN novo.
    pode_estar_trocado: bool = False


@pytest.fixture
def restauracao_do_pin(app_session_e2e_registro_ponto, app_pin, pin_novo):
    """
    Rede de segurança: se o teste parar com o PIN possivelmente trocado,
    relança, tenta desbloquear com o PIN novo e, se abrir, troca de volta
    para o original. Se não abrir, o PIN não chegou a mudar.
    """
    estado = EstadoDoPin()

    yield estado

    if not estado.pode_estar_trocado:
        return

    sessao = app_session_e2e_registro_ponto
    logger.warning("Teste parou com o PIN possivelmente trocado; restaurando")

    sessao.relaunch()

    try:
        UnlockPage(sessao.driver).desbloquear_com_pin(pin_novo)
    except AssertionError:
        # O PIN novo não abriu: o app continua com o original.
        sessao.relaunch()
        UnlockPage(sessao.driver).desbloquear_com_pin(app_pin)
        return

    HomePage(sessao.driver).dispensar_popups_sobrepostos()

    pagina = AlterarPinPage(sessao.driver)
    pagina.acessar()
    pagina.alterar_pin(pin_novo, app_pin)

    logger.warning("PIN original restaurado pela rede de segurança")
