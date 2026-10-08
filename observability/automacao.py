"""
Configuração desta automação para o pacote ifponto-qa-report: pastas dos
testes com CT, ordem da suíte, nome dos fluxos no dashboard e o print
das evidências. O pacote importa este módulo sozinho (qa_report.automacao).
"""

from pathlib import Path

from qa_report.automacao import Automacao, configurar
from qa_report.casos_teste import suite_alfabetica, suite_do_makefile

from utils.file_utils import build_screenshot_path
from utils.logger import get_logger

RAIZ = Path(__file__).resolve().parent.parent

# Os logs do pacote saem no mesmo formato dos da automação.
get_logger("qa_report")


def ordem_da_suite(raiz: Path) -> list[Path]:
    """A ordem do make run: a APP_SUITE do Makefile e depois tests/api."""
    return suite_do_makefile(raiz) + suite_alfabetica(raiz, ("tests/api",))


def tirar_print(driver, caminho: str) -> bool:
    return driver.save_screenshot(caminho)


configurar(
    Automacao(
        raiz=RAIZ,
        pastas_com_ct=("tests/app", "tests/api"),
        ordem_da_suite=ordem_da_suite,
        tirar_print=tirar_print,
        caminho_do_print=build_screenshot_path,
        # Arquivo fora da lista usa o próprio nome (test_ferias.py ->
        # "ferias"): tela nova já ganha a sua linha no dashboard.
        fluxo_por_arquivo={
            "test_e2e": "jornada e2e",
            "test_registro_sem_foto": "registro de ponto",
            "test_ponto": "tela ponto",
            "test_status": "status das marcações",
            "test_registro_geo": "registro com geo delimitação",
            "test_informe_rendimentos": "informe de rendimentos",
            "test_estado_humor": "estado de humor",
            "test_ass_espelho": "assinatura do espelho",
            "test_sobre_aplicativo": "sobre o aplicativo",
            "test_dados_pessoais": "dados pessoais",
            "test_privacidade": "privacidade",
            "test_alterar_pin": "alterar pin",
            "test_alterar_senha_sistema": "alterar senha do sistema",
            "test_zerar_dados": "zerar dados",
        },
        fluxo_por_pasta={"api": "api", "unit": "unitários"},
    )
)
