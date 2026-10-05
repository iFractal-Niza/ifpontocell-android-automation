"""
Vídeo dos testes (observability.video): o gravador usa o Appium (adb
screenrecord); por padrão só o vídeo das falhas fica no report.
"""

import base64
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from selenium.common.exceptions import WebDriverException

from observability import pytest_report, video
from observability.video import Gravador, guardar_video, nome_do_video

VIDEO = b"\x00\x00\x00 ftypmp4-falso"
VIDEO_B64 = base64.b64encode(VIDEO).decode()


def test_grava_pelo_appium():
    driver = Mock()
    driver.stop_recording_screen.return_value = VIDEO_B64

    gravador = Gravador(driver)

    assert gravador.iniciar() is True
    assert gravador.parar() == VIDEO
    driver.start_recording_screen.assert_called_once()


def test_sem_gravacao_segue_sem_video():
    driver = Mock()
    driver.start_recording_screen.side_effect = WebDriverException(
        "screenrecord indisponível"
    )

    gravador = Gravador(driver)

    assert gravador.iniciar() is False
    assert gravador.parar() is None


def test_falha_ao_parar_nao_derruba_o_teste():
    driver = Mock()
    driver.stop_recording_screen.side_effect = WebDriverException("perdeu")

    gravador = Gravador(driver)
    gravador.iniciar()

    assert gravador.parar() is None
    driver.stop_recording_screen.assert_called_once()


def test_nome_do_video_leva_o_ct():
    item = SimpleNamespace(
        name="test_visualizar_holerite_mais_recente",
        get_closest_marker=lambda nome: SimpleNamespace(args=("CT014",)),
    )

    assert nome_do_video(item, datetime(2026, 10, 1, 9, 30, 5)) == (
        "CT014_test_visualizar_holerite_mais_recente_2026-10-01_09-30-05.mp4"
    )


def test_video_e_embutido_no_report_com_legenda(tmp_path):
    arquivo = tmp_path / "CT014.mp4"
    arquivo.write_bytes(VIDEO)
    report_extras = []

    assert pytest_report.anexar_video(report_extras, str(arquivo))
    assert report_extras[0]["format_type"] == "video"
    assert report_extras[0]["content"] == VIDEO_B64
    assert report_extras[0]["name"] == "Vídeo do teste"


def _excinfo(erro: BaseException):
    try:
        raise erro
    except BaseException:
        return sys.exc_info()


@pytest.mark.parametrize(
    ("modo", "excinfo", "guarda"),
    [
        (video.FALHAS, None, False),
        (video.FALHAS, _excinfo(AssertionError("quebrou")), True),
        (video.FALHAS, _excinfo(pytest.skip.Exception("sem massa")), False),
        (video.FALHAS, _excinfo(pytest.xfail.Exception("esperada")), False),
        (video.TODOS, None, True),
        (video.NAO, _excinfo(AssertionError("quebrou")), False),
    ],
    ids=[
        "falhas-passou",
        "falhas-falhou",
        "falhas-pulou",
        "falhas-xfail",
        "todos-passou",
        "nao-falhou",
    ],
)
def test_qual_video_fica(modo, excinfo, guarda):
    assert guardar_video(modo, excinfo) is guarda


def test_opcao_padrao_e_so_das_falhas(pytestconfig):
    assert pytestconfig.getoption(video.OPCAO) in video.MODOS


# === Compressão pelo ffmpeg ===
def _ffmpeg_que_grava(conteudo: bytes):
    def run(comando, **kwargs):
        with open(comando[-1], "wb") as saida:
            saida.write(conteudo)

    return run


def test_comprime_quando_o_resultado_e_menor(monkeypatch):
    original = b"x" * 1000
    monkeypatch.setattr(video.shutil, "which", lambda nome: "/bin/ffmpeg")
    monkeypatch.setattr(video.subprocess, "run", _ffmpeg_que_grava(b"menor"))

    assert video.comprimir_video(original) == b"menor"


def test_mantem_o_original_se_a_compressao_nao_compensa(monkeypatch):
    monkeypatch.setattr(video.shutil, "which", lambda nome: "/bin/ffmpeg")
    monkeypatch.setattr(
        video.subprocess, "run", _ffmpeg_que_grava(b"maior" * 10)
    )

    assert video.comprimir_video(b"curto") == b"curto"


def test_sem_ffmpeg_mantem_o_original(monkeypatch):
    monkeypatch.setattr(video.shutil, "which", lambda nome: None)
    run = Mock()
    monkeypatch.setattr(video.subprocess, "run", run)

    assert video.comprimir_video(VIDEO) == VIDEO
    run.assert_not_called()


@pytest.mark.parametrize(
    "erro",
    [
        video.subprocess.CalledProcessError(1, "ffmpeg", stderr=b"quebrou"),
        video.subprocess.TimeoutExpired("ffmpeg", 120),
    ],
)
def test_falha_do_ffmpeg_mantem_o_original(monkeypatch, erro):
    monkeypatch.setattr(video.shutil, "which", lambda nome: "/bin/ffmpeg")
    monkeypatch.setattr(video.subprocess, "run", Mock(side_effect=erro))

    assert video.comprimir_video(VIDEO) == VIDEO


def test_comando_reduz_para_720_sem_ampliar():
    comando = video.comando_de_compressao("in.mp4", "out.mp4")

    assert comando[comando.index("-vf") + 1] == "scale='min(720,iw)':-2"
    assert "-an" in comando
    assert comando[-1] == "out.mp4"
