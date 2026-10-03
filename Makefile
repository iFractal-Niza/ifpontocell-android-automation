# === Variáveis ===
VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
RUFF := $(VENV)/bin/ruff

# Versão mínima do Python exigida pelo projeto
PYTHON_MIN_VERSION ?= 3.10

# Appium
APPIUM_HOST ?= 127.0.0.1
APPIUM_PORT ?= 4723

# Versões fixadas p/ reprodutibilidade (dev == CI).
# Vazio = "última compatível" (evite em time/CI; preencha com a versão homologada).
APPIUM_VERSION   ?=
UIAUTOMATOR2_VERSION ?=

# Instalação local do npm/Appium por usuário.
# Evita dependência de sudo e mantém o ambiente de automação
# isolado no usuário responsável pela execução dos testes.
NPM_PREFIX := $(HOME)/.npm-global
NPM_BIN := $(NPM_PREFIX)/bin
APPIUM_BIN := $(NPM_BIN)/appium

# Diretórios de testes
TESTS := tests
APP_TESTS := $(TESTS)/app
API_TESTS := $(TESTS)/api
UNIT_TESTS := $(TESTS)/unit

# Arquivos de app - ordem lógica de execução
TEST_ONBOARDING := $(APP_TESTS)/test_onboarding.py
TEST_LOGIN := $(APP_TESTS)/test_login.py
TEST_UNLOCK := $(APP_TESTS)/test_unlock.py
TEST_E2E := $(APP_TESTS)/test_e2e.py
TEST_REGISTRO_PONTO := $(APP_TESTS)/test_registro_sem_foto.py
TEST_DADOS_PESSOAIS := $(APP_TESTS)/test_dados_pessoais.py
TEST_PRIVACIDADE := $(APP_TESTS)/test_privacidade.py
TEST_ZERAR_DADOS := $(APP_TESTS)/test_zerar_dados.py

# Suíte principal de app em ordem controlada
APP_SUITE := \
	$(TEST_ONBOARDING) \
	$(TEST_LOGIN) \
	$(TEST_UNLOCK) \
	$(TEST_E2E) \
	$(TEST_REGISTRO_PONTO) \
	$(TEST_DADOS_PESSOAIS) \
	$(TEST_PRIVACIDADE) \
	$(TEST_ZERAR_DADOS)

# Suíte completa em ordem controlada
FULL_SUITE := \
	$(APP_SUITE) \
	$(API_TESTS)

# Relatórios (REPORTS vem do DEVICE, em "Aparelho")
SCREENSHOTS = $(REPORTS)/screenshots
HISTORY_FILE = $(REPORTS)/history.json
EXPORT_REPORT_PDF := scripts/export_report_pdf.py

# === Arquivos locais (não versionados) ===
#
# env.<device>.yaml, test_data.yaml e o APK contêm dados locais/sensíveis
# e ficam fora do controle de versão (.gitignore), mas dentro do projeto.
#
# === Aparelho ===
# Um env por aparelho: make <comando> usa o emulador (config/env.emulator.yaml,
# reports/emulator/); make <comando> DEVICE=real, o celular (config/env.real.yaml,
# reports/real/). Cada um com o seu usuário de teste, a sua pasta de report
# (prints, vídeos, histórico) e o seu cache do make falhas: os dois rodam ao
# mesmo tempo, em dois terminais.
DEVICE ?= emulator
ENV_FILE := config/env.$(DEVICE).yaml
ENV_EXAMPLE_FILE := config/env.$(DEVICE).example.yaml
REPORTS := reports/$(DEVICE)
export IFPONTO_ENV_FILE := $(abspath $(ENV_FILE))
export IFPONTO_REPORTS_DIR := $(abspath $(REPORTS))
PYTEST_FLAGS += -o cache_dir=.pytest_cache/$(DEVICE)
TEST_DATA_FILE := config/test_data.yaml

# Arquivos seguros/versionados dentro do projeto
DEVICES_FILE := config/devices.yaml
REQUIREMENTS := requirements.txt

# Branches padrão
BRANCH_DEV := desenvolvimento
BRANCH_MAIN := main

# Controle de log
LOG_LEVEL ?= INFO

# Flags adicionais opcionais
PYTEST_FLAGS ?=

# Vídeo no report: por padrão, só dos testes que falharam.
# make <comando> VIDEO=1 grava todos; VIDEO=0 não grava nada.
ifeq ($(strip $(VIDEO)),1)
PYTEST_FLAGS += --video=todos
else ifeq ($(strip $(VIDEO)),0)
PYTEST_FLAGS += --video=nao
endif

# Execução padrão:
# exibe apenas progresso, resumo customizado e caminho do report.
# O progresso é por contagem ([ 7/34]), não percentual: o -q esconde o
# total de testes coletados.
PYTEST_FLAGS_CLEAN := \
	-q \
	-o verbosity_test_cases=1 \
	-o console_output_style=count \
	-rN \
	--tb=no \
	--no-header \
	--disable-warnings \
	--log-level=INFO

# Execução de diagnóstico:
# exibe testes, logs, stdout/stderr e traceback completo.
PYTEST_FLAGS_DEBUG := \
	-vv \
	-rA \
	--tb=long \
	--showlocals \
	--capture=tee-sys \
	--log-level=DEBUG

# Alvo opcional do modo debug.
# Exemplo:
# make debug test=tests/app/test_login.py::test_credenciais_validas
DEBUG_TARGET = $(if $(test),$(test),$(FULL_SUITE))

# === Alvos phony ===
.PHONY: help \
        venv install install-appium appium-update setup git-hooks \
        check-venv check-config check-test-data check-app check-devices \
        check-appium check-mobile \
        doctor impact appium appium-servers lint format \
        run debug unit smoke regression \
        ct falhas onboarding login unlock primeiro-acesso e2e e2e-debug registro-ponto jornada dados-pessoais privacidade zerar-dados \
        api \
        clear limpar-historico report report-pdf renumerar-ct \
        git-status commit push update-dev update-feature start-feature \
        merge-dev merge-main merge-branch delete-branch

# === Ajuda ===
help:
	@echo ""
	@echo "=== Ambiente ==="
	@echo "  make setup                 Prepara venv, dependências Python, Appium e UiAutomator2"
	@echo "  make install               Cria o venv se necessário e instala dependências Python"
	@echo "  make install-appium        Instala Appium e UiAutomator2 no usuário atual"
	@echo "  make git-hooks             Ativa o lint e os unitários no pre-commit (1x por clone)"
	@echo "  make appium                Sobe o Appium (log em reports/appium.log)"
	@echo "  make appium-update         Atualiza o driver UiAutomator2 para a última compatível"
	@echo "  make doctor                Diagnóstico completo do ambiente"
	@echo "  make impact file=x.py      Mostra os testes que dependem de um arquivo e o que rodar"
	@echo "  make lint                  Verifica lint e formatação (ruff), sem alterar"
	@echo "  make format                Corrige lint e formata o código (ruff)"
	@echo "  make appium-servers        Sobe servidores Appium definidos em devices.yaml"
	@echo "  make <comando> DEVICE=real Roda no celular (config/env.real.yaml; padrão: emulador)"
	@echo ""
	@echo "=== Execução ==="
	@echo "  make run                   Roda suíte completa em ordem lógica (inclui os que consomem massa)"
	@echo "  make debug                 Roda suíte completa em modo debug"
	@echo "  make debug test=arquivo    Roda arquivo ou teste específico em modo debug"
	@echo "  make ct id=CT010           Roda casos de teste pelo ID (vários: id=CT010,CT011)"
	@echo "  make falhas                Roda de novo só os testes que falharam na última execução"
	@echo "  make <comando> VIDEO=1     Vídeo de todos os testes no report (padrão: só dos que falharam)"
	@echo "  make <comando> VIDEO=0     Sem vídeo, nem das falhas"
	@echo ""
	@echo "=== Testes ==="
	@echo "  make unit                  Roda os testes unitários (sem emulador, ~1s)"
	@echo "  make smoke                 Roda testes smoke em ordem lógica"
	@echo "  make regression            Roda testes regression em ordem lógica"
	@echo "  make onboarding            Roda testes de onboarding"
	@echo "  make login                 Roda testes de login"
	@echo "  make unlock                Roda testes de unlock"
	@echo "  make primeiro-acesso       Roda onboarding > login > unlock"
	@echo "  make e2e                   Roda testes end-to-end"
	@echo "  make e2e-debug             Roda testes end-to-end em modo debug"
	@echo "  make registro-ponto        Roda testes de registro de ponto"
	@echo "  make jornada               Roda e2e + registro de ponto"
	@echo "  make dados-pessoais        Roda o teste de Dados Pessoais (nome do colaborador)"
	@echo "  make privacidade           Roda o teste da Privacidade (índice e navegação)"
	@echo "  make zerar-dados           Apagar dados (Ajustes e menu do perfil: NÃO e SIM; o SIM refaz o primeiro acesso)"
	@echo "  make api                   Roda testes de API"
	@echo ""
	@echo "=== Reports ==="
	@echo "  make clear                 Limpa reports, histórico, vídeos e caches (todos os aparelhos; DEVICE=… só um)"
	@echo "  make limpar-historico      Zera só o histórico (falhas novas, recorrentes e instáveis)"
	@echo "  make report                Abre o último report HTML"
	@echo "  make report-pdf            Exporta o último report HTML para PDF"
	@echo "  make renumerar-ct          Mostra a renumeração dos CTs na ordem da suíte (aplicar=1 aplica)"
	@echo ""
	@echo "=== Git ==="
	@echo "  make git-status            Exibe status do git"
	@echo "  make commit m=\"msg\"       Cria commit"
	@echo "  make push                  Envia branch atual"
	@echo "  make update-dev            Atualiza desenvolvimento"
	@echo "  make update-feature        Atualiza feature com desenvolvimento"
	@echo "  make start-feature name=x  Cria nova feature"
	@echo "  make merge-dev             Testa e mescla feature na desenvolvimento"
	@echo "  make merge-main            Testa, mescla desenvolvimento na main e volta para desenvolvimento"
	@echo "  make merge-branch source=x target=y"
	@echo "  make delete-branch name=x  Exclui branch local e remota"
	@echo ""

# === Ambiente virtual ===
venv:
	@if [ ! -x "$(PYTHON)" ]; then \
		echo "Criando ambiente virtual em '$(VENV)'..."; \
		command -v python3 >/dev/null 2>&1 \
			|| ( echo "Python 3 não encontrado no sistema."; \
			     echo "Instale o Python 3 e execute 'make install' novamente."; \
			     exit 1 ); \
		python3 -m venv "$(VENV)" \
			|| ( echo "Falha ao criar o ambiente virtual em '$(VENV)'."; \
			     exit 1 ); \
		echo "Ambiente virtual criado com sucesso."; \
	else \
		echo "Ambiente virtual já existe em '$(VENV)'."; \
	fi

# === Instalação ===
install: venv check-venv
	@test -f "$(REQUIREMENTS)" \
		|| ( echo "Arquivo de dependências não encontrado: $(REQUIREMENTS)"; exit 1 )
	@echo "Atualizando pip..."
	@$(PIP) install --upgrade pip
	@echo "Instalando dependências de $(REQUIREMENTS)..."
	@$(PIP) install -r "$(REQUIREMENTS)"
	@echo "Ambiente Python preparado com sucesso."

install-appium:
	@command -v npm >/dev/null 2>&1 \
		|| ( echo "npm não encontrado."; \
		     echo "Instale Node.js/npm antes de continuar."; \
		     exit 1 )
	@echo "Configurando instalação npm para o usuário atual..."
	@mkdir -p "$(NPM_PREFIX)"
	@npm config set prefix "$(NPM_PREFIX)"
	@# --- Appium ---
	@if [ ! -x "$(APPIUM_BIN)" ]; then \
		echo "Instalando appium$(if $(APPIUM_VERSION),@$(APPIUM_VERSION))..."; \
		npm install -g "appium$(if $(APPIUM_VERSION),@$(APPIUM_VERSION))" \
			|| ( echo "Falha ao instalar Appium."; exit 1 ); \
	elif [ -n "$(APPIUM_VERSION)" ] && [ "$$($(APPIUM_BIN) --version)" != "$(APPIUM_VERSION)" ]; then \
		echo "Alinhando Appium: $$($(APPIUM_BIN) --version) -> $(APPIUM_VERSION)..."; \
		npm install -g "appium@$(APPIUM_VERSION)" \
			|| ( echo "Falha ao alinhar Appium."; exit 1 ); \
	else \
		echo "Appium OK: $$($(APPIUM_BIN) --version)"; \
	fi
	@# --- Driver UiAutomator2 ---
	@# Presença: 'driver list' escreve a lista no stderr; capturamos os dois
	@# streams com 2>&1 e casamos o nome do driver. Não depende da forma do
	@# JSON, então é robusto entre versões do Appium (era esse o bug: o
	@# 2>/dev/null anterior descartava justamente onde 'uiautomator2' aparece).
	@if "$(APPIUM_BIN)" driver list --installed 2>&1 | grep -qw "uiautomator2"; then \
		if [ -n "$(UIAUTOMATOR2_VERSION)" ]; then \
			echo "Alinhando uiautomator2 -> $(UIAUTOMATOR2_VERSION)..."; \
			"$(APPIUM_BIN)" driver uninstall uiautomator2 >/dev/null \
				&& "$(APPIUM_BIN)" driver install "uiautomator2@$(UIAUTOMATOR2_VERSION)" \
				|| ( echo "Falha ao alinhar o driver UiAutomator2."; exit 1 ); \
		else \
			echo "Driver uiautomator2 já instalado."; \
		fi; \
	else \
		echo "Instalando driver uiautomator2$(if $(UIAUTOMATOR2_VERSION),@$(UIAUTOMATOR2_VERSION))..."; \
		"$(APPIUM_BIN)" driver install "uiautomator2$(if $(UIAUTOMATOR2_VERSION),@$(UIAUTOMATOR2_VERSION))" \
			|| ( echo "Falha ao instalar o driver UiAutomator2."; exit 1 ); \
	fi
	@echo "Appium: $$($(APPIUM_BIN) --version)"
	@echo "Appium e UiAutomator2 preparados com sucesso."
	@if ! echo ":$$PATH:" | grep -q ":$(NPM_BIN):"; then \
		echo ""; \
		echo "ATENÇÃO: $(NPM_BIN) não está no PATH deste shell."; \
		echo 'Adicione ao ~/.zshrc: export PATH="$$HOME/.npm-global/bin:$$PATH"'; \
		echo "Depois execute: source ~/.zshrc"; \
	fi

# Atualização explícita do driver (dev local; não usar em CI pinado).
appium-update:
	@"$(APPIUM_BIN)" driver update uiautomator2

# Configuração local do git (não é clonada): hook de pre-commit com o
# lint e os unitários.
git-hooks:
	@git config core.hooksPath .githooks
	@echo "Hooks do git ativados (.githooks)."

setup: install install-appium git-hooks
	@echo ""
	@echo "Ambiente de automação preparado com sucesso."
	@echo "Execute 'make doctor' para validar."

# === Validação de ambiente ===
check-venv:
	@test -x "$(PYTHON)" \
		|| ( echo "Ambiente virtual não encontrado em '$(VENV)'."; \
		     echo "Execute 'make install'."; \
		     exit 1 )
	@$(PYTHON) -c "import sys; req=tuple(int(p) for p in '$(PYTHON_MIN_VERSION)'.split('.')); sys.exit(0 if sys.version_info[:len(req)] >= req else 1)" \
		|| ( echo "Python do venv abaixo do mínimo exigido (>= $(PYTHON_MIN_VERSION))."; \
		     echo "Versão atual: $$($(PYTHON) --version 2>&1)"; \
		     exit 1 )

check-config:
	@test -f "$(ENV_FILE)" \
		|| ( echo "Arquivo de configuração ausente: $(ENV_FILE)"; \
		     echo "Crie-o a partir de '$(ENV_EXAMPLE_FILE)'."; \
		     exit 1 )

check-test-data:
	@test -f "$(TEST_DATA_FILE)" \
		|| ( echo "Arquivo de massa de teste ausente: $(TEST_DATA_FILE)"; \
		     exit 1 )

# APK só com APP_SOURCE=apk (package usa o app já instalado no device).
check-app:
	@$(PYTHON) scripts/check_app.py

check-devices:
	@test -f "$(DEVICES_FILE)" \
		|| ( echo "Arquivo de dispositivos ausente: $(DEVICES_FILE)"; \
		     exit 1 )

check-appium:
	@curl -sf --max-time 3 "http://$(APPIUM_HOST):$(APPIUM_PORT)/status" >/dev/null 2>&1 \
		|| ( echo "Appium não está respondendo em http://$(APPIUM_HOST):$(APPIUM_PORT)"; \
		     echo "Inicie o servidor executando 'appium'."; \
		     echo "Detalhes: 'make doctor'."; \
		     exit 1 )

# Gate para testes mobile
check-mobile: check-venv check-config check-test-data check-app check-appium

# === Diagnóstico ===
doctor:
	@PYTHON="$(PYTHON)" \
	 VENV="$(VENV)" \
	 PYTHON_MIN_VERSION="$(PYTHON_MIN_VERSION)" \
	 APPIUM_HOST="$(APPIUM_HOST)" \
	 APPIUM_PORT="$(APPIUM_PORT)" \
	 ENV_FILE="$(ENV_FILE)" \
	 ENV_EXAMPLE_FILE="$(ENV_EXAMPLE_FILE)" \
	 TEST_DATA_FILE="$(TEST_DATA_FILE)" \
	 DEVICES_FILE="$(DEVICES_FILE)" \
	 REQUIREMENTS="$(REQUIREMENTS)" \
	 bash scripts/doctor.sh

# === Qualidade de código ===
# Configuração em pyproject.toml.
lint: check-venv
	@$(RUFF) check .
	@$(RUFF) format --check .

format: check-venv
	@$(RUFF) check --fix .
	@$(RUFF) format .

# === Servidores Appium ===
# Sobe o servidor do Appium para a suíte (emulador e celular): grava o
# log em reports/appium.log, com horário em cada linha (para investigar
# quedas do UiAutomator2), além de mostrar no terminal. Emulador e celular
# ao mesmo tempo no mesmo servidor: ANDROID_SYSTEM_PORT diferente em cada
# env (ver config/env.*.example.yaml).
APPIUM_LOG := reports/appium.log

appium:
	@test -x "$(APPIUM_BIN)" || ( echo "Appium não instalado: make install-appium"; exit 1 )
	@mkdir -p reports
	@echo "Appium em http://$(APPIUM_HOST):$(APPIUM_PORT) (log: $(APPIUM_LOG)). Ctrl+C para parar."
	@"$(APPIUM_BIN)" \
		--address $(APPIUM_HOST) \
		--port $(APPIUM_PORT) \
		--log-timestamp \
		--local-timezone \
		--log $(APPIUM_LOG)

appium-servers: check-venv check-devices
	@bash scripts/start-appium-servers.sh

# === Análise de impacto ===
impact: check-venv
	@if [ -z "$(file)" ]; then \
		echo "Informe o arquivo. Exemplo: make impact file=login_page.py"; \
		exit 1; \
	fi
	@$(PYTHON) scripts/impact.py "$(file)"

# === Helper de execução pytest ===
# APP_PATH e TEST_DATA_FILE não são repassados: o shell tem precedência
# sobre o env.<device>.yaml, então exportá-los aqui anularia o APP_PATH
# dele. Os defaults do código apontam para os mesmos caminhos.
define run_pytest_with_report
	@LOG_LEVEL="$(LOG_LEVEL)" \
	$(PYTEST) $(1) $(2); \
	status=$$?; \
	if [ $$status -ne 0 ]; then \
		echo "Falha detectada. Abrindo report..."; \
		$(MAKE) report; \
	elif [ -f "$(REPORTS)/.pulados" ]; then \
		echo "$$(cat "$(REPORTS)/.pulados") teste(s) pulado(s). Abrindo report..."; \
		$(MAKE) report; \
	fi; \
	exit $$status
endef

# === Configuração de ambiente ===


# === Execuções ===
# Inclui os testes que consomem massa (--consumir-massa), como no iOS;
# hoje nenhum teste do Android consome.
run: check-mobile
	$(call run_pytest_with_report,$(FULL_SUITE),$(PYTEST_FLAGS_CLEAN) --consumir-massa $(PYTEST_FLAGS))

debug: check-mobile
	$(call run_pytest_with_report,$(DEBUG_TARGET),$(PYTEST_FLAGS_DEBUG) $(PYTEST_FLAGS))

# Casos de teste pelo ID, na ordem da suíte: make ct id=CT010 (ou CT010,CT011).
# Pedir o CT é escolha explícita: inclui os que consomem massa.
ct: check-mobile
	@if [ -z "$(id)" ]; then \
		echo "Informe o CT. Exemplo: make ct id=CT010 (vários: id=CT010,CT011)"; \
		exit 1; \
	fi
	$(call run_pytest_with_report,$(FULL_SUITE) --ct "$(id)",$(PYTEST_FLAGS_CLEAN) --consumir-massa $(PYTEST_FLAGS))

# Só os testes que falharam na última execução (cache do pytest; o make
# clear apaga). Sem falhas registradas, não roda nada.
falhas: check-mobile
	$(call run_pytest_with_report,$(FULL_SUITE) --last-failed --last-failed-no-failures none,$(PYTEST_FLAGS_CLEAN) --consumir-massa $(PYTEST_FLAGS))

# === Testes unitários ===
# Sem Appium nem emulador. O plugin de report fica desligado: ele gera
# um HTML por execução e descarta os mais antigos, o que empurraria para
# fora os reports das execuções reais.
unit: check-venv
	@$(PYTEST) $(UNIT_TESTS) -q -p no:observability.pytest_report $(PYTEST_FLAGS)

# === Testes por marker ===
# Inclui os que consomem massa; merge-dev e merge-main dependem deste
# alvo. Sem massa, eles pulam e o merge segue.
smoke: check-mobile
	$(call run_pytest_with_report,$(FULL_SUITE) -m "smoke",$(PYTEST_FLAGS_CLEAN) --consumir-massa $(PYTEST_FLAGS))

regression: check-mobile
	$(call run_pytest_with_report,$(FULL_SUITE) -m "regression",$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

e2e: check-mobile
	$(call run_pytest_with_report,$(TEST_E2E) -m "e2e",$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

e2e-debug: check-mobile
	$(call run_pytest_with_report,$(TEST_E2E) -m "e2e",$(PYTEST_FLAGS_DEBUG) $(PYTEST_FLAGS))

registro-ponto: check-mobile
	$(call run_pytest_with_report,$(TEST_REGISTRO_PONTO),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

# Jornada: e2e + registro de ponto
dados-pessoais: check-mobile
	$(call run_pytest_with_report,$(TEST_DADOS_PESSOAIS),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

privacidade: check-mobile
	$(call run_pytest_with_report,$(TEST_PRIVACIDADE),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

# Apaga os dados do app no aparelho (Ajustes e menu do perfil) e refaz o
# primeiro acesso a cada SIM.
zerar-dados: check-mobile
	$(call run_pytest_with_report,$(TEST_ZERAR_DADOS),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

jornada: check-mobile
	$(call run_pytest_with_report,$(TEST_E2E) $(TEST_REGISTRO_PONTO),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

# === Testes por arquivo ===
onboarding: check-mobile
	$(call run_pytest_with_report,$(TEST_ONBOARDING),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

login: check-mobile
	$(call run_pytest_with_report,$(TEST_LOGIN),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

unlock: check-mobile
	$(call run_pytest_with_report,$(TEST_UNLOCK),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

primeiro-acesso: check-mobile
	$(call run_pytest_with_report,$(TEST_ONBOARDING) $(TEST_LOGIN) $(TEST_UNLOCK),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

api: check-venv check-config check-test-data
	$(call run_pytest_with_report,$(API_TESTS),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

# === Relatórios ===
# Zera só o histórico do dashboard (reports/history.json); o resto fica.
limpar-historico:
	@rm -f $(HISTORY_FILE)
	@echo "Histórico de execuções zerado ($(HISTORY_FILE))."

# Sem DEVICE: limpa tudo (todos os aparelhos). Com DEVICE=…: só ele.
# Fica a reports/assets (visual do report, versionado) e o appium.log
# (o make appium pode estar escrevendo nele).
clear:
ifeq ($(origin DEVICE),command line)
	@echo "Limpando reports, histórico e caches de $(DEVICE)..."
	@rm -rf $(REPORTS) .pytest_cache/$(DEVICE)
else
	@echo "Limpando reports, histórico e caches de todos os aparelhos..."
	@find reports -mindepth 1 -maxdepth 1 ! -name assets ! -name appium.log -exec rm -rf {} +
	@rm -f reports/.pulados
	@rm -rf .pytest_cache
endif
	@find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -not -path "./venv/*" -delete 2>/dev/null || true

report:
	@echo "Abrindo último report..."
	@latest_report=$$(ls -t $(REPORTS)/*.html 2>/dev/null | head -n 1); \
	if [ -n "$$latest_report" ]; then \
		open "$$latest_report"; \
	else \
		echo "Nenhum report encontrado em $(REPORTS)."; \
	fi

# Renumera os CTs na ordem da suíte. Sem aplicar=1, só mostra o mapa.
renumerar-ct: check-venv
	@$(PYTHON) scripts/renumerar_ct.py $(if $(aplicar),--aplicar,)

report-pdf: check-venv
	@test -f "$(EXPORT_REPORT_PDF)" \
		|| ( echo "Script de exportação não encontrado: $(EXPORT_REPORT_PDF)"; \
		     echo "Crie o script antes de executar 'make report-pdf'."; \
		     exit 1 )
	@$(PYTHON) "$(EXPORT_REPORT_PDF)"

# === Git ===
git-status:
	git status

commit:
	@if [ -z "$(m)" ]; then \
		echo "Informe a mensagem do commit. Exemplo: make commit m=\"feat: ajustar fluxo de login\""; \
		exit 1; \
	fi
	git add .
	git commit -m "$(m)"

push:
	git push origin $$(git branch --show-current)

update-dev:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Existem alterações não commitadas. Faça commit ou stash antes de continuar."; \
		exit 1; \
	fi
	git checkout $(BRANCH_DEV)
	git pull origin $(BRANCH_DEV)

update-feature:
	@CURRENT_BRANCH=$$(git branch --show-current); \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "Existem alterações não commitadas. Faça commit ou stash antes de continuar."; \
		exit 1; \
	fi; \
	if [ "$$CURRENT_BRANCH" = "$(BRANCH_DEV)" ] || [ "$$CURRENT_BRANCH" = "$(BRANCH_MAIN)" ]; then \
		echo "Troque para uma feature antes de executar este comando."; \
		exit 1; \
	fi; \
	git checkout $(BRANCH_DEV) && \
	git pull origin $(BRANCH_DEV) && \
	git checkout $$CURRENT_BRANCH && \
	git merge $(BRANCH_DEV)

start-feature:
	@if [ -z "$(name)" ]; then \
		echo "Informe o nome da feature. Exemplo: make start-feature name=niza-login"; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Existem alterações não commitadas. Faça commit ou stash antes de continuar."; \
		exit 1; \
	fi
	git checkout $(BRANCH_DEV)
	git pull origin $(BRANCH_DEV)
	git checkout -b feature/$(name)

merge-dev: smoke
	@CURRENT_BRANCH=$$(git branch --show-current); \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "Existem alterações não commitadas. Faça commit ou stash antes de continuar."; \
		exit 1; \
	fi; \
	if [ "$$CURRENT_BRANCH" = "$(BRANCH_DEV)" ]; then \
		echo "Você já está na branch $(BRANCH_DEV)."; \
		exit 1; \
	fi; \
	if [ "$$CURRENT_BRANCH" = "$(BRANCH_MAIN)" ]; then \
		echo "Não é permitido mesclar $(BRANCH_MAIN) em $(BRANCH_DEV) por este comando."; \
		exit 1; \
	fi; \
	echo "Mesclando $$CURRENT_BRANCH em $(BRANCH_DEV)..."; \
	git checkout $(BRANCH_DEV) && \
	git pull origin $(BRANCH_DEV) && \
	git merge $$CURRENT_BRANCH && \
	git push origin $(BRANCH_DEV)

merge-main: smoke
	@CURRENT_BRANCH=$$(git branch --show-current); \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "Existem alterações não commitadas. Faça commit ou stash antes de continuar."; \
		exit 1; \
	fi; \
	echo "Mesclando $(BRANCH_DEV) em $(BRANCH_MAIN)..."; \
	git checkout $(BRANCH_MAIN) && \
	git pull origin $(BRANCH_MAIN) && \
	git merge $(BRANCH_DEV) && \
	git push origin $(BRANCH_MAIN) && \
	git checkout $(BRANCH_DEV) && \
	echo "Merge concluído. De volta à $(BRANCH_DEV)."

merge-branch: smoke
	@if [ -z "$(source)" ] || [ -z "$(target)" ]; then \
		echo "Informe source e target. Exemplo: make merge-branch source=feature/niza target=desenvolvimento"; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Existem alterações não commitadas. Faça commit ou stash antes de continuar."; \
		exit 1; \
	fi
	@echo "Mesclando $(source) em $(target)..."
	git checkout $(target)
	git pull origin $(target)
	git merge $(source)
	git push origin $(target)

delete-branch:
	@if [ -z "$(name)" ]; then \
		echo "Informe o nome da branch. Exemplo: make delete-branch name=feature/niza-login"; \
		exit 1; \
	fi
	@if [ "$(name)" = "$(BRANCH_DEV)" ] || [ "$(name)" = "$(BRANCH_MAIN)" ]; then \
		echo "Não é permitido excluir $(name)."; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Existem alterações não commitadas. Faça commit ou stash antes de continuar."; \
		exit 1; \
	fi
	@git branch -d $(name) || ( \
		echo "A branch $(name) tem commits não mesclados."; \
		echo "Revise antes de excluir. Para forçar manualmente:"; \
		echo "  git branch -D $(name)"; \
		exit 1; \
	)
	@# Feature que nunca foi enviada ao GitHub não tem o que apagar no
	@# remoto: checa antes, em vez de deixar o push falhar com erro.
	@if git ls-remote --exit-code --heads origin "$(name)" >/dev/null 2>&1; then \
		git push origin --delete "$(name)"; \
	else \
		echo "Branch $(name) não existe no remoto; nada a apagar lá."; \
	fi
	@git fetch --prune