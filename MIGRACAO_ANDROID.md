# Migração iOS → Android

## Alterado

- `XCUITestOptions` → `UiAutomator2Options`;
- capabilities iOS → `appPackage`, `appActivity`, `udid`, APK/package e opções UiAutomator2;
- ciclo de vida `.app`/bundleId/simctl → APK/appPackage/ADB/Appium;
- permissões de Simulator → `autoGrantPermissions` + Permission Controller Android;
- locators iOS → `resource-id` Android via `pages/android_locators.py`;
- PIN → teclado `numberN`;
- Home/menu/registro → IDs Android do projeto de referência;
- menu lateral/perfil → IDs Android existentes;
- registro sem foto → fluxo Android real até `btn_confirmar_sem_foto`;
- `Makefile`/doctor/setup → UiAutomator2 e Android SDK;
- relatório → título Android.

## Preservado

- Pytest + Page Object;
- testes e intenção dos cenários;
- integração com API de celular;
- compartilhamento de sessão E2E → registro;
- markers;
- relatórios HTML/PDF;
- comandos Git do `Makefile`;
- `make set-simulator` por compatibilidade, agora selecionando `ANDROID_TARGET=emulator`;
- `make set-real` para device físico Android.

## Antes da execução real

1. criar `config/env.yaml` a partir de `config/env.example.yaml`;
2. informar credenciais/API;
3. adicionar `app/ifPontoCell.apk` ou usar `APP_SOURCE=package`;
4. confirmar os locators Prioridade 1 em `PENDENCIAS_LOCATORS_ANDROID.md`;
5. validar `adb devices`;
6. executar `make doctor`;
7. subir Appium e rodar a suíte desejada.
