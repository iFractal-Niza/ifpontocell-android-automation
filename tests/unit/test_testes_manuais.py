"""
Testes que continuam manuais: o observability/testes_manuais.yaml desta
automação (válido e sem CT dos automatizados) e o plugin do report, que
só leva os previstos para a página com a opção --testes-manuais. A
leitura e o dashboard são do pacote ifponto-qa-report (testados lá).
"""

from types import SimpleNamespace

import pytest
from qa_report import testes_manuais

from observability import execution_metrics, pytest_report
from observability.casos_teste import PROJECT_ROOT, ler_casos


def test_arquivo_do_projeto_e_valido_e_sem_ct_dos_automatizados():
    arquivo = testes_manuais.arquivo_da_automacao(PROJECT_ROOT)
    manuais = {teste["ct"] for teste in testes_manuais.carregar(arquivo)}
    automatizados = {caso.id for caso in ler_casos() if caso.id}

    assert manuais & automatizados == set()


@pytest.mark.parametrize("ligada", [True, False])
def test_plugin_so_leva_os_previstos_com_a_opcao(monkeypatch, ligada):
    previstos = [{"ct": "CT900", "descricao": "A", "fluxo": "B"}]
    recebidos = {}

    def injetar(prefix, postfix, stats, **_):
        recebidos.update(stats)

    monkeypatch.setattr(pytest_report, "injetar", injetar)
    monkeypatch.setattr(pytest_report, "coletar_contexto", lambda **_: [])
    monkeypatch.setattr(testes_manuais, "carregar", lambda arquivo: previstos)
    execution_metrics.reset_dashboard_stats()

    sessao = SimpleNamespace(
        config=SimpleNamespace(getoption=lambda nome, default=None: ligada)
    )
    pytest_report.pytest_html_results_summary([], [], [], session=sessao)

    assert recebidos["testes_manuais_previstos"] == (
        previstos if ligada else []
    )
