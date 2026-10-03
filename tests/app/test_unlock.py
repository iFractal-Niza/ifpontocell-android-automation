from dataclasses import dataclass

import pytest

from pages.unlock_page import UnlockPage
from tests.support.flows import (
    realizar_login,
    realizar_unlock,
)


@dataclass(frozen=True)
class ContextoUnlock:
    unlock_page: UnlockPage
    codigos_anteriores: set[int]


# === Unlock: preparação do módulo ===
@pytest.fixture(scope="module", autouse=True)
def posicionar_na_tela_pin(
    driver_unlock,
    app_system,
    app_user,
    app_password,
    celular_api,
    monitor_nome_pessoa,
) -> ContextoUnlock:
    """
    Posiciona o driver na criação do PIN uma única vez.

    Antes do login, captura os códigos existentes para identificar
    o registro criado especificamente pela execução atual.

    Fronteira: Login -> criação do PIN.
    """
    codigos_anteriores = (
        celular_api
        .obter_codigos_celular_por_nome_pessoa(
            monitor_nome_pessoa
        )
    )

    unlock_page = realizar_login(
        driver=driver_unlock,
        nome_sistema=app_system,
        usuario=app_user,
        senha=app_password,
    )

    return ContextoUnlock(
        unlock_page=unlock_page,
        codigos_anteriores=codigos_anteriores,
    )


# === Unlock: cenário positivo ===
@pytest.mark.smoke
def test_pin_valido(
    posicionar_na_tela_pin,
    driver_unlock,
    app_pin,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Valida a ativação paliativa do celular antes da criação
    e confirmação do PIN válido.

    Fronteira:
    ativação pela API -> criação do PIN -> confirmação do PIN -> Home.
    """
    assert (
        posicionar_na_tela_pin
        .unlock_page
        .validar_tela_criar_pin()
    ), "A tela de criação do PIN não foi exibida."

    home_page = realizar_unlock(
        driver=driver_unlock,
        pin=app_pin,
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
        codigos_anteriores=(
            posicionar_na_tela_pin.codigos_anteriores
        ),
    )

    assert home_page.validar_home(), (
        "A Home não foi exibida após a ativação do celular "
        "e configuração do PIN válido."
    )


# === Unlock: cenários negativos ===
# TODO: test_pin_invalido
# Pendência: mapear os locators da mensagem de erro de PIN.
# Rastrear em: [issue no board]