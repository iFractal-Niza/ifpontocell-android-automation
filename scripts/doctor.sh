#!/usr/bin/env bash
# Diagnóstico de ambiente do framework de automação Android.
# Entrada via: make doctor
# Não destrutivo: apenas inspeciona.
# Sai com 0 se não houver FALHA bloqueante.

set -u

PYTHON="${PYTHON:-venv/bin/python3}"
VENV="${VENV:-venv}"
PYTHON_MIN_VERSION="${PYTHON_MIN_VERSION:-3.10}"
APPIUM_HOST="${APPIUM_HOST:-127.0.0.1}"
APPIUM_PORT="${APPIUM_PORT:-4723}"

# Configuração local, não versionada (.gitignore).
ENV_FILE="${ENV_FILE:-config/env.emulator.yaml}"

# Template seguro mantido dentro do projeto.
ENV_EXAMPLE_FILE="${ENV_EXAMPLE_FILE:-config/env.emulator.example.yaml}"

DEVICES_FILE="${DEVICES_FILE:-config/devices.yaml}"
REQUIREMENTS="${REQUIREMENTS:-requirements.txt}"

# APK local utilizado quando APP_SOURCE=apk.
APP_PATH="${APP_PATH:-app/ifPontoCell.apk}"

fail=0

ok() {
  printf "  \033[32m[ OK ]\033[0m  %s\n" "$1"
}

warn() {
  printf "  \033[33m[WARN]\033[0m  %s\n" "$1"
  [ -n "${2:-}" ] && printf "          ↳ %s\n" "$2"
  return 0
}

err() {
  printf "  \033[31m[FALHA]\033[0m %s\n" "$1"
  [ -n "${2:-}" ] && printf "          ↳ %s\n" "$2"
  fail=1
  return 0
}

section() {
  printf "\n— %s —\n" "$1"
}

# Lê uma chave simples do env.<device>.yaml usando PyYAML.
yaml_value() {
  local key="$1"

  "$PYTHON" - "$ENV_FILE" "$key" <<'PY'
import sys
import yaml

env_file = sys.argv[1]
key = sys.argv[2]

with open(env_file, encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

value = data.get(key, "")

if value is None:
    value = ""

print(str(value).strip())
PY
}

echo ""
echo "=== DIAGNÓSTICO DE AMBIENTE ANDROID (make doctor) ==="

# ============================================================
# Python
# ============================================================

section "Python do sistema"

if command -v python3 >/dev/null 2>&1; then
  ok "python3: $(python3 --version 2>&1)"
else
  err "python3 não encontrado no PATH" \
      "Instale o Python 3 (ex.: brew install python)"
fi

section "Ambiente virtual"

if [ -x "$PYTHON" ]; then
  ok "venv encontrado em '$VENV'"

  ver="$("$PYTHON" --version 2>&1)"

  if "$PYTHON" -c "
import sys

req = tuple(int(p) for p in '$PYTHON_MIN_VERSION'.split('.'))

sys.exit(
    0 if sys.version_info[:len(req)] >= req else 1
)
"; then
    ok "Python do venv: $ver (>= $PYTHON_MIN_VERSION)"
  else
    err "Python do venv abaixo do mínimo: $ver" \
        "Recrie o venv com Python >= $PYTHON_MIN_VERSION e rode 'make install'"
  fi
else
  err "venv ausente em '$VENV'" \
      "Crie o venv e rode 'make install'"
fi

# ============================================================
# Dependências
# ============================================================

section "pip e dependências"

if [ -x "$PYTHON" ] && "$PYTHON" -m pip --version >/dev/null 2>&1; then
  ok "pip disponível no venv"
else
  err "pip indisponível no venv" \
      "Rode 'make install'"
fi

if [ -f "$REQUIREMENTS" ]; then
  ok "$REQUIREMENTS encontrado"
else
  err "$REQUIREMENTS ausente" \
      "Adicione o arquivo de dependências na raiz do projeto"
fi

if [ -x "$PYTHON" ]; then
  if "$PYTHON" -c "import pytest, appium, yaml" >/dev/null 2>&1; then
    ok "Dependências principais importáveis (pytest, Appium-Python-Client, PyYAML)"
  else
    err "Falha ao importar pytest/appium/yaml" \
        "Rode 'make install'"
  fi
fi

# ============================================================
# Android SDK
# ============================================================

section "Android SDK"

if command -v adb >/dev/null 2>&1; then
  ok "adb: $(adb version 2>/dev/null | head -1)"

  devices="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"

  if [ -n "$devices" ]; then
    ok "device(s) disponível(is): $(echo "$devices" | tr '\n' ' ')"
  else
    warn \
      "Nenhum device Android online" \
      "Inicie um emulador ou conecte o celular (depuração USB ligada)."
  fi
else
  err "adb não encontrado no PATH" \
      "Coloque \$ANDROID_HOME/platform-tools no PATH."
fi

# ============================================================
# Appium
# ============================================================

section "Appium"

if command -v appium >/dev/null 2>&1; then
  ok "CLI Appium: $(appium --version 2>&1)"

  if appium driver list --installed 2>&1 | grep -qi uiautomator2; then
    ok "Driver uiautomator2 instalado"
  else
    err "Driver uiautomator2 não instalado" \
        "Rode 'make install-appium'"
  fi
else
  err "CLI Appium não encontrado" \
      "Rode 'make install-appium'"
fi

if curl -sf --max-time 3 \
  "http://$APPIUM_HOST:$APPIUM_PORT/status" >/dev/null 2>&1; then

  ok "Servidor Appium respondendo em http://$APPIUM_HOST:$APPIUM_PORT"

else
  warn \
    "Servidor Appium não está respondendo em http://$APPIUM_HOST:$APPIUM_PORT" \
    "Inicie com 'appium'. Não é obrigatório para testes de API."
fi

# ============================================================
# Configuração
# ============================================================

section "Arquivos de configuração"

if [ -f "$ENV_FILE" ]; then
  ok "Configuração local encontrada em '$ENV_FILE'"
else
  err \
    "Configuração local não encontrada em '$ENV_FILE'" \
    "Crie o arquivo a partir de '$ENV_EXAMPLE_FILE'."
fi

if [ -f "$ENV_EXAMPLE_FILE" ]; then
  ok "Template '$ENV_EXAMPLE_FILE' encontrado"
else
  warn \
    "Template '$ENV_EXAMPLE_FILE' ausente" \
    "Mantenha um template sem credenciais reais dentro do projeto."
fi

# Mesma validação que a suíte faz ao abrir a primeira sessão do app
# (config.settings.Settings): formato, obrigatórias por contexto e
# coordenadas. Lista todos os erros de uma vez. Chave repetida no
# env.<device>.yaml também é recusada aqui (config.env_loader).
if [ -f "$ENV_FILE" ] && [ -x "$PYTHON" ]; then
  if validacao="$(LOG_LEVEL=WARNING IFPONTO_ENV_FILE="$ENV_FILE" "$PYTHON" - 2>&1 <<'PY'
import sys
from config.env_loader import carregar_env
from config.settings import ConfiguracaoInvalida, Settings

try:
    carregar_env()
    Settings.from_env()
except ConfiguracaoInvalida as erro:
    print("\n".join(erro.erros))
    sys.exit(1)
PY
)"; then
    ok "Valores do '$ENV_FILE' válidos (Settings)"
  else
    err \
      "Valores inválidos em '$ENV_FILE'" \
      "Corrija os itens abaixo antes de rodar a suíte:"
    printf '%s\n' "$validacao" | sed 's/^/            - /'
  fi
fi

if [ -f "$DEVICES_FILE" ]; then
  ok "$DEVICES_FILE encontrado"
else
  warn \
    "$DEVICES_FILE ausente" \
    "Necessário apenas caso o projeto utilize configuração adicional de devices."
fi

# ============================================================
# Aplicação
# ============================================================

section "Aplicação"

if [ ! -f "$ENV_FILE" ]; then
  warn \
    "Validação da aplicação ignorada porque '$ENV_FILE' não existe" \
    "Crie o arquivo de configuração e rode 'make doctor' novamente."

elif [ ! -x "$PYTHON" ]; then
  warn \
    "Validação da aplicação ignorada porque o venv não está disponível" \
    "Rode 'make install' e execute 'make doctor' novamente."

elif ! "$PYTHON" -c "import yaml" >/dev/null 2>&1; then
  err \
    "PyYAML não disponível para leitura do '$ENV_FILE'" \
    "Rode 'make install'."

else
  APP_SOURCE_VALUE="$(yaml_value "APP_SOURCE")"

  case "$APP_SOURCE_VALUE" in
    apk)
      ok "APP_SOURCE: apk"

      APP_PATH_VALUE="$(yaml_value "APP_PATH")"

      # Permite APP_PATH no env.<device>.yaml ou fallback definido pelo Makefile/script.
      if [ -z "$APP_PATH_VALUE" ]; then
        APP_PATH_VALUE="$APP_PATH"
      fi

      if [ -f "$APP_PATH_VALUE" ]; then
        ok "APK encontrado: $APP_PATH_VALUE"
      else
        err \
          "APK não encontrado: $APP_PATH_VALUE" \
          "Adicione o ifPontoCell.apk nesse caminho ou use APP_SOURCE=package."
      fi
      ;;

    package|"")
      ok "APP_SOURCE: package${APP_SOURCE_VALUE:- (padrão)}"

      APP_PACKAGE_VALUE="$(yaml_value "ANDROID_APP_PACKAGE")"
      APP_PACKAGE_VALUE="${APP_PACKAGE_VALUE:-br.com.ifractal.Stou}"
      ANDROID_UDID_VALUE="$(yaml_value "ANDROID_UDID")"

      ok "package: $APP_PACKAGE_VALUE"

      if command -v adb >/dev/null 2>&1; then
        selected_udid="$ANDROID_UDID_VALUE"

        if [ -z "$selected_udid" ]; then
          online_devices="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
          online_count="$(printf '%s\n' "$online_devices" | sed '/^$/d' | wc -l | tr -d ' ')"

          if [ "$online_count" = "1" ]; then
            selected_udid="$(printf '%s\n' "$online_devices" | head -1)"
          fi
        fi

        if [ -z "$selected_udid" ]; then
          warn \
            "Não foi possível confirmar se o app está instalado" \
            "Configure ANDROID_UDID quando houver mais de um device online."
        elif adb -s "$selected_udid" shell pm path "$APP_PACKAGE_VALUE" 2>/dev/null | grep -q '^package:'; then
          ok "app instalado em $selected_udid"
        else
          err \
            "package '$APP_PACKAGE_VALUE' não encontrado em $selected_udid" \
            "Instale o app no device ou use APP_SOURCE=apk."
        fi
      fi
      ;;

    *)
      err \
        "APP_SOURCE inválido: '$APP_SOURCE_VALUE'" \
        "Use 'apk' ou 'package' no '$ENV_FILE'."
      ;;
  esac
fi

# ============================================================
# Estrutura
# ============================================================

section "Estrutura do projeto"

for d in tests tests/app config scripts pages core; do
  if [ -d "$d" ]; then
    ok "diretório '$d' presente"
  else
    err \
      "diretório '$d' ausente" \
      "Estrutura básica do projeto incompleta"
  fi
done

# ============================================================
# Git
# ============================================================

# Configuração local do clone (não vem no git clone). Ausência não
# bloqueia a execução dos testes, por isso é WARN e não FALHA.
section "Git"

if [ "$(git config --get core.hooksPath 2>/dev/null)" = ".githooks" ]; then
  ok "hook de pre-commit ativo (lint com ruff)"
else
  warn \
    "hook de pre-commit não ativado: commits passam sem lint" \
    "Rode 'make git-hooks' (uma vez por clone)."
fi

if [ -x "$VENV/bin/ruff" ]; then
  ok "ruff instalado no venv"
else
  warn \
    "ruff não encontrado em '$VENV/bin/ruff': o pre-commit ignora o lint" \
    "Rode 'make install'."
fi

# ============================================================
# Resultado
# ============================================================

echo ""

if [ "$fail" -eq 0 ]; then
  echo "✅ Ambiente Android pronto. Nenhum problema bloqueante encontrado."
else
  echo "❌ Problemas bloqueantes encontrados. Corrija os itens [FALHA] e rode 'make doctor' novamente."
fi

exit "$fail"