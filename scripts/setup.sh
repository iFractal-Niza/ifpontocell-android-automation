#!/bin/zsh

# =========================
# SETUP INICIAL DO PROJETO
# =========================
#
# Cria e valida o ambiente de automação Android (Python + Appium + SDK).
# Falha cedo, com mensagem acionável, em vez de deixar um ambiente
# meio-configurado que quebra depois.

set -e   # aborta no primeiro erro não tratado
set -u   # variável não definida é erro

# Versão mínima de Python exigida pelo código (usa sintaxe 3.10+).
readonly PYTHON_MIN_MAJOR=3
readonly PYTHON_MIN_MINOR=10

# Cores para legibilidade da saída.
readonly VERMELHO=$'\e[31m'
readonly VERDE=$'\e[32m'
readonly AMARELO=$'\e[33m'
readonly RESET=$'\e[0m'

info()  { echo "${VERDE}>>${RESET} $1" }
aviso() { echo "${AMARELO}>> aviso:${RESET} $1" }
erro()  { echo "${VERMELHO}>> erro:${RESET} $1" >&2 }

# Garante que rodamos na raiz do projeto (onde está requirements.txt).
if [[ ! -f "requirements.txt" ]]; then
  erro "requirements.txt não encontrado."
  erro "Rode este script a partir da raiz do projeto."
  exit 1
fi

echo ""
info "Iniciando setup do projeto..."

# =========================
# VALIDAÇÃO DE PYTHON 3.11
# =========================
#
# Correção importante: 'python3' no macOS aponta para o Python 3.9 do
# sistema, que NÃO roda este projeto (o código usa sintaxe 3.10+).
# Procuramos explicitamente por um Python >= 3.10, preferindo python3.11.

encontrar_python() {
  local candidato
  for candidato in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidato" >/dev/null 2>&1; then
      local versao
      versao=$("$candidato" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
      local major="${versao%%.*}"
      local minor="${versao##*.}"
      if (( major > PYTHON_MIN_MAJOR )) || \
         (( major == PYTHON_MIN_MAJOR && minor >= PYTHON_MIN_MINOR )); then
        echo "$candidato"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN=$(encontrar_python) || {
  erro "Nenhum Python >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} encontrado."
  erro "Instale com: brew install python@3.11"
  exit 1
}

info "Python selecionado: $($PYTHON_BIN --version) (${PYTHON_BIN})"

# =========================
# CRIAR / VALIDAR VENV
# =========================
#
# Se o venv existir mas apontar para um Python antigo (ex.: 3.9 do
# sistema, herdado de uma criação anterior), recriamos. Esse foi um bug
# real: venv em 3.9 aprovado por um gate calibrado abaixo do necessário.

venv_python_ok() {
  [[ -x "venv/bin/python" ]] || return 1
  local versao
  versao=$(venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
  local major="${versao%%.*}"
  local minor="${versao##*.}"
  (( major > PYTHON_MIN_MAJOR )) || \
    (( major == PYTHON_MIN_MAJOR && minor >= PYTHON_MIN_MINOR ))
}

if [[ -d "venv" ]]; then
  if venv_python_ok; then
    info "Ambiente virtual já existe e usa Python compatível."
  else
    aviso "venv existente usa Python incompatível. Recriando..."
    rm -rf venv
    "$PYTHON_BIN" -m venv venv
    info "Ambiente virtual recriado."
  fi
else
  info "Criando ambiente virtual..."
  "$PYTHON_BIN" -m venv venv
fi

# =========================
# ATIVAR VENV
# =========================
if [[ ! -f "venv/bin/activate" ]]; then
  erro "arquivo de ativação do venv não encontrado."
  exit 1
fi

info "Ativando ambiente virtual..."
source venv/bin/activate

# Daqui em diante, 'python' e 'pip' são os do venv.
# Correção: o script antigo chamava 'python3' (do sistema) mesmo após
# ativar o venv, podendo instalar deps no interpretador errado.

# =========================
# ATUALIZAR PIP
# =========================
info "Atualizando pip..."
python -m pip install --quiet --upgrade pip

# =========================
# INSTALAR DEPENDÊNCIAS
# =========================
info "Instalando dependências..."
python -m pip install --quiet -r requirements.txt
info "Dependências instaladas."

# =========================
# VALIDAR ANDROID SDK
# =========================
if command -v adb >/dev/null 2>&1; then
  info "adb: $(adb version 2>/dev/null | head -1)"
else
  aviso "adb não encontrado. Instale o Android SDK (Android Studio) e"
  aviso "coloque \$ANDROID_HOME/platform-tools e \$ANDROID_HOME/emulator no PATH."
fi

# =========================
# VALIDAR APPIUM + DRIVER UIAUTOMATOR2
# =========================
#
# Não basta ter o Appium. Sem o driver uiautomator2 instalado, os
# testes Android falham com "Could not find a driver for 'UiAutomator2'".

if command -v appium >/dev/null 2>&1; then
  info "Appium: $(appium --version)"

  if appium driver list --installed 2>&1 | grep -q "uiautomator2"; then
    uiautomator2_versao=$(appium driver list --installed 2>&1 | grep "uiautomator2" | head -1)
    info "Driver uiautomator2 instalado: ${uiautomator2_versao}"
  else
    aviso "Driver uiautomator2 NÃO instalado. Testes Android não vão rodar."
    aviso "Instale com: make install-appium"
  fi
else
  aviso "Appium não encontrado no PATH."
  aviso "Instale com: make install-appium"
fi

# =========================
# VALIDAR EMULADOR DISPONÍVEL
# =========================
#
# Lista os AVDs (emuladores) e os devices online, para o
# env.<device>.yaml apontar o ANDROID_UDID correto.

if command -v emulator >/dev/null 2>&1; then
  info "Emuladores (AVD) disponíveis:"
  emulator -list-avds 2>/dev/null | sed 's/^/     /'
fi

if command -v adb >/dev/null 2>&1; then
  info "Devices online (adb devices):"
  adb devices | awk 'NR>1 && NF {print "     " $0}'
fi

# =========================
# VALIDAR PYTEST
# =========================
if python -m pytest --version >/dev/null 2>&1; then
  info "Pytest validado: $(python -m pytest --version 2>&1 | head -1)"
else
  aviso "não foi possível validar o pytest."
fi

# =========================
# FINALIZAÇÃO
# =========================
echo ""
info "Setup finalizado!"
echo ""
echo "Próximos passos:"
echo "   1. Abrir o VS Code"
echo "   2. Selecionar o interpretador: ./venv/bin/python"
echo "   3. Criar config/env.emulator.yaml a partir do config/env.emulator.example.yaml"
echo "   4. Rodar: make smoke"
echo ""
echo "Se algo quebrar, consulte RESET_AMBIENTE.md"
echo ""