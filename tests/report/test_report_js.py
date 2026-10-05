"""
O que o report.js faz na página do report: tabela, classificação, testes
manuais, totais e fluxos recalculados, blocos de cards e a cópia do
"Baixar HTML". Totais e fluxos são conferidos contra o Python
(utils/report_dashboard.py), que o report.js repete.
"""

import base64

import pytest

from tests.report.conftest import _PNG, STATS_PADRAO
from utils.report_dashboard import (
    build_dashboard_html,
    build_fluxo_html_card,
    calcular_taxa_sucesso,
)

# O que o dashboard mostra (para comparar com o gerado pelo Python).
_LER_DASHBOARD = """() => ({
  resumo: document.querySelector('.qa-execution-alert-content strong')
    .textContent.trim(),
  cor: document.querySelector('.qa-execution-alert').className,
  cards: [...document.querySelectorAll('.qa-kpi-grid [data-qa-kpi]')]
    .filter(c => ['taxa', 'total', 'passou', 'falhou', 'erro', 'pulados']
      .includes(c.dataset.qaKpi))
    .map(c => c.dataset.qaKpi + '=' +
      c.querySelector('.qa-kpi-value').textContent.trim() +
      (c.classList.contains('muted') ? '(m)' : '') +
      ' ' + c.className.replace(/\\s+/g, ' ').trim())
})"""

_LER_FLUXO = """c => ({
  titulo: c.querySelector('.qa-flow-title').textContent.trim(),
  resumo: c.querySelector('.qa-flow-summary strong').textContent.trim(),
  numeros: [...c.querySelectorAll('.qa-flow-meta-item')]
    .filter(x => !/Dura/.test(x.textContent))
    .map(x => x.querySelector('strong').textContent.trim()),
  cor: c.querySelector('.qa-flow-progress').className,
  largura: c.querySelector('.qa-flow-progress').style.width.replace(' ', ''),
})"""


def _valor(pagina, seletor):
    return pagina.page.locator(seletor).input_value()


# === Tabela dos automatizados ===
def test_colunas_status_traduzido_e_blocos(abrir, report_padrao):
    pagina = abrir(report_padrao).page

    assert pagina.eval_on_selector_all(
        "#results-table-head th", "e => e.map(x => x.textContent.trim())"
    ) == [
        "Teste",
        "Status",
        "Categoria do erro",
        "Tipo de erro",
        "Status apont.",
        "Duração",
        "Evidências",
    ]
    assert sorted(
        pagina.locator("tr.collapsible td.col-result").all_inner_texts()
    ) == ["Falhou", "Passou"]
    assert pagina.locator(".qa-bloco-titulo").all_inner_texts() == [
        "Testes automatizados (2)",
        "Testes manuais (0)",
        "Melhorias (0)",
    ]


def test_clique_em_qualquer_ponto_da_linha_expande(abrir, report_padrao):
    pagina = abrir(report_padrao).page
    linha = pagina.locator("tbody.results-table-row", has_text="test_falha")
    fechada = (
        "e => e.querySelector('.col-result').classList.contains('collapsed')"
    )

    antes = linha.evaluate(fechada)
    linha.locator(".col-duration").click()

    assert linha.evaluate(fechada) != antes


def test_classificacao_e_salva_e_volta_ao_ordenar_e_recarregar(
    abrir, report_padrao
):
    pagina = abrir(report_padrao)
    categoria = "#results-table select[data-campo=categoria]"

    pagina.page.locator(categoria).select_option("Crítico")
    pagina.page.click("th[data-column-type=testId]")
    assert _valor(pagina, categoria) == "Crítico"

    pagina.recarregar()
    assert _valor(pagina, categoria) == "Crítico"
    # A cor da categoria acompanha o valor.
    assert pagina.page.locator(categoria).get_attribute("data-valor") == (
        "Crítico"
    )


# === Totais e fluxos: iguais ao Python ===
def _stats_com(manuais_passou=0, manuais_falhou=0, manuais_pulado=0):
    base = STATS_PADRAO
    passed = base["passed"] + manuais_passou
    failed = base["failed"] + manuais_falhou
    skipped = base["skipped"] + manuais_pulado

    return {
        "total": passed + failed + skipped,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "success_rate": calcular_taxa_sucesso(passed, failed, 0),
    }


@pytest.mark.parametrize(
    ("status", "esperado"),
    [
        ([], {}),
        (["Passou", "Passou"], {"manuais_passou": 2}),
        (
            ["Corrigido", "Não corrigido"],
            {"manuais_passou": 1, "manuais_falhou": 1},
        ),
        (["Pulado"], {"manuais_pulado": 1}),
        (["Falhou"] * 5, {"manuais_falhou": 5}),
    ],
)
def test_totais_com_testes_manuais_iguais_ao_python(
    abrir, navegador, report_padrao, status, esperado
):
    pagina = abrir(report_padrao)

    for valor in status:
        pagina.adicionar(status=valor)

    referencia = navegador.new_page()
    referencia.set_content(build_dashboard_html(_stats_com(**esperado)))

    assert pagina.page.evaluate(_LER_DASHBOARD) == referencia.evaluate(
        _LER_DASHBOARD
    )
    referencia.close()


def test_fluxos_com_testes_manuais_iguais_ao_python(
    abrir, navegador, report_padrao
):
    pagina = abrir(report_padrao)
    pagina.adicionar(status="Passou", fluxo="Jornada E2E")
    pagina.adicionar(status="Falhou", fluxo="Holerite")
    pagina.adicionar(melhoria=True, status="Corrigido", fluxo="holerite")
    pagina.adicionar(melhoria=True, fluxo="Espelho")  # sem Status: não conta

    cards = pagina.page.locator(".qa-fluxos .qa-flow-row")
    vistos = [cards.nth(i).evaluate(_LER_FLUXO) for i in range(cards.count())]

    referencia = navegador.new_page()
    esperados = []
    for nome, dados in (
        ("jornada e2e", {"ok": 2, "fail": 1}),
        ("Holerite", {"ok": 1, "fail": 1}),
    ):
        referencia.set_content(build_fluxo_html_card(nome, dados))
        esperados.append(
            referencia.locator(".qa-flow-row").evaluate(_LER_FLUXO)
        )
    referencia.close()

    assert vistos == esperados


# === Testes manuais e melhorias ===
def test_fluxo_adota_a_grafia_existente_e_ordena_as_linhas(
    abrir, report_padrao
):
    pagina = abrir(report_padrao)
    pagina.adicionar(ct="CT1", fluxo="Teste Ricadio")
    pagina.adicionar(ct="CT2")
    pagina.adicionar(ct="CT3", fluxo="TESTE RICADIO")
    pagina.adicionar(ct="CT4", fluxo="jornada e2e")

    linhas = pagina.page.eval_on_selector_all(
        ".qa-bloco-manuais tr.qa-manual-row",
        "e => e.map(t => t.querySelector('.qa-manual-teste').value + ' ' + "
        "t.querySelector('.qa-fluxo-botao').textContent)",
    )

    assert linhas == [
        "CT1 Fluxo: Teste Ricadio",
        "CT3 Fluxo: Teste Ricadio",
        "CT4 Fluxo: JORNADA E2E",
        "CT2 + Fluxo",
    ]


def test_teste_manual_volta_ao_recarregar(abrir, report_padrao):
    pagina = abrir(report_padrao)
    linha = pagina.adicionar(ct="CT900 · Manual", status="Corrigido")
    linha.locator("[data-chave=apontamento]").select_option(
        "Correção realizada"
    )
    linha.locator(".qa-manual-obs").fill("Linha 1\nLinha 2 <x>")

    pagina.recarregar()
    linha = pagina.page.locator(".qa-bloco-manuais tr.qa-manual-row")

    assert linha.locator(".qa-manual-teste").input_value() == "CT900 · Manual"
    assert linha.locator("[data-chave=resultado]").input_value() == "Corrigido"
    assert (
        linha.locator(".qa-manual-obs").input_value() == "Linha 1\nLinha 2 <x>"
    )


def test_blocos_de_cards_contam_por_origem(abrir, report_padrao):
    pagina = abrir(report_padrao)
    grupos = ".qa-kpi-grupo:not([hidden])"
    assert pagina.page.locator(grupos).count() == 0

    pagina.adicionar(status="Corrigido")
    pagina.adicionar(status="Não corrigido")
    melhoria = pagina.adicionar(melhoria=True, status="Corrigido")
    melhoria.locator("[data-chave=apontamento]").select_option(
        "Melhoria implementada"
    )
    pagina.page.locator(
        "#results-table select[data-campo=apontamento]"
    ).select_option("Correção não realizada")

    valores = pagina.page.evaluate(
        "() => Object.fromEntries([...document.querySelectorAll("
        "'.qa-kpi-grupo [data-qa-kpi]')].map(c => [c.dataset.qaKpi, "
        "c.querySelector('.qa-kpi-value').textContent]))"
    )

    assert valores == {
        "manual-passou": "0",
        "manual-falhou": "0",
        "corrigido": "1",
        "nao-corrigido": "1",
        "correcao-realizada": "0",
        "correcao-nao-realizada": "1",
        "melhorias": "1",
        "melhoria-corrigida": "1",
        "melhoria-nao-corrigida": "0",
        "melhoria-implementada": "1",
        "melhoria-nao-implementada": "0",
    }
    assert pagina.page.locator(".qa-kpi-grupo-resumo").all_inner_texts() == [
        "2 testes · 1 corrigido · 1 não corrigido",
        "1 melhoria · 1 implementada",
    ]
    # Fechados por padrão.
    assert pagina.page.locator(".qa-kpi-grupo[open]").count() == 0


# === Baixar HTML ===
def _baixar(pagina, destino):
    with pagina.page.expect_download() as download:
        pagina.page.click("[data-qa-baixar]")

    caminho = destino / download.value.suggested_filename
    download.value.save_as(caminho)

    return caminho


def test_copia_e_somente_leitura_e_leva_tudo(abrir, report_padrao, tmp_path):
    pagina = abrir(report_padrao)
    pagina.page.locator(
        "#results-table select[data-campo=categoria]"
    ).select_option("Moderado")
    linha = pagina.adicionar(ct="CT900", status="Falhou", fluxo="Holerite")

    with pagina.page.expect_file_chooser() as escolha:
        linha.locator(".qa-evidencia-anexar").click()
    arquivo = tmp_path / "tela.png"
    arquivo.write_bytes(base64.b64decode(_PNG))
    escolha.value.set_files(str(arquivo))
    pagina.page.wait_for_selector(".qa-evidencia-abrir")
    totais = pagina.page.evaluate(_LER_DASHBOARD)

    copia = abrir(_baixar(pagina, tmp_path)).page

    editaveis = (
        "#results-table select, .qa-bloco-manuais select, "
        ".qa-bloco-manuais input, .qa-bloco-manuais textarea"
    )
    assert copia.locator(editaveis).count() == 0
    assert copia.locator(".qa-baixar-html").inner_text() == "Somente leitura"
    assert (
        "Moderado"
        in copia.locator(".qa-classificacao--fixa").all_inner_texts()
    )
    assert copia.locator(".qa-bloco-manuais .qa-test-path").inner_text() == (
        "Teste manual · Fluxo: Holerite"
    )
    assert copia.evaluate(_LER_DASHBOARD) == totais

    copia.locator(".qa-evidencia-abrir").click()
    assert copia.locator(".qa-lightbox img").count() == 1
