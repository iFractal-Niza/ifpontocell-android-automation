# ifPontoCell Android Automation

Framework de automação mobile Android com **Pytest + Appium + UiAutomator2 + Selenium**, organizado em Page Objects e executado pelo `Makefile`.

## Stack

- Python / Pytest
- Appium Python Client
- Appium UiAutomator2 Driver
- Selenium
- Page Object Model
- macOS como ambiente de desenvolvimento

## Estrutura

```text
config/       env.yaml, env.example.yaml, devices.yaml, test_data.yaml
core/         driver/session/launch profile
pages/        Page Objects Android + android_locators.py
scripts/      doctor, Appium servers, reports
 tests/app/   onboarding, login, unlock, e2e, registro sem foto
```

## Configuração

Crie o arquivo local:

```bash
cp config/env.example.yaml config/env.yaml
```

Principais chaves Android:

```yaml
APP_SOURCE: "apk"              # apk | package
APP_PATH: "app/ifPontoCell.apk"
ANDROID_TARGET: "emulator"     # emulator | real
ANDROID_APP_PACKAGE: "br.com.ifractal.Stou"
ANDROID_APP_ACTIVITY: "br.com.ifractal.stou.view.MainActivity"
ANDROID_UDID: ""
```

Quando `APP_SOURCE=package`, o app deve estar previamente instalado e `APP_PATH` não é utilizado pela sessão.

## Ambiente

```bash
make setup
make doctor
```

O setup instala Appium no prefixo npm do usuário e garante o driver `uiautomator2`.

## Execução

```bash
make run
make smoke
make regression
make onboarding
make login
make unlock
make e2e
make registro-ponto
make jornada
make debug test=tests/app/test_login.py::test_credenciais_validas
```

`make set-simulator` foi preservado por compatibilidade com o fluxo do time e agora seleciona `ANDROID_TARGET=emulator`. `make set-real` seleciona device Android real.

## Locators Android

`pages/android_locators.py` centraliza a estratégia por `resource-id` com package opcional. Os IDs reaproveitados vieram do projeto Android de referência e não dependem do package completo.

Pendências de locators da build atual estão documentadas em `PENDENCIAS_LOCATORS_ANDROID.md`.

## Paralelo

`config/devices.yaml` usa a chave `emulators` e define `udid` + `appium_port`. `make appium-servers` sobe um Appium por entrada e, por design, não depende de `check-appium`.

## Reports

```bash
make report
make report-pdf
```

## Fluxo Git

Os comandos Git existentes no `Makefile` foram preservados.
