"""
Configuração desta automação para o pacote ifponto-observability: pastas dos
testes com CT, ordem da suíte, nome dos fluxos no dashboard, o print
das evidências e o que o report anexa (observability.anexos). O pacote
importa este módulo sozinho (qa_observability.automacao).
"""

from datetime import datetime
from pathlib import Path

from qa_observability import execution_metrics
from qa_observability.automacao import Automacao, configurar
from qa_observability.casos_teste import suite_alfabetica, suite_do_makefile

from observability import anexos
from observability.contexto_execucao import coletar_contexto
from utils.file_utils import build_screenshot_path
from utils.logger import get_logger

RAIZ = Path(__file__).resolve().parent.parent

# Os logs do pacote saem no mesmo formato dos da automação.
get_logger("qa_observability")


def ordem_da_suite(raiz: Path) -> list[Path]:
    """A ordem do make run: a APP_SUITE do Makefile e depois tests/api."""
    return suite_do_makefile(raiz) + suite_alfabetica(raiz, ("tests/api",))


def tirar_print(driver, caminho: str) -> bool:
    return driver.save_screenshot(caminho)


def contexto(inicio: datetime, fim: datetime) -> list[tuple[str, str]]:
    """Identificação da execução (aparelho e versão só se usou o app)."""
    return coletar_contexto(
        inicio=inicio,
        fim=fim,
        usa_app=execution_metrics.execucao_usa_o_sistema(),
    )


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
        titulo="Android Automation",
        nota_preparacao=(
            "O tempo inclui a preparação de cada teste (ex.: abrir o app "
            "ou refazer o primeiro acesso)."
        ),
        sessao_de=anexos.driver_de,
        fixtures_da_sessao=anexos.FIXTURES_DO_DRIVER,
        na_falha=anexos.na_falha,
        na_etapa=anexos.na_etapa,
        contexto=contexto,
    )
)
