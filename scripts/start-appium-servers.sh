#!/bin/bash
# =========================
# start-appium-servers.sh
# Sobe um servidor Appium por emulador/device definido no devices.yaml
# =========================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VENV="$PROJECT_ROOT/venv"
PYTHON="$VENV/bin/python3"

DEVICES_FILE="$PROJECT_ROOT/config/devices.yaml"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"

# === Validações ===

if ! command -v appium >/dev/null 2>&1; then
    echo "[ERRO] Appium não encontrado."
    echo "       Execute 'make setup' para preparar o ambiente."
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "[ERRO] Ambiente virtual não encontrado em '$VENV'."
    echo "       Execute 'make install' ou 'make setup'."
    exit 1
fi

if [ ! -f "$DEVICES_FILE" ]; then
    echo "[ERRO] Arquivo de dispositivos não encontrado: $DEVICES_FILE"
    echo "       Configure 'config/devices.yaml' antes da execução paralela."
    exit 1
fi

# === Leitura das portas ===

PORTS=$("$PYTHON" - <<EOF
import yaml

with open("$DEVICES_FILE") as f:
    data = yaml.safe_load(f) or {}

ports = [
    str(device["appium_port"])
    for device in data.get("emulators", data.get("devices", []))
    if "appium_port" in device
]

print(" ".join(ports))
EOF
)

if [ -z "$PORTS" ]; then
    echo "[ERRO] Nenhum emulador/device com 'appium_port' encontrado em $DEVICES_FILE."
    exit 1
fi

# === Inicialização ===

echo "[INFO] Iniciando servidores Appium nas portas: $PORTS"

for PORT in $PORTS; do
    LOG_FILE="$LOG_DIR/appium-$PORT.log"

    echo "[INFO] Subindo Appium na porta $PORT → $LOG_FILE"

    appium \
        --port "$PORT" \
        --log "$LOG_FILE" \
        --log-level info &
done

echo ""
echo "[INFO] Todos os servidores Appium foram iniciados."
echo "[INFO] Processos ativos:"

pgrep -a node | grep appium || true

echo ""
echo "Para encerrar todos:"
echo "  pkill -f 'appium --port'"