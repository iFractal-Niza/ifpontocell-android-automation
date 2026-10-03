"""
Configuração raiz do pytest.

Só carrega o env.<device>.yaml e registra os plugins; as fixtures ficam em
tests/fixtures/, separadas por assunto.
"""

import pytest

from config.env_loader import carregar_env
from config.settings import ConfiguracaoInvalida

pytest_plugins = [
    "observability.pytest_report",
    "observability.video",
    "tests.fixtures.devices",
    "tests.fixtures.sessoes",
    "tests.fixtures.jornada",
    "tests.fixtures.api",
    "tests.fixtures.dados",
    "tests.fixtures.massa",
    "tests.fixtures.geo",
    "tests.fixtures.casos_teste",
]


def pytest_configure(config) -> None:
    """
    Carrega o ambiente antes da coleta.

    Executado como hook e não em tempo de import para que a ordem de
    carregamento não dependa de qual conftest o pytest importa primeiro.

    env.<device>.yaml com chave repetida para a execução antes de começar,
    com a mensagem de qual chave e em que linhas (sem traceback).
    """
    try:
        carregar_env()
    except ConfiguracaoInvalida as erro:
        raise pytest.UsageError(str(erro)) from None
