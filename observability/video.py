"""
Vídeo dos testes no report HTML (e salvo em reports/videos/). Cada teste
que usa o app é gravado do início ao fim da sua execução, e a opção
--video decide o que fica:

- falhas (padrão): guarda só o vídeo dos testes que falharam; o dos que
  passaram é descartado. É a "caixa-preta": o vídeo da falha sem
  precisar reproduzir, sem pesar o report quando tudo passa;
- todos (make <comando> VIDEO=1): guarda o vídeo de todos os testes;
- nao (make <comando> VIDEO=0): não grava nada.

Gravação pelo comando padrão do Appium (start_recording_screen), que no
UiAutomator2 usa o adb screenrecord do próprio device: não precisa de
ffmpeg. O screenrecord limita cada gravação a 3 minutos (teste mais
longo fica com o vídeo cortado no fim). Se não funcionar, o teste segue
sem vídeo e o log avisa.

O vídeo guardado é comprimido pelo ffmpeg do computador (720 px de
largura, 30 fps, H.264, sem áudio), que deixa o report bem mais leve que
a gravação na resolução do aparelho. Sem ffmpeg, ou se a compressão
falhar, fica o original.
"""

import base64
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

import pytest
from qa_observability import pastas
from qa_observability.relatorio import obter_sessao
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger("video")

OPCAO = "--video"
TODOS = "todos"
FALHAS = "falhas"
NAO = "nao"
MODOS = (FALHAS, TODOS, NAO)


def pasta_dos_videos() -> str:
    return os.path.join(pastas.reports_dir(), "videos")


# Marcado na primeira vez em que nenhum meio de gravação funciona: os
# testes seguintes da execução nem tentam.
GRAVACAO_INDISPONIVEL = pytest.StashKey[bool]()

# Atributo do item com o caminho do vídeo gravado (lido pelo plugin do
# report para anexar o vídeo na linha do teste).
ATRIBUTO_VIDEO = "caminho_do_video"


class Gravador:
    """Grava a tela do app durante um teste."""

    def __init__(self, driver):
        self.driver = driver
        self.gravando = False

    def iniciar(self) -> bool:
        try:
            self.driver.start_recording_screen()
        except WebDriverException as erro:
            logger.warning(
                "Não foi possível gravar o vídeo do teste pelo Appium "
                "(adb screenrecord). Os próximos testes seguem sem vídeo: "
                f"{erro.msg}"
            )
            return False

        self.gravando = True
        return True

    def parar(self) -> bytes | None:
        """O vídeo em bytes (mp4), ou None se não houver."""
        if not self.gravando:
            return None

        try:
            conteudo = self.driver.stop_recording_screen()
        except WebDriverException as erro:
            logger.warning(f"Não foi possível finalizar o vídeo: {erro.msg}")
            return None

        if not conteudo:
            return None

        try:
            return base64.b64decode(conteudo)
        except (ValueError, TypeError):
            return None


# === Compressão ===
LARGURA_MAXIMA = 720
FPS = 30
# Qualidade do H.264: maior = arquivo menor e imagem pior (18 a 28 é o
# usual; 28 ainda deixa os textos da tela legíveis).
CRF = 28
TEMPO_LIMITE_COMPRESSAO = 120


def comando_de_compressao(entrada: str, saida: str) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        entrada,
        # min(): não amplia um vídeo que já seja mais estreito.
        "-vf",
        f"scale='min({LARGURA_MAXIMA},iw)':-2",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-crf",
        str(CRF),
        "-preset",
        "medium",
        # Formato de cor que todo navegador toca.
        "-pix_fmt",
        "yuv420p",
        # Índice no começo do arquivo: o player começa sem ler tudo.
        "-movflags",
        "+faststart",
        "-an",
        saida,
    ]


def comprimir_video(video: bytes) -> bytes:
    """O vídeo comprimido, ou o original se não der ou não compensar."""
    if not shutil.which("ffmpeg"):
        logger.info("ffmpeg não encontrado: o vídeo fica sem compressão.")
        return video

    with tempfile.TemporaryDirectory() as pasta:
        entrada = os.path.join(pasta, "original.mp4")
        saida = os.path.join(pasta, "comprimido.mp4")

        with open(entrada, "wb") as arquivo:
            arquivo.write(video)

        try:
            subprocess.run(
                comando_de_compressao(entrada, saida),
                check=True,
                capture_output=True,
                timeout=TEMPO_LIMITE_COMPRESSAO,
            )
            with open(saida, "rb") as arquivo:
                comprimido = arquivo.read()
        except (OSError, subprocess.SubprocessError) as erro:
            stderr = getattr(erro, "stderr", None)
            detalhe = (
                stderr.decode(errors="replace").strip()
                if isinstance(stderr, bytes) and stderr
                else erro
            )
            logger.warning(f"Não foi possível comprimir o vídeo: {detalhe}")
            return video

    if not comprimido or len(comprimido) >= len(video):
        return video

    logger.info(
        f"Vídeo comprimido: {len(video) // 1024} KB -> "
        f"{len(comprimido) // 1024} KB"
    )
    return comprimido


def nome_do_video(item, agora: datetime) -> str:
    marker = item.get_closest_marker("ct")
    ct = str(marker.args[0]) if marker and marker.args else "SEM_CT"

    return f"{ct}_{item.name}_{agora:%Y-%m-%d_%H-%M-%S}.mp4"


def falhou(excinfo) -> bool:
    """
    True se a chamada do teste terminou em falha. Pulo (pytest.skip) e
    falha esperada (pytest.xfail) também chegam como exceção, mas não são
    falha.
    """
    if excinfo is None:
        return False

    return not isinstance(
        excinfo[1], (pytest.skip.Exception, pytest.xfail.Exception)
    )


def guardar_video(modo: str, excinfo) -> bool:
    return modo == TODOS or (modo == FALHAS and falhou(excinfo))


# === Plugin ===
def pytest_addoption(parser) -> None:
    parser.addoption(
        OPCAO,
        nargs="?",
        const=TODOS,
        default=FALHAS,
        choices=MODOS,
        help=(
            "vídeo dos testes no report: falhas (padrão, só dos que "
            "falharam), todos (--video sozinho) ou nao"
        ),
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    modo = item.config.getoption(OPCAO, default=FALHAS)

    if modo == NAO:
        yield
        return

    driver = obter_sessao(item)
    # Só um driver de verdade: os unitários usam drivers falsos (Mock), e
    # gravar neles mexeria nas chamadas que eles conferem.
    gravador = Gravador(driver) if isinstance(driver, WebDriver) else None
    gravando = False

    # Agora que grava por padrão, um ambiente sem gravação não pode
    # repetir o aviso (e a tentativa) em todo teste.
    if gravador and not item.config.stash.get(GRAVACAO_INDISPONIVEL, False):
        gravando = gravador.iniciar()

        if not gravando:
            item.config.stash[GRAVACAO_INDISPONIVEL] = True

    resultado = yield

    if not gravando:
        return

    # Para a gravação mesmo quando o vídeo vai ser descartado: senão ela
    # continuaria no teste seguinte.
    video = gravador.parar()

    if not video or not guardar_video(modo, resultado.excinfo):
        return

    video = comprimir_video(video)

    pasta = pasta_dos_videos()
    ensure_dir(pasta)
    caminho = os.path.join(pasta, nome_do_video(item, datetime.now()))

    with open(caminho, "wb") as arquivo:
        arquivo.write(video)

    setattr(item, ATRIBUTO_VIDEO, caminho)
    logger.info(f"Vídeo do teste salvo: {caminho}")
