"""
Suporte dos testes unitários.

Testes unitários exercitam lógica pura: sem Appium, emulador ou API.
Rodam com 'make unit' em cerca de 1 segundo.
"""

import os
from pathlib import Path

import pytest

UNIT_DIR = Path(__file__).parent

# Prefixos das variáveis de configuração da suíte. O conftest raiz
# carrega o env.<device>.yaml no os.environ antes da coleta; limpá-los garante
# que o teste veja só o que ele próprio define.
PREFIXOS_CONFIG = ("ANDROID_", "APP_", "API_", "MONITOR_", "IFPONTO_")


def pytest_collection_modifyitems(items) -> None:
    for item in items:
        if UNIT_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def ambiente():
    """
    os.environ isolado: sem as chaves do env.<device>.yaml e restaurado ao fim.

    O monkeypatch não desfaz chaves criadas diretamente em os.environ
    (como faz load_yaml_env), por isso o snapshot manual.
    """
    original = dict(os.environ)

    for chave in list(os.environ):
        if chave.startswith(PREFIXOS_CONFIG):
            del os.environ[chave]

    try:
        yield os.environ
    finally:
        os.environ.clear()
        os.environ.update(original)
