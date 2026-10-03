# Reset de ambiente Android

## Diagnóstico primeiro

```bash
make doctor
adb devices
appium driver list --installed
```

## Recriar venv

```bash
rm -rf venv
make install
```

## Reinstalar Appium/UiAutomator2

```bash
make install-appium
```

## Validar device/emulador

```bash
adb devices
adb -s <UDID> shell getprop ro.build.version.release
```

## Resetar app sem apagar o emulador

```bash
adb -s <UDID> shell am force-stop br.com.ifractal.Stou
adb -s <UDID> shell pm clear br.com.ifractal.Stou
```

Use `pm clear` apenas quando o cenário exigir estado totalmente limpo.

## Execução

```bash
make doctor
appium
make smoke
```
