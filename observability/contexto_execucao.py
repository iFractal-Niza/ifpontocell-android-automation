"""
Identificação da execução exibida no cabeçalho do dashboard: quando
rodou, quanto durou, em qual ambiente, em qual dispositivo e qual versão
do app. Sem isso, um report enviado a alguém não diz o que foi
testado nem onde.

Nada aqui pode derrubar a geração do report: o que não puder ser lido é
omitido.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from config.settings import ConfiguracaoInvalida, Settings

AMBIENTE_PADRAO = "local"


def formatar_duracao(segundos: float) -> str:
    total = max(0, round(segundos))
    horas, resto = divmod(total, 3600)
    minutos, segundos_restantes = divmod(resto, 60)

    return f"{horas:02d}:{minutos:02d}:{segundos_restantes:02d}"


def _localizar_aapt() -> str | None:
    """
    aapt do Android SDK: no PATH ou no build-tools mais recente do
    ANDROID_HOME/ANDROID_SDK_ROOT. None se não houver.
    """
    no_path = shutil.which("aapt")

    if no_path:
        return no_path

    for variavel in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        sdk = os.environ.get(variavel, "").strip()

        if not sdk:
            continue

        candidatos = sorted(Path(sdk).glob("build-tools/*/aapt"))

        if candidatos:
            return str(candidatos[-1])

    return None


def _ler_badging(apk_path: Path) -> str:
    """Saída do 'aapt dump badging' do APK, ou vazio."""
    aapt = _localizar_aapt()

    if not aapt or not apk_path.is_file():
        return ""

    try:
        resultado = subprocess.run(
            [aapt, "dump", "badging", str(apk_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""

    return resultado.stdout if resultado.returncode == 0 else ""


def _campo_badging(badging: str, campo: str) -> str:
    achado = re.search(rf"{campo}='([^']*)'", badging)

    return achado.group(1).strip() if achado else ""


def ler_versao_curta_app(apk_path: Path) -> str:
    """
    Só a versão do APK ("2.4.1", sem o build), como o app a exibe na
    tela Sobre o aplicativo. Vazio se não puder ser lida.
    """
    return _campo_badging(_ler_badging(apk_path), "versionName")


def ler_versao_app(apk_path: Path) -> str:
    """
    Versão do APK (APP_SOURCE=apk), lida pelo aapt: "2.4.1 (87)"
    (versionName e versionCode). Vazio sem aapt ou sem APK local.
    """
    badging = _ler_badging(apk_path)

    return _formatar_versao(
        _campo_badging(badging, "versionName"),
        _campo_badging(badging, "versionCode"),
    )


def _formatar_versao(versao: str, build: str) -> str:
    if versao and build and build != versao:
        return f"{versao} ({build})"

    return versao or build


def versao_do_dumpsys(saida: str) -> str:
    """'versionName=2.4.1' e 'versionCode=87 ...' -> "2.4.1 (87)"."""
    nome = re.search(r"versionName=(\S+)", saida)
    codigo = re.search(r"versionCode=(\d+)", saida)

    return _formatar_versao(
        nome.group(1) if nome else "", codigo.group(1) if codigo else ""
    )


def ler_versao_instalada(app_package: str, udid: str = "") -> str:
    """
    Versão do app instalado no device (APP_SOURCE=package), pelo
    'adb shell dumpsys package'. Vazio sem adb ou sem device.
    """
    comando = ["adb"] + (["-s", udid] if udid else [])
    comando += ["shell", "dumpsys", "package", app_package]

    try:
        resultado = subprocess.run(
            comando, capture_output=True, text=True, check=False, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""

    if resultado.returncode != 0:
        return ""

    return versao_do_dumpsys(resultado.stdout)


def descrever_dispositivo(settings: Settings) -> str:
    """Ex.: "Pixel 7 · Android 14 (emulador)"."""
    nome = settings.device.device_name
    versao = settings.device.platform_version
    tipo = "emulador" if settings.is_emulator else "device físico"

    partes = [nome, f"Android {versao}" if versao else ""]
    descricao = " · ".join(parte for parte in partes if parte)

    return f"{descricao} ({tipo})" if descricao else tipo.capitalize()


def coletar_contexto(
    inicio: datetime,
    fim: datetime,
    usa_app: bool,
    env: Mapping[str, str] | None = None,
) -> list[tuple[str, str]]:
    """
    Pares (rótulo, valor) na ordem de exibição.

    'usa_app' é False quando só rodaram testes sem app (API, unitários):
    dispositivo e versão do app não entram, pois não foram usados.
    """
    env = os.environ if env is None else env

    contexto = [
        ("Data", inicio.strftime("%d/%m/%Y %H:%M")),
        ("Duração", formatar_duracao((fim - inicio).total_seconds())),
        ("Ambiente", str(env.get("ENV", "")).strip() or AMBIENTE_PADRAO),
    ]

    if not usa_app:
        return contexto

    try:
        settings = Settings.from_env(env)
    except ConfiguracaoInvalida:
        return contexto

    contexto.append(("Dispositivo", descrever_dispositivo(settings)))

    versao_app = (
        ler_versao_app(settings.apk_path)
        if settings.app_source == "apk"
        else ler_versao_instalada(settings.app.package, settings.device.udid)
    )

    if versao_app:
        contexto.append(("App", versao_app))

    return contexto
