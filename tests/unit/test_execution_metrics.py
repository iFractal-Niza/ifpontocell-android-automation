"""
Configuração desta automação para as métricas (observability.automacao):
o fluxo de cada arquivo no dashboard e o que conta como uso do app. As
métricas em si são do pacote ifponto-observability (testadas lá).
"""

import pytest
from qa_observability import execution_metrics
from qa_observability.execution_metrics import extract_fluxo


@pytest.fixture(autouse=True)
def metricas_isoladas():
    execution_metrics.reset_dashboard_stats()
    yield
    execution_metrics.reset_dashboard_stats()


@pytest.mark.parametrize(
    ("nodeid", "fluxo"),
    [
        ("tests/app/test_login.py::test_senha_invalida", "login"),
        ("tests/app/test_ass_espelho.py::test_x", "assinatura do espelho"),
        ("tests/app/test_registro_sem_foto.py::test_x", "registro de ponto"),
        # O nome do teste não decide: "home" aqui é da jornada e2e.
        (
            "tests/app/test_e2e.py::test_primeiro_acesso_home_e_lembrete",
            "jornada e2e",
        ),
        ("tests/api/test_celular_api.py::test_x", "api"),
        ("tests/unit/test_periodo.py::test_x", "unitários"),
        # Tela nova, fora do mapa: ganha a própria linha.
        ("tests/app/test_espelho_ponto.py::test_x", "espelho ponto"),
    ],
)
def test_fluxo_vem_do_arquivo(nodeid, fluxo):
    assert extract_fluxo(nodeid) == fluxo


def test_execucao_so_de_api_nao_usa_o_app():
    execution_metrics.update_dashboard_stats(
        "tests/api/test_a.py::t", "passed"
    )

    assert execution_metrics.execucao_usa_o_sistema() is False


def test_execucao_com_teste_de_tela_usa_o_app():
    execution_metrics.update_dashboard_stats(
        "tests/api/test_a.py::t", "passed"
    )
    execution_metrics.update_dashboard_stats(
        "tests/app/test_login.py::t", "passed"
    )

    assert execution_metrics.execucao_usa_o_sistema() is True
