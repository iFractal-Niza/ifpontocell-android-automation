"""
O que o report anexa nesta automação, pelo driver do Appium: o print e a
árvore da tela na falha e o vídeo do teste. O resto do report (métricas,
erro resumido, evidências, página) é o plugin qa_observability.relatorio, do
pacote ifponto-observability, que chama estas funções pela configuração
(observability.automacao).
"""

import base64

from pytest_html import extras
from qa_observability import pastas
from qa_observability.relatorio import anexar_imagem, obter_sessao

from observability.video import ATRIBUTO_VIDEO
from utils.file_utils import build_screenshot_path
from utils.logger import get_logger

logger = get_logger("anexos")

# Fixtures com o driver, em ordem de preferência (qualquer outra fixture
# com driver também serve: qa_observability.relatorio.obter_sessao).
FIXTURES_DO_DRIVER = (
    "driver",
    "driver_e2e",
    "driver_registro_ponto",
    "home_para_marcacao",
)

LEGENDA_PRINT_FALHA = "Print da falha"
LEGENDA_VIDEO = "Vídeo do teste"
LEGENDA_ARVORE = "Árvore da tela"


def driver_de(valor):
    """
    O driver contido em um valor de fixture: o próprio driver, ou o
    .driver de uma Page/AppSession. None se não houver.
    """
    if hasattr(valor, "save_screenshot"):
        return valor

    driver_interno = getattr(valor, "driver", None)

    if hasattr(driver_interno, "save_screenshot"):
        return driver_interno

    return None


def na_falha(item, report, report_extras: list) -> None:
    """Print e árvore da tela no momento da falha."""
    driver = obter_sessao(item)

    if driver is None:
        logger.warning(
            "Nenhum driver ativo foi encontrado para capturar o screenshot",
            extra={
                "event": "report_driver_not_found",
                "test_name": item.name,
                "when": report.when,
                "available_funcargs": list(item.funcargs.keys()),
            },
        )
        return

    anexar_print_da_falha(report_extras, driver, item.name, report.when)
    anexar_arvore_da_tela(report_extras, driver, item.name)


def na_etapa(item, report, report_extras: list) -> None:
    """Vídeo do teste (opção --video), gravado durante a chamada."""
    caminho_video = getattr(item, ATRIBUTO_VIDEO, None)

    if report.when == "call" and caminho_video:
        anexar_video(report_extras, caminho_video)


def anexar_print_da_falha(
    report_extras: list, driver, nome_teste: str, etapa: str
) -> bool:
    try:
        caminho = build_screenshot_path(pastas.screenshots_dir(), nome_teste)
        salvo = driver.save_screenshot(caminho)
    except Exception:
        logger.exception(
            "Não foi possível salvar o screenshot no relatório",
            extra={
                "event": "report_screenshot_failed",
                "test_name": nome_teste,
                "when": etapa,
            },
        )
        return False

    if salvo and anexar_imagem(report_extras, caminho, LEGENDA_PRINT_FALHA):
        logger.info(
            "Screenshot anexado ao relatório",
            extra={
                "event": "report_screenshot_attached",
                "test_name": nome_teste,
                "screenshot_path": caminho,
                "when": etapa,
            },
        )
        return True

    logger.warning(
        "O driver não retornou um screenshot válido",
        extra={
            "event": "report_screenshot_not_saved",
            "test_name": nome_teste,
            "when": etapa,
            "screenshot_path": caminho,
        },
    )
    return False


def anexar_arvore_da_tela(
    report_extras: list, driver, nome_teste: str
) -> bool:
    """
    Anexa a árvore de acessibilidade da tela no momento da falha (o mesmo
    XML do Appium Inspector), para investigar locator sem reproduzir a
    falha. Salva também o .xml ao lado dos prints. False se o driver não
    devolver a árvore (ex.: sessão perdida).
    """
    try:
        arvore = driver.page_source
    except Exception:
        logger.warning(
            "Não foi possível capturar a árvore da tela na falha",
            extra={
                "event": "report_page_source_failed",
                "test_name": nome_teste,
            },
        )
        return False

    if not arvore:
        return False

    caminho = build_screenshot_path(
        pastas.screenshots_dir(), nome_teste
    ).rsplit(".", 1)[0]
    caminho = f"{caminho}_arvore.xml"

    try:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(arvore)
    except OSError:
        pass

    report_extras.append(extras.text(arvore, name=LEGENDA_ARVORE))

    return True


def anexar_video(report_extras: list, caminho: str) -> bool:
    """
    Anexa o vídeo do teste ao report, embutido (base64), como as
    imagens. False se não houver arquivo.
    """
    try:
        with open(caminho, "rb") as arquivo:
            conteudo = base64.b64encode(arquivo.read()).decode("ascii")
    except OSError:
        return False

    report_extras.append(extras.video(conteudo, name=LEGENDA_VIDEO))

    return True
