"""
Testes que continuam manuais (observability.testes_manuais): a leitura do
testes_manuais.yaml e a garantia de que o arquivo do projeto é válido e
não reaproveita CT dos testes automatizados.
"""

import pytest

from observability import testes_manuais
from observability.casos_teste import ler_casos
from utils.report_dashboard import build_dashboard_html


def _arquivo(tmp_path, conteudo: str):
    arquivo = tmp_path / "testes_manuais.yaml"
    arquivo.write_text(conteudo, encoding="utf-8")
    return arquivo


def test_le_ct_descricao_e_fluxo(tmp_path):
    arquivo = _arquivo(
        tmp_path,
        "- ct: CT900\n"
        "  descricao: ' Exporta o espelho em PDF '\n"
        "  fluxo: Espelho de ponto\n",
    )

    assert testes_manuais.carregar(arquivo) == [
        {
            "ct": "CT900",
            "descricao": "Exporta o espelho em PDF",
            "fluxo": "Espelho de ponto",
        }
    ]


def test_sem_arquivo_ou_lista_vazia_nao_ha_testes(tmp_path):
    assert testes_manuais.carregar(tmp_path / "nao_existe.yaml") == []
    assert testes_manuais.carregar(_arquivo(tmp_path, "[]\n")) == []


@pytest.mark.parametrize(
    ("conteudo", "trecho"),
    [
        ("ct: CT900\n", "lista"),
        ("- CT900\n", "não é um teste"),
        ("- ct: 900\n  descricao: x\n  fluxo: y\n", "formato"),
        ("- ct: CT900\n  fluxo: y\n", "descricao"),
        ("- ct: CT900\n  descricao: x\n", "fluxo"),
        (
            "- {ct: CT900, descricao: x, fluxo: y}\n"
            "- {ct: CT900, descricao: z, fluxo: y}\n",
            "repetido",
        ),
    ],
)
def test_item_fora_do_formato_e_recusado(tmp_path, conteudo, trecho):
    with pytest.raises(testes_manuais.ListaInvalida, match=trecho):
        testes_manuais.carregar(_arquivo(tmp_path, conteudo))


def test_arquivo_do_projeto_e_valido_e_sem_ct_dos_automatizados():
    manuais = {teste["ct"] for teste in testes_manuais.carregar()}
    automatizados = {caso.id for caso in ler_casos() if caso.id}

    assert manuais & automatizados == set()


def test_dashboard_leva_os_previstos_para_o_report():
    import html as html_lib
    import json
    import re

    previstos = [{"ct": "CT900", "descricao": "A <b>", "fluxo": "Espelho"}]
    painel = build_dashboard_html({"testes_manuais_previstos": previstos})
    atributo = re.search(r'data-qa-previstos="([^"]+)"', painel)[1]

    assert json.loads(html_lib.unescape(atributo)) == previstos
    assert "data-qa-previstos" not in build_dashboard_html({})


@pytest.mark.parametrize("ligada", [True, False])
def test_plugin_so_leva_os_previstos_com_a_opcao(monkeypatch, ligada):
    from types import SimpleNamespace

    from observability import execution_metrics, pytest_report

    previstos = [{"ct": "CT900", "descricao": "A", "fluxo": "B"}]
    recebidos = {}

    def montar(raiz, stats):
        recebidos.update(stats)
        return "", ""

    monkeypatch.setattr(pytest_report, "build_results_summary_html", montar)
    monkeypatch.setattr(pytest_report, "coletar_contexto", lambda **_: [])
    monkeypatch.setattr(testes_manuais, "carregar", lambda: previstos)
    execution_metrics.reset_dashboard_stats()

    sessao = SimpleNamespace(
        config=SimpleNamespace(getoption=lambda nome, default=None: ligada)
    )
    pytest_report.pytest_html_results_summary([], [], [], session=sessao)

    assert recebidos["testes_manuais_previstos"] == (
        previstos if ligada else []
    )
