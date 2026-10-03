# === Variáveis ===
VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest

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
INTEGRATION_TESTS := $(TESTS)/integration

# Arquivos de app - ordem lógica de execução
TEST_ONBOARDING := $(APP_TESTS)/test_onboarding.py
TEST_LOGIN := $(APP_TESTS)/test_login.py
TEST_UNLOCK := $(APP_TESTS)/test_unlock.py
TEST_E2E := $(APP_TESTS)/test_e2e.py
TEST_REGISTRO_PONTO := $(APP_TESTS)/test_registro_sem_foto.py

# Suíte principal de app em ordem controlada
APP_SUITE := \
	$(TEST_ONBOARDING) \
	$(TEST_LOGIN) \
	$(TEST_UNLOCK) \
	$(TEST_E2E) \
	$(TEST_REGISTRO_PONTO)

# Suíte completa em ordem controlada
FULL_SUITE := \
	$(APP_SUITE) \
	$(API_TESTS) \
	$(INTEGRATION_TESTS)

# Relatórios
REPORTS := reports
SCREENSHOTS := $(REPORTS)/screenshots
HISTORY_FILE := $(REPORTS)/history.json
EXPORT_REPORT_PDF := scripts/export_report_pdf.py

# === Arquivos locais (não versionados) ===
#
# env.yaml, test_data.yaml e o APK Android contêm dados locais/sensíveis
# e ficam fora do controle de versão (.gitignore), mas dentro do projeto.
#
ENV_FILE := config/env.yaml
TEST_DATA_FILE := config/test_data.yaml
APP_PATH := app/ifPontoCell.apk

# Arquivos seguros/versionados dentro do projeto
ENV_EXAMPLE_FILE := config/env.example.yaml
DEVICES_FILE := config/devices.yaml
REQUIREMENTS := requirements.txt

# Branches padrão
BRANCH_DEV := desenvolvimento
BRANCH_MAIN := main

# Controle de log
LOG_LEVEL ?= INFO

# Flags adicionais opcionais
PYTEST_FLAGS ?=

# Execução padrão:
# exibe apenas progresso, resumo customizado e caminho do report.
PYTEST_FLAGS_CLEAN := \
	-q \
	-o verbosity_test_cases=1 \
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
        venv install install-appium appium-update setup \
        check-venv check-config check-test-data check-app check-devices \
        check-appium check-mobile \
        doctor impact appium-servers \
        set-simulator set-real \
        run debug smoke regression \
        onboarding login unlock primeiro-acesso e2e e2e-debug registro-ponto jornada \
        api integration bloqueio \
        clear report report-pdf \
        status commit push update-dev update-feature start-feature \
        merge-dev merge-main merge-branch delete-branch

# === Ajuda ===
help:
	@echo ""
	@echo "=== Ambiente ==="
	@echo "  make setup                 Prepara venv, dependências Python, Appium e UiAutomator2"
	@echo "  make install               Cria o venv se necessário e instala dependências Python"
	@echo "  make install-appium        Instala Appium e UiAutomator2 no usuário atual"
	@echo "  make appium-update         Atualiza o driver UiAutomator2 para a última compatível"
	@echo "  make doctor                Diagnóstico completo do ambiente"
	@echo "  make impact file=x.py      Mostra quem depende de um arquivo"
	@echo "  make appium-servers        Sobe servidores Appium definidos em devices.yaml"
	@echo "  make set-simulator         Ajusta o env.yaml para emulador Android (.apk)"
	@echo "  make set-real              Ajusta o env.yaml para device real"
	@echo ""
	@echo "=== Execução ==="
	@echo "  make run                   Roda suíte completa em ordem lógica"
	@echo "  make debug                 Roda suíte completa em modo debug"
	@echo "  make debug test=arquivo    Roda arquivo ou teste específico em modo debug"
	@echo ""
	@echo "=== Testes ==="
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
	@echo "  make api                   Roda testes de API"
	@echo "  make integration           Roda testes de integração"
	@echo "  make bloqueio              Roda teste de bloqueio de celular"
	@echo ""
	@echo "=== Reports ==="
	@echo "  make clear                 Limpa reports, histórico, screenshots e caches"
	@echo "  make report                Abre o último report HTML"
	@echo "  make report-pdf            Exporta o último report HTML para PDF"
	@echo ""
	@echo "=== Git ==="
	@echo "  make status                Exibe status do git"
	@echo "  make commit m=\"msg\"       Cria commit"
	@echo "  make push                  Envia branch atual"
	@echo "  make update-dev            Atualiza desenvolvimento"
	@echo "  make update-feature        Atualiza feature com desenvolvimento"
	@echo "  make start-feature name=x  Cria nova feature"
	@echo "  make merge-dev             Testa e mescla feature na desenvolvimento"
	@echo "  make merge-main            Testa e mescla desenvolvimento na main"
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

setup: install install-appium
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

check-app:
	@source="$$(ENV_FILE="$(ENV_FILE)" "$(PYTHON)" -c 'import os, yaml; data = yaml.safe_load(open(os.environ["ENV_FILE"], encoding="utf-8")) or {}; print(str(data.get("APP_SOURCE", "")).strip().lower())')"; \
	app_path="$$(ENV_FILE="$(ENV_FILE)" "$(PYTHON)" -c 'import os, yaml; data = yaml.safe_load(open(os.environ["ENV_FILE"], encoding="utf-8")) or {}; print(str(data.get("APP_PATH", "")).strip())')"; \
	package="$$(ENV_FILE="$(ENV_FILE)" "$(PYTHON)" -c 'import os, yaml; data = yaml.safe_load(open(os.environ["ENV_FILE"], encoding="utf-8")) or {}; print(str(data.get("ANDROID_APP_PACKAGE", "")).strip())')"; \
	if [ "$$source" = "apk" ]; then \
		if [ -z "$$app_path" ]; then \
			echo "APP_SOURCE=apk exige APP_PATH no $(ENV_FILE)."; \
			echo 'Exemplo: APP_PATH: "app/ifPontoCell.apk"'; \
			exit 1; \
		fi; \
		test -f "$$app_path" \
			|| ( echo "APK não encontrado: $$app_path"; \
			     echo "Adicione o APK no caminho configurado ou use APP_SOURCE=package."; \
			     exit 1 ); \
	elif [ "$$source" = "package" ]; then \
		test -n "$$package" \
			|| ( echo "APP_SOURCE=package exige ANDROID_APP_PACKAGE no $(ENV_FILE)."; \
			     exit 1 ); \
	else \
		echo "APP_SOURCE inválido: '$$source'. Use 'apk' ou 'package'."; \
		exit 1; \
	fi

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
	 APP_PATH="$(APP_PATH)" \
	 DEVICES_FILE="$(DEVICES_FILE)" \
	 REQUIREMENTS="$(REQUIREMENTS)" \
	 bash scripts/doctor.sh

# === Servidores Appium ===
appium-servers: check-venv check-devices
	@bash scripts/start-appium-servers.sh

# === Análise de impacto ===
impact:
	@if [ -z "$(file)" ]; then \
		echo "Informe o arquivo. Exemplo: make impact file=login_page.py"; \
		exit 1; \
	fi
	@bash scripts/impact.sh "$(file)"

# === Helper de execução pytest ===
define run_pytest_with_report
	@LOG_LEVEL="$(LOG_LEVEL)" \
	ENV_FILE="$(ENV_FILE)" \
	TEST_DATA_FILE="$(TEST_DATA_FILE)" \
	APP_PATH="$(APP_PATH)" \
	$(PYTEST) $(1) $(2); \
	status=$$?; \
	if [ $$status -ne 0 ]; then \
		echo "Falha detectada. Abrindo report..."; \
		$(MAKE) report; \
	fi; \
	exit $$status
endef

# === Configuração de ambiente ===
set-simulator: check-config
	@echo "Configurando env.yaml para EMULADOR Android..."
	@sed -i '' 's/^ANDROID_TARGET:.*/ANDROID_TARGET: "emulator"/' "$(ENV_FILE)"
	@echo "ANDROID_TARGET=emulator"

set-real: check-config
	@echo "Configurando env.yaml para DEVICE Android REAL..."
	@sed -i '' 's/^ANDROID_TARGET:.*/ANDROID_TARGET: "real"/' "$(ENV_FILE)"
	@echo "ANDROID_TARGET=real"

# === Execuções ===
run: check-mobile
	$(call run_pytest_with_report,$(FULL_SUITE),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

debug: check-mobile
	$(call run_pytest_with_report,$(DEBUG_TARGET),$(PYTEST_FLAGS_DEBUG) $(PYTEST_FLAGS))

# === Testes por marker ===
smoke: check-mobile
	$(call run_pytest_with_report,$(FULL_SUITE) -m "smoke",$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

regression: check-mobile
	$(call run_pytest_with_report,$(FULL_SUITE) -m "regression",$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

e2e: check-mobile
	$(call run_pytest_with_report,$(TEST_E2E) -m "e2e",$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

e2e-debug: check-mobile
	$(call run_pytest_with_report,$(TEST_E2E) -m "e2e",$(PYTEST_FLAGS_DEBUG) $(PYTEST_FLAGS))

registro-ponto: check-mobile
	$(call run_pytest_with_report,$(TEST_REGISTRO_PONTO),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

# Jornada: e2e + registro de ponto
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

integration: check-mobile
	$(call run_pytest_with_report,$(INTEGRATION_TESTS),$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

bloqueio: check-mobile
	$(call run_pytest_with_report,$(INTEGRATION_TESTS)/test_bloqueio_celular.py,$(PYTEST_FLAGS_CLEAN) $(PYTEST_FLAGS))

# === Relatórios ===
clear:
	@echo "Limpando reports, histórico e caches..."
	@rm -f $(REPORTS)/*.html
	@rm -f $(REPORTS)/*.pdf
	@rm -f $(REPORTS)/resultado_testes.txt
	@rm -f $(HISTORY_FILE)
	@rm -rf $(SCREENSHOTS)
	@rm -rf .pytest_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

report:
	@echo "Abrindo último report..."
	@latest_report=$$(ls -t $(REPORTS)/*.html 2>/dev/null | head -n 1); \
	if [ -n "$$latest_report" ]; then \
		open "$$latest_report"; \
	else \
		echo "Nenhum report encontrado em $(REPORTS)."; \
	fi

report-pdf: check-venv
	@test -f "$(EXPORT_REPORT_PDF)" \
		|| ( echo "Script de exportação não encontrado: $(EXPORT_REPORT_PDF)"; \
		     echo "Crie o script antes de executar 'make report-pdf'."; \
		     exit 1 )
	@$(PYTHON) "$(EXPORT_REPORT_PDF)"

# === Git ===
status:
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
	git push origin $(BRANCH_MAIN)

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
	git push origin --delete $(name) || true
	git fetch --prune