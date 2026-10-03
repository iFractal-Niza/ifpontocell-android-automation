"""
Identificação da execução no cabeçalho do dashboard
(observability.contexto_execucao).

A versão do app vem do 'aapt dump badging' do APK; aqui a saída do aapt
é simulada, sem depender do Android SDK.
"""

from datetime import datetime

import pytest

from observability import contexto_execucao
from observability.contexto_execucao import (
    coletar_contexto,
    formatar_duracao,
    ler_versao_app,
    ler_versao_curta_app,
)

INICIO = datetime(2026, 9, 30, 10, 32, 51)
FIM = datetime(2026, 9, 30, 10, 42, 3)


def _badging(nome: str = "", codigo: str = "") -> str:
    return (
        "package: name='br.com.ifractal.Stou' "
        f"versionCode='{codigo}' versionName='{nome}' "
        "platformBuildVersionName='14'\n"
    )


@pytest.fixture
def aapt(monkeypatch):
    """Define a saída do aapt para o próximo APK lido."""

    def definir(saida: str) -> None:
        monkeypatch.setattr(
            contexto_execucao, "_ler_badging", lambda _apk: saida
        )

    return definir


def test_duracao_em_horas_minutos_e_segundos():
    assert formatar_duracao(552) == "00:09:12"
    assert formatar_duracao(3725.4) == "01:02:05"


def test_versao_e_build_do_app(aapt, tmp_path):
    aapt(_badging("2.4.1", "87"))

    assert ler_versao_app(tmp_path / "ifPontoCell.apk") == "2.4.1 (87)"


def test_build_igual_a_versao_nao_repete(aapt, tmp_path):
    aapt(_badging("2.4.1", "2.4.1"))

    assert ler_versao_app(tmp_path / "ifPontoCell.apk") == "2.4.1"


def test_apk_ausente_nao_tem_versao(tmp_path):
    assert ler_versao_app(tmp_path / "nao_existe.apk") == ""


def test_sem_aapt_nao_tem_versao(aapt, tmp_path):
    aapt("")

    assert ler_versao_app(tmp_path / "ifPontoCell.apk") == ""


def test_contexto_de_execucao_com_app(aapt, tmp_path):
    aapt(_badging("2.4.1"))

    contexto = coletar_contexto(
        INICIO,
        FIM,
        usa_app=True,
        env={
            "ENV": "homologacao",
            "APP_SOURCE": "apk",
            "APP_PATH": str(tmp_path / "ifPontoCell.apk"),
            "ANDROID_DEVICE_NAME": "Pixel 7",
            "ANDROID_PLATFORM_VERSION": "14",
        },
    )

    assert contexto == [
        ("Data", "30/09/2026 10:32"),
        ("Duração", "00:09:12"),
        ("Ambiente", "homologacao"),
        ("Dispositivo", "Pixel 7 · Android 14 (emulador)"),
        ("App", "2.4.1"),
    ]


def test_celular_aparece_como_device_fisico(monkeypatch):
    monkeypatch.setattr(
        contexto_execucao, "ler_versao_instalada", lambda *_: ""
    )

    contexto = dict(
        coletar_contexto(
            INICIO,
            FIM,
            usa_app=True,
            env={
                "ANDROID_TARGET": "real",
                "ANDROID_UDID": "R58N12ABCDE",
                "APP_SOURCE": "package",
                "ANDROID_DEVICE_NAME": "Galaxy A54",
            },
        )
    )

    assert contexto["Dispositivo"] == "Galaxy A54 (device físico)"
    assert "App" not in contexto


def test_app_instalado_mostra_a_versao_do_device(monkeypatch):
    # APP_SOURCE=package (padrão): a versão vem do app instalado.
    chamadas = []

    def instalada(pacote, udid):
        chamadas.append((pacote, udid))
        return "2.4.1 (87)"

    monkeypatch.setattr(contexto_execucao, "ler_versao_instalada", instalada)

    contexto = dict(
        coletar_contexto(
            INICIO, FIM, usa_app=True, env={"ANDROID_UDID": "emulator-5554"}
        )
    )

    assert contexto["App"] == "2.4.1 (87)"
    assert chamadas == [("br.com.ifractal.Stou", "emulator-5554")]


def test_versao_lida_do_dumpsys():
    saida = (
        "Packages:\n"
        "  Package [br.com.ifractal.Stou] (abc):\n"
        "    versionCode=87 minSdk=24 targetSdk=34\n"
        "    versionName=2.4.1\n"
    )

    assert contexto_execucao.versao_do_dumpsys(saida) == "2.4.1 (87)"
    assert contexto_execucao.versao_do_dumpsys("") == ""


def test_execucao_sem_app_omite_dispositivo_e_versao():
    contexto = coletar_contexto(INICIO, FIM, usa_app=False, env={})

    assert [rotulo for rotulo, _ in contexto] == [
        "Data",
        "Duração",
        "Ambiente",
    ]
    assert contexto[2] == ("Ambiente", "local")


def test_configuracao_invalida_nao_derruba_o_report():
    contexto = coletar_contexto(
        INICIO,
        FIM,
        usa_app=True,
        env={"ANDROID_TARGET": "ios"},
    )

    assert [rotulo for rotulo, _ in contexto] == [
        "Data",
        "Duração",
        "Ambiente",
    ]


def test_versao_curta_nao_leva_o_build(aapt, tmp_path):
    aapt(_badging("2.7.3", "3"))

    assert ler_versao_curta_app(tmp_path / "ifPontoCell.apk") == "2.7.3"
