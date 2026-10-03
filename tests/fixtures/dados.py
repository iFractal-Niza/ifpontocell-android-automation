"""
Massa de teste (test_data.yaml) e credenciais do app (env.<device>.yaml).
"""

import os
from pathlib import Path

import pytest
import yaml

from config.settings import PROJECT_ROOT, CredenciaisApp


# === Massa de teste ===
@pytest.fixture
def test_data():
    """
    Carrega dados de teste do test_data.yaml.
    """
    test_data_path = (
        Path(
            os.getenv(
                "TEST_DATA_FILE",
                PROJECT_ROOT / "config" / "test_data.yaml",
            )
        )
        .expanduser()
        .resolve()
    )

    if not test_data_path.is_file():
        raise FileNotFoundError(
            f"Arquivo de dados de teste não encontrado em: {test_data_path}"
        )

    with test_data_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# === Dados do app ===
@pytest.fixture(scope="session")
def app_system():
    """
    Nome do sistema utilizado no onboarding.
    """
    return CredenciaisApp.from_env().sistema


@pytest.fixture(scope="session")
def app_user():
    """
    Usuário válido do app.
    """
    return CredenciaisApp.from_env().usuario


@pytest.fixture(scope="session")
def app_password():
    """
    Senha válida do app.
    """
    return CredenciaisApp.from_env().senha


@pytest.fixture(scope="session")
def app_pin():
    """
    PIN válido para autenticação.
    """
    return CredenciaisApp.from_env().pin


@pytest.fixture(scope="session")
def jornada_do_usuario() -> list[str]:
    """
    Horários da escala do usuário (APP_JORNADA), como a tela Ponto
    mostra num dia escalado futuro. Vazia se não configurada.
    """
    return list(CredenciaisApp.from_env().jornada)
