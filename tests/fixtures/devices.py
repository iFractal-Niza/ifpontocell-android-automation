"""
Seleção de emulador/device por worker na execução paralela (devices.yaml).
"""

import os

import pytest
import yaml

from config.settings import PROJECT_ROOT
from utils.logger import get_logger

logger = get_logger("fixtures.devices")


# === Devices da execução paralela ===
def _load_devices() -> list[dict]:
    """
    Carrega a lista de emuladores/devices do devices.yaml.
    """
    path = os.path.join(
        PROJECT_ROOT,
        "config",
        "devices.yaml",
    )

    if not os.path.exists(path):
        return []

    with open(
        path,
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file) or {}

    return data.get("emulators", data.get("devices", []))


@pytest.fixture(scope="session")
def device_config(request) -> dict | None:
    """
    Retorna o device usado pelo worker atual.

    Comportamento:
    - Execução sequencial: usa as variáveis de ambiente.
    - Execução paralela: usa devices.yaml.
    """
    worker_id = os.getenv(
        "PYTEST_XDIST_WORKER",
        "",
    )

    if not worker_id:
        return None

    devices = _load_devices()

    if not devices:
        logger.warning(
            "devices.yaml não encontrado ou vazio. "
            "Usando variáveis de ambiente."
        )
        return None

    markers = {marker.name for marker in request.node.iter_markers()}

    for device in devices:
        device_marks = set(device.get("marks", []))

        matching_marks = markers & device_marks

        if matching_marks:
            logger.info(
                "Device selecionado por mark: "
                f"{device['name']} "
                f"(worker={worker_id}, "
                f"marks={matching_marks})"
            )
            return device

    index = int(worker_id.replace("gw", "")) % len(devices)

    device = devices[index]

    logger.info(
        "Device selecionado por round-robin: "
        f"{device['name']} "
        f"(worker={worker_id}, index={index})"
    )

    return device
