# Android Automation — Appium + Pytest

Framework de automação mobile do **ifPontoCell Android** com **Pytest + Appium + UiAutomator2**, organizado em Page Objects e executado pelo `Makefile`.

A arquitetura é a mesma do projeto irmão `ifpontocell-ios-automation` (configuração tipada, env por aparelho, fixtures por assunto, pages em pastas por menu, report com histórico e vídeo). O que é específico do Android — e por quê — está em [DECISOES.md](DECISOES.md).

---

## Objetivo

Validar os fluxos críticos do app Android com testes estáveis e diagnósticos claros na falha:

* primeiro acesso em corrente (onboarding → login → PIN → Home)
* registro de ponto sem foto
* integração com a API de controle de celular (ativação e `sem_foto`)

---

## Tecnologias

* Python 3.10+ / Pytest
* Appium 2 + driver UiAutomator2
* Appium Python Client / Selenium
* Android SDK (adb, emulador)
* pytest-html (report com dashboard, histórico e vídeo)
* ruff (lint e formatação, também no pre-commit)

---

## Estrutura do ambiente

Arquivos da máquina, credenciais, massa de teste e o APK ficam dentro do repositório, mas fora do versionamento (`.gitignore`):

```text
ifpontocell-android-automation/
│
├── app/
│   └── ifPontoCell.apk
│
├── config/
│   ├── env.emulator.yaml
│   ├── env.real.yaml
│   └── test_data.yaml
│
├── api/  core/  observability/  pages/  reports/  scripts/  tests/  utils/
├── venv/
├── Makefile
├── pytest.ini
└── requirements.txt
```

---

## Arquitetura

```text
ifpontocell-android-automation/
│
├── api/
│   ├── configuracao_app_client.py       # Configuração > Tela do aplicativo
│   ├── ifponto_api_client.py            # base: transporte, auth, parse e escrita genérica
│   └── monitor_celular_client.py        # Monitor > Celular
│
├── config/
│   ├── capabilities.py                  # Settings -> capabilities UiAutomator2
│   ├── devices.yaml                     # devices p/ execução paralela (local)
│   ├── env.emulator.example.yaml        # template do emulador
│   ├── env.real.example.yaml            # template do celular
│   ├── env_loader.py                    # carga do env do aparelho para o ambiente
│   ├── settings.py                      # configuração tipada e validada
│   └── timeouts.py
│
├── core/
│   ├── app_session.py                   # ciclo de vida do app (relaunch)
│   ├── driver_factory.py                # sessão Appium + adb uninstall no cold start
│   ├── launch_profile.py                # cold start / sessão morna / permissões
│   ├── localizacao.py                   # localização simulada (set_location)
│   └── privacy_services.py
│
├── observability/                       # report, dashboard, histórico, vídeo, CTs
│
├── pages/
│   ├── android_locators.py              # android_id / android_text / ...
│   ├── base_page.py                     # waits, clique, digitação conferida, logging
│   ├── alertas.py                       # alertas do app (mixin)
│   ├── navegacao.py                     # voltar para a Home (mixin)
│   ├── home_page.py                     # Home, popups e registro de ponto
│   ├── menu_page.py                     # menu lateral e menu do perfil
│   ├── autenticacao/                    # onboarding, login, unlock (PIN), autorização
│   ├── ajustes/                         # Ajustes do Aplicativo
│   └── zerar_dados/                     # diálogo Zerar Dados (recomeçar o primeiro acesso)
│
├── scripts/                             # doctor, setup, check_app, impact, report PDF...
│
├── tests/
│   ├── api/                             # API de controle de celular
│   ├── app/                             # onboarding, login, unlock, e2e, registro sem foto
│   ├── fixtures/                        # fixtures por assunto (plugins do conftest)
│   ├── support/                         # flows, assertions, profile_resolver
│   └── unit/                            # unitários (make unit, sem emulador)
│
└── utils/                               # logger, períodos, ponto, textos, report
```

---

## Camadas do projeto

### `config/`

`settings.py` é o único lugar que interpreta as variáveis do `env.<aparelho>.yaml`: converte, aplica defaults, valida e lista todos os erros de uma vez (`ConfiguracaoInvalida`). O resto do código usa `Settings.from_env()`, nunca `os.getenv`. `capabilities.py` só traduz o `Settings` em capabilities do UiAutomator2.

### `core/`

`driver_factory.py` cria a sessão Appium; no cold start com `APP_SOURCE=apk`, desinstala o app pelo `adb` antes. `app_session.py` relança o app pelo `appPackage`. `localizacao.py` aplica a localização simulada (emulador e celular).

### `pages/`

Uma classe por tela, com **uma pasta por menu do app** (regra do iOS: está no menu X, vai para `X/`; usada por mais de um menu, `compartilhado/`). Os locators usam `pages/android_locators.py`, por `resource-id` sem depender do package. Locators ainda provisórios estão em [PENDENCIAS_LOCATORS_ANDROID.md](PENDENCIAS_LOCATORS_ANDROID.md).

### `tests/fixtures/`

Fixtures por assunto, registradas pelo `conftest.py` via `pytest_plugins` (o `conftest.py` só carrega o env e lista os plugins): `sessoes.py`, `jornada.py` (sessão compartilhada e Home autenticada), `api.py`, `dados.py`, `devices.py`, `geo.py`, `massa.py`, `casos_teste.py`.

### `tests/support/`

* `flows.py` — fluxos reutilizáveis, incluindo a corrente do primeiro acesso
* `assertions.py` — validações do caminho negativo
* `profile_resolver.py` — `LaunchProfile` do teste atual

---

## Padrões adotados

* **Page Object Model** — testes não acessam o driver diretamente
* **Configuração tipada e validada** — `Settings`, erros todos de uma vez
* **Um env por aparelho** — emulador e celular ao mesmo tempo, cada um com seu usuário
* **Sessão morna** — testes de tela partem da Home autenticada sem reinstalar
* **Primeiro acesso em corrente** — onboarding → login → unlock → e2e numa sessão só
* **Postcondition positiva** — popup de erro é checado ativamente no caminho feliz
* **Makefile como interface de execução**

---

## Preparação do ambiente

```bash
make setup     # venv, dependências, Appium + UiAutomator2, hooks do git
make doctor    # diagnóstico (Python, adb, devices, Appium, env, APK)
```

Requisitos fora do projeto: Node.js/npm (Appium) e o Android SDK com `platform-tools` e `emulator` no `PATH` (`ANDROID_HOME`).

---

## Configuração de execução

Um arquivo por aparelho, cada um com **o seu usuário de teste** (com o mesmo usuário, os dois brigariam pelo login, pela ativação do celular e pela massa):

```bash
cp config/env.emulator.example.yaml config/env.emulator.yaml   # padrão
cp config/env.real.example.yaml     config/env.real.yaml       # DEVICE=real
```

> Quem usava o `config/env.yaml` antigo: renomeie para `config/env.emulator.yaml` e confira as chaves novas no template (`ANDROID_SYSTEM_PORT`, `ANDROID_GEO_*`, `APP_JORNADA`).

Principais chaves:

```yaml
APP_SOURCE: "apk"                 # apk | package (app já instalado)
APP_PATH: "app/ifPontoCell.apk"
ANDROID_TARGET: "emulator"        # emulator | real
ANDROID_APP_PACKAGE: "br.com.ifractal.Stou"
ANDROID_UDID: ""                  # obrigatório no celular (adb devices)
ANDROID_SYSTEM_PORT: "8200"       # 8201 no celular, para rodar os dois juntos
```

### Celular (device real)

1. Opções do desenvolvedor ligadas e **depuração USB** ativa; autorize o computador.
2. `adb devices` mostra o aparelho como `device`: copie o identificador para `ANDROID_UDID`.
3. Localização simulada: Opções do desenvolvedor → *Selecionar app de local fictício* → **Appium Settings** (instalado pelo UiAutomator2 na primeira sessão).
4. `make doctor DEVICE=real` e depois `make smoke DEVICE=real`.

### Emulador e celular ao mesmo tempo

Dois terminais, um servidor Appium: `make smoke` e `make smoke DEVICE=real`. Cada aparelho tem o seu report (`reports/emulator/`, `reports/real/`), histórico e cache do `make falhas`.

---

## Execução

```bash
make unit                 # unitários (~1s, sem emulador)
make run                  # suíte completa em ordem lógica
make smoke                # testes smoke
make regression
make primeiro-acesso      # onboarding > login > unlock
make onboarding | login | unlock | e2e | registro-ponto | jornada
make api
make ct id=CT005          # pelo ID do caso de teste
make falhas               # só o que falhou na última execução
make debug test=tests/app/test_login.py::test_credenciais_validas
```

Variações: `DEVICE=real` (celular), `VIDEO=1` (vídeo de todos os testes; padrão: só das falhas), `VIDEO=0`.

---

## Relatórios

```bash
make report        # abre o último report
make report-pdf    # exporta para PDF
make clear         # limpa reports, histórico, vídeos e caches
```

O report traz o dashboard da execução, o histórico (falhas novas, recorrentes, instáveis), print e árvore da tela na falha e o vídeo dos testes que falharam (`adb screenrecord`, sem ffmpeg; até 3 min por teste).

---

## Qualidade de código

```bash
make lint      # ruff check + format --check
make format    # corrige
make git-hooks # pre-commit com lint + unitários (uma vez por clone)
```

---

## Git

Fluxo `main` ← `desenvolvimento` ← `feature/*`, pelos alvos do Makefile (`start-feature`, `commit`, `merge-dev`, `merge-main`...). Ver [GIT_GUIDE.md](GIT_GUIDE.md).

---

## Comandos principais

```bash
make help
```
