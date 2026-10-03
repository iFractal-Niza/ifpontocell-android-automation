"""
Client da API de controle de celular e o contexto que ele usa.
"""

import pytest

from api.monitor_celular_client import MonitorCelularClient
from config.settings import ApiConfig
from utils.logger import get_logger

logger = get_logger("fixtures.api")


# === API ===
@pytest.fixture(scope="module")
def celular_api():
    """
    Retorna o cliente da API de controle de celular.

    O escopo de módulo permite reutilizar a mesma sessão HTTP
    durante os fluxos de preparação e execução do módulo.
    """
    api = ApiConfig.from_env()

    client = MonitorCelularClient(
        base_url=api.base_url,
        user=api.user,
        token_original=api.token,
    )

    try:
        yield client

    finally:
        client.session.close()

        logger.info("Sessão da API de celulares finalizada")


# === Contexto ===
@pytest.fixture(scope="session")
def monitor_nome_pessoa() -> str:
    """
    Nome utilizado para localizar o celular criado pelo login atual.
    """
    nome_pessoa = ApiConfig.from_env().monitor_nome_pessoa

    if not nome_pessoa:
        raise RuntimeError(
            "MONITOR_NOME_PESSOA não foi configurado em "
            "config/env.<device>.yaml."
        )

    return nome_pessoa
