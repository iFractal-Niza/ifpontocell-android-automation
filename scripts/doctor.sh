#!/usr/bin/env bash
# Diagnóstico de ambiente do framework de automação Android.
# Entrada via: make doctor
# Não destrutivo: apenas inspeciona.
set -u

PYTHON="${PYTHON:-venv/bin/python3}"
VENV="${VENV:-venv}"
PYTHON_MIN_VERSION="${PYTHON_MIN_VERSION:-3.10}"
APPIUM_HOST="${APPIUM_HOST:-127.0.0.1}"
APPIUM_PORT="${APPIUM_PORT:-4723}"
ENV_FILE="${ENV_FILE:-config/env.yaml}"
ENV_EXAMPLE_FILE="${ENV_EXAMPLE_FILE:-config/env.example.yaml}"
TEST_DATA_FILE="${TEST_DATA_FILE:-config/test_data.yaml}"
APP_PATH="${APP_PATH:-app/ifPontoCell.apk}"
DEVICES_FILE="${DEVICES_FILE:-config/devices.yaml}"
REQUIREMENTS="${REQUIREMENTS:-requirements.txt}"
fail=0

ok(){ printf "  \033[32m[ OK ]\033[0m  %s\n" "$1"; }
warn(){ printf "  \033[33m[WARN]\033[0m  %s\n" "$1"; [ -n "${2:-}" ] && printf "          ↳ %s\n" "$2"; }
err(){ printf "  \033[31m[FALHA]\033[0m %s\n" "$1"; [ -n "${2:-}" ] && printf "          ↳ %s\n" "$2"; fail=1; }
section(){ printf "\n— %s —\n" "$1"; }

echo ""
echo "=== DIAGNÓSTICO DE AMBIENTE ANDROID (make doctor) ==="

section "Python / venv"
if command -v python3 >/dev/null 2>&1; then ok "python3: $(python3 --version 2>&1)"; else err "python3 não encontrado" "Instale Python 3 e rode 'make install'"; fi
if [ -x "$PYTHON" ]; then
  if "$PYTHON" -c "import sys; req=tuple(map(int,'$PYTHON_MIN_VERSION'.split('.'))); raise SystemExit(0 if sys.version_info[:len(req)] >= req else 1)"; then
    ok "venv: $($PYTHON --version 2>&1)"
  else err "Python do venv abaixo de $PYTHON_MIN_VERSION" "Recrie o venv e rode 'make install'"; fi
  "$PYTHON" -c "import pytest, appium" >/dev/null 2>&1 && ok "pytest/Appium-Python-Client importáveis" || err "Dependências Python incompletas" "Rode 'make install'"
else err "venv ausente em '$VENV'" "Rode 'make install'"; fi

section "Android SDK"
if command -v adb >/dev/null 2>&1; then
  ok "adb: $(adb version 2>/dev/null | head -1)"
  devices=$(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  if [ -n "$devices" ]; then ok "device(s) disponível(is): $(echo "$devices" | tr '\n' ' ')"; else warn "Nenhum device Android online" "Inicie um emulador ou conecte o device físico"; fi
else err "adb não encontrado no PATH" "Configure ANDROID_HOME/platform-tools no PATH"; fi

section "Appium"
if command -v appium >/dev/null 2>&1; then
  ok "CLI Appium: $(appium --version 2>&1)"
  if appium driver list --installed 2>&1 | grep -qi uiautomator2; then ok "Driver uiautomator2 instalado"; else err "Driver uiautomator2 não instalado" "Rode 'appium driver install uiautomator2' ou 'make install-appium'"; fi
else err "CLI Appium não encontrado" "Rode 'make install-appium'"; fi

if curl -sf --max-time 3 "http://$APPIUM_HOST:$APPIUM_PORT/status" >/dev/null 2>&1; then ok "Servidor Appium respondendo em http://$APPIUM_HOST:$APPIUM_PORT"; else warn "Servidor Appium não responde em http://$APPIUM_HOST:$APPIUM_PORT" "Inicie com 'appium'; não bloqueia testes apenas de API"; fi

section "Configuração"
[ -f "$ENV_FILE" ] && ok "$ENV_FILE encontrado" || err "$ENV_FILE ausente" "Crie a partir de '$ENV_EXAMPLE_FILE'"
[ -f "$ENV_EXAMPLE_FILE" ] && ok "$ENV_EXAMPLE_FILE encontrado" || err "$ENV_EXAMPLE_FILE ausente" "Restaure o template versionado"
[ -f "$TEST_DATA_FILE" ] && ok "$TEST_DATA_FILE encontrado" || err "$TEST_DATA_FILE ausente" "Crie o arquivo de massa de teste"
[ -f "$DEVICES_FILE" ] && ok "$DEVICES_FILE encontrado" || warn "$DEVICES_FILE ausente" "Obrigatório apenas para paralelo"
[ -f "$REQUIREMENTS" ] && ok "$REQUIREMENTS encontrado" || err "$REQUIREMENTS ausente" "Restaure o arquivo na raiz"


section "Aplicação"
if [ ! -f "$ENV_FILE" ]; then
  err "Não foi possível validar a aplicação sem '$ENV_FILE'" \
      "Crie o arquivo a partir de '$ENV_EXAMPLE_FILE'"
elif [ ! -x "$PYTHON" ]; then
  err "Não foi possível validar APP_SOURCE sem o Python do venv" \
      "Rode 'make install'"
else
  app_config="$("$PYTHON" - "$ENV_FILE" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as file:
    data = yaml.safe_load(file) or {}

values = (
    str(data.get("APP_SOURCE", "")).strip().lower(),
    str(data.get("APP_PATH", "")).strip(),
    str(data.get("ANDROID_APP_PACKAGE", "")).strip(),
    str(data.get("ANDROID_UDID", "")).strip(),
)

print("\n".join(values))
PY
  )"

  if [ "$?" -ne 0 ]; then
    err "Falha ao interpretar '$ENV_FILE'" \
        "Valide a sintaxe YAML e rode 'make doctor' novamente"
  else
    app_source="$(printf '%s\n' "$app_config" | sed -n '1p')"
    app_path_config="$(printf '%s\n' "$app_config" | sed -n '2p')"
    app_package="$(printf '%s\n' "$app_config" | sed -n '3p')"
    android_udid="$(printf '%s\n' "$app_config" | sed -n '4p')"

    case "$app_source" in
      apk)
        ok "APP_SOURCE: apk"

        if [ -z "$app_path_config" ]; then
          err "APP_PATH não configurado em '$ENV_FILE'" \
              "Adicione: APP_PATH: \"app/ifPontoCell.apk\""
        else
          case "$app_path_config" in
            *.apk|*.APK) ;;
            *)
              err "APP_PATH não aponta para um arquivo .apk: $app_path_config" \
                  "Ajuste APP_PATH para o APK Android"
              ;;
          esac

          if [ -f "$app_path_config" ]; then
            ok "APK encontrado: $app_path_config"
          else
            err "APK não encontrado: $app_path_config" \
                "Adicione o APK nesse caminho ou use APP_SOURCE=package"
          fi
        fi
        ;;

      package)
        ok "APP_SOURCE: package"

        if [ -z "$app_package" ]; then
          err "ANDROID_APP_PACKAGE não configurado em '$ENV_FILE'" \
              "Informe o package do app Android"
        else
          ok "package configurado: $app_package"

          if command -v adb >/dev/null 2>&1; then
            selected_udid="$android_udid"

            if [ -z "$selected_udid" ]; then
              online_devices="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
              online_count="$(printf '%s\n' "$online_devices" | sed '/^$/d' | wc -l | tr -d ' ')"

              if [ "$online_count" = "1" ]; then
                selected_udid="$(printf '%s\n' "$online_devices" | head -1)"
              fi
            fi

            if [ -n "$selected_udid" ]; then
              if adb -s "$selected_udid" shell pm path "$app_package" 2>/dev/null | grep -q '^package:'; then
                ok "app instalado em $selected_udid"
              else
                err "package '$app_package' não encontrado em $selected_udid" \
                    "Instale o app ou altere APP_SOURCE para apk"
              fi
            else
              warn "Não foi possível confirmar se o package está instalado" \
                   "Configure ANDROID_UDID quando houver mais de um device"
            fi
          fi
        fi
        ;;

      *)
        err "APP_SOURCE inválido: '$app_source'" \
            "Use 'apk' ou 'package' em '$ENV_FILE'"
        ;;
    esac
  fi
fi

section "Estrutura"
for d in tests tests/app config scripts pages core; do [ -d "$d" ] && ok "diretório '$d' presente" || err "diretório '$d' ausente" "Estrutura do projeto incompleta"; done

echo ""
if [ "$fail" -eq 0 ]; then echo "✅ Ambiente Android sem falhas bloqueantes."; else echo "❌ Corrija os itens [FALHA] e rode 'make doctor' novamente."; fi
exit "$fail"