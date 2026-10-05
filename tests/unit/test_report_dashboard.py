"""
Status e taxa de sucesso do dashboard do report (utils.report_dashboard).
Teste pulado não conta como reprovação.
"""

import pytest

from utils.report_dashboard import (
    _build_demorados_html,
    _calculate_flow_metrics,
    _get_status_meta,
    build_dashboard_html,
    calcular_taxa_sucesso,
)


def _status(passed=0, failed=0, error=0, skipped=0, criticas=0) -> str:
    _, rotulo, _ = _get_status_meta(
        calcular_taxa_sucesso(passed, failed, error),
        total=passed + failed + error + skipped,
        failed=failed,
        error=error,
        skipped=skipped,
        criticas=criticas,
    )

    return rotulo


def test_taxa_ignora_os_pulados():
    assert calcular_taxa_sucesso(passed=15, failed=0, error=0) == 100.0


def test_taxa_considera_falhas_e_erros():
    assert calcular_taxa_sucesso(passed=8, failed=1, error=1) == 80.0


def test_taxa_sem_teste_executado_e_zero():
    assert calcular_taxa_sucesso(passed=0, failed=0, error=0) == 0.0


@pytest.mark.parametrize(
    ("resultados", "esperado"),
    [
        ({"passed": 18}, "APROVADO"),
        # Caso real: 15 aprovados e 3 pulados por massa saíam INSTÁVEL.
        ({"passed": 15, "skipped": 3}, "APROVADO COM RESSALVAS"),
        # Muitos pulados não viram CRÍTICO sem nenhuma falha.
        ({"passed": 6, "skipped": 12}, "APROVADO COM RESSALVAS"),
        ({"passed": 19, "failed": 1}, "INSTÁVEL"),
        ({"passed": 19, "failed": 1, "skipped": 5}, "INSTÁVEL"),
        ({"passed": 6, "failed": 4}, "CRÍTICO"),
        # Falha fora do smoke chama atenção, mas não é crítica.
        ({"passed": 19, "error": 1}, "INSTÁVEL"),
        ({"passed": 19, "failed": 1, "criticas": 1}, "CRÍTICO"),
        ({"passed": 19, "error": 1, "criticas": 1}, "CRÍTICO"),
        ({"skipped": 4}, "SEM EXECUÇÃO"),
        ({}, "SEM EXECUÇÃO"),
    ],
)
def test_status_da_execucao(resultados, esperado):
    assert _status(**resultados) == esperado


def test_fluxo_calcula_a_taxa_sobre_os_executados():
    metricas = _calculate_flow_metrics({"ok": 7, "skip": 3})

    assert metricas["total"] == 10
    assert metricas["executed"] == 7
    assert metricas["success_rate"] == 100.0


def test_dashboard_mostra_ressalvas_e_aprovados_sobre_executados():
    html = build_dashboard_html(
        {
            "total": 18,
            "passed": 15,
            "failed": 0,
            "error": 0,
            "skipped": 3,
            "success_rate": calcular_taxa_sucesso(15, 0, 0),
            "por_fluxo": {"holerite": {"ok": 7, "skip": 3}},
            "contexto": [("Ambiente", "homologacao"), ("App", "")],
            "pulados": [
                {
                    "nodeid": "tests/app/test_h.py::test_segundo",
                    "titulo": "Abre o segundo holerite",
                    "fluxo": "holerite",
                    "motivo": "um documento só <1>",
                }
            ],
        }
    )

    # Sem etiqueta de status (CRÍTICO, APROVADO...): só a cor do resumo.
    assert "APROVADO COM RESSALVAS" not in html
    assert 'class="qa-execution-alert caveat"' in html
    assert "15 de 15 executados" in html
    # O fluxo conta os pulados no total: 7 aprovados de 10 testes.
    assert "<strong>7/10</strong>" in html
    # Ressalvas: fluxo, título e motivo (escapado) de cada pulado.
    assert "Motivo dos testes pulados" in html
    assert "Abre o segundo holerite" in html
    assert "um documento só &lt;1&gt;" in html
    # Identificação: item sem valor não aparece.
    assert "homologacao" in html
    assert ">App<" not in html


def test_dashboard_sem_pulados_nao_tem_ressalvas():
    html = build_dashboard_html(
        {"total": 1, "passed": 1, "success_rate": 100.0, "pulados": []}
    )

    assert "Motivo dos testes pulados" not in html
    assert "qa-context" not in html


def test_classe_do_instavel_e_diferente_da_das_ressalvas():
    instavel, _, _ = _get_status_meta(95.0, total=20, failed=1)
    ressalvas, _, _ = _get_status_meta(100.0, total=20, skipped=2)

    assert (instavel, ressalvas) == ("unstable", "caveat")


def test_dashboard_tem_botao_de_tema_e_aplica_o_tema_salvo_antes():
    html = build_dashboard_html({"total": 1, "passed": 1, "success_rate": 100})

    assert 'data-qa-theme="light"' in html
    assert 'data-qa-theme="dark"' in html
    # O script do tema vem antes do dashboard, para não piscar o claro.
    assert html.index("qa-report-tema") < html.index('class="qa-dashboard"')


def test_dashboard_tem_botao_de_baixar_html():
    # O report.js liga o clique (ou troca por "Somente leitura" na cópia).
    html = build_dashboard_html({"total": 1, "passed": 1, "success_rate": 100})

    assert "data-qa-baixar" in html
    assert "Baixar HTML" in html


def test_dashboard_leva_os_totais_para_somar_os_testes_manuais():
    # O report.js soma testes manuais e melhorias a estes totais.
    import html as html_lib
    import json
    import re

    painel = build_dashboard_html(
        {"total": 3, "passed": 1, "failed": 1, "skipped": 1, "criticas": 1}
    )

    totais = json.loads(
        html_lib.unescape(re.search(r'data-qa-totais="([^"]+)"', painel)[1])
    )

    assert totais == {
        "total": 3,
        "passed": 1,
        "failed": 1,
        "error": 0,
        "skipped": 1,
        "criticas": 1,
        "saudavel": 90,
        "instavel": 70,
    }
    for chave in ("taxa", "total", "passou", "falhou", "erro", "pulados"):
        assert f'data-qa-kpi="{chave}"' in painel


def _duracoes(**segundos) -> dict:
    return {
        nome: {"titulo": f"Teste {nome}", "fluxo": "holerite", "segundos": s}
        for nome, s in segundos.items()
    }


def test_demorados_lista_os_cinco_mais_lentos_em_ordem():
    html = _build_demorados_html(
        _duracoes(a=3, b=200, c=0.2, d=45, e=10, f=7, g=1)
    )

    ordem = [html.index(f"Teste {nome}") for nome in "bdefa"]
    assert ordem == sorted(ordem)
    assert "Teste c" not in html and "Teste g" not in html
    assert "03:20" in html and "45s" in html


def test_demorados_com_um_teste_so_nao_aparece():
    assert _build_demorados_html(_duracoes(a=30)) == ""
    assert _build_demorados_html({}) == ""


def test_demorados_abaixo_de_um_segundo():
    html = _build_demorados_html(_duracoes(a=0.4, b=0.1))

    assert "&lt;1s" in html or "<1s" in html


def _cor_do_fluxo(**dados) -> str:
    """Classe de cor da barra do fluxo (a etiqueta de status saiu)."""
    import re

    from utils.report_dashboard import build_fluxo_html_card

    html = build_fluxo_html_card("privacidade", dados)

    assert "CRÍTICO" not in html and "FALHOU" not in html

    return re.search(r'class="qa-flow-progress (\w+)"', html)[1]


def test_fluxo_com_falha_fora_do_smoke_nao_e_critico():
    # Caso real: Privacidade (regression), 1 teste, falhou -> 0%.
    assert _cor_do_fluxo(fail=1) == "unstable"


def test_fluxo_com_falha_do_smoke_e_critico():
    assert _cor_do_fluxo(ok=1, fail=1, critico=1) == "failed"


@pytest.mark.parametrize(
    ("falhas", "erros", "esperado"),
    [
        (1, 0, "1 falha funcional detectada."),
        (2, 0, "2 falhas funcionais detectadas."),
        (0, 1, "1 erro técnico detectado."),
        (0, 3, "3 erros técnicos detectados."),
        (1, 1, "1 falha funcional e 1 erro técnico detectados."),
    ],
)
def test_resumo_concorda_com_falha_e_erro(falhas, erros, esperado):
    html = build_dashboard_html(
        {
            "total": 10,
            "passed": 10 - falhas - erros,
            "failed": falhas,
            "error": erros,
        }
    )

    assert esperado in html


def test_fluxo_leva_os_numeros_para_somar_os_testes_manuais():
    import html as html_lib
    import json
    import re

    from utils.report_dashboard import build_fluxo_html_card

    card = build_fluxo_html_card(
        "jornada e2e", {"ok": 2, "fail": 1, "skip": 1, "critico": 1}
    )
    dados = json.loads(
        html_lib.unescape(re.search(r'data-qa-fluxo="([^"]+)"', card)[1])
    )

    assert dados == {
        "nome": "jornada e2e",
        "ok": 2,
        "fail": 1,
        "error": 0,
        "skip": 1,
        "critico": 1,
    }


def test_sem_fluxo_a_lista_existe_para_os_testes_manuais():
    html = build_dashboard_html({"total": 0})

    assert "Nenhum fluxo foi identificado" in html
    assert 'class="qa-flow-list"' in html


def test_resumo_diz_se_algum_teste_do_smoke_falhou():
    sem = build_dashboard_html({"total": 20, "passed": 19, "failed": 1})
    com = build_dashboard_html(
        {"total": 20, "passed": 18, "failed": 2, "criticas": 2}
    )

    assert "Nenhum teste do smoke falhou." in sem
    assert "2 testes do smoke falharam." in com
