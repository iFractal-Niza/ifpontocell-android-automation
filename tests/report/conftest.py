"""
Testes do report no navegador (reports/assets/report.js) com o Playwright.

Cada teste abre um report de exemplo: um pytest-html de verdade, gerado
num diretório temporário com os mesmos ganchos do plugin (colunas,
dashboard, CSS e script injetados como em observability.pytest_report),
e confere o que o report.js faz na página. Não usam simulador nem a API:
rodam com `make test-report` (fora do `make unit`: abrem navegador).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="Playwright não instalado (make install)",
)

from observability.pytest_report import PROJECT_ROOT  # noqa: E402

# Um teste que falha (com árvore e print) e um que passa.
_AMOSTRA = """
def test_falha():
    assert False


def test_passa():
    pass
"""

# PNG 1x1, para o print da falha.
_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAF"
    "AAH/q842iQAAAABJRU5ErkJggg=="
)

# Os ganchos do plugin que montam a página, com os totais da automação
# vindos de QA_REPORT_STATS (o dashboard real usa os da execução).
_CONFTEST = f'''
import json
import os

import pytest
from pytest_html import extras

from observability.dashboard import build_results_summary_html, load_inline_js
from observability.pytest_report import (
    PROJECT_ROOT,
    _codificar_ascii_seguro,
    _codificar_js_ascii_seguro,
    pytest_html_results_table_header,
    pytest_html_results_table_row,
)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    report = resultado.get_result()

    if report.when == "call" and report.failed:
        report.extras = [
            extras.text("<arvore/>", name="Árvore da tela"),
            extras.png("{_PNG}", name="Print da falha"),
        ]


def pytest_html_results_summary(prefix, summary, postfix):
    stats = json.loads(os.environ["QA_REPORT_STATS"])
    css, painel = build_results_summary_html(PROJECT_ROOT, stats)

    prefix.append(f"<style>{{_codificar_ascii_seguro(css)}}</style>")
    prefix.append(_codificar_ascii_seguro(painel))
    postfix.append(
        f"<script>{{_codificar_js_ascii_seguro(load_inline_js(PROJECT_ROOT))}}</script>"
    )
'''

# Totais da automação no dashboard de exemplo: 1 passou, 1 falhou, num
# fluxo só (não é do smoke).
STATS_PADRAO = {
    "total": 2,
    "passed": 1,
    "failed": 1,
    "error": 0,
    "skipped": 0,
    "success_rate": 50.0,
    "criticas": 0,
    "por_fluxo": {"jornada e2e": {"ok": 1, "fail": 1, "duration": 30}},
}


def montar_report(destino: Path, stats: dict) -> Path:
    """Gera o report de exemplo em destino e devolve o caminho do HTML."""
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "test_amostra.py").write_text(_AMOSTRA, encoding="utf-8")
    (destino / "conftest.py").write_text(_CONFTEST, encoding="utf-8")
    html = destino / "report_amostra.html"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_amostra.py",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--html={html}",
            "--self-contained-html",
        ],
        cwd=destino,
        env={
            **os.environ,
            "PYTHONPATH": PROJECT_ROOT,
            "QA_REPORT_STATS": json.dumps(stats),
        },
        capture_output=True,
        check=False,
    )

    assert html.exists(), "o pytest-html não gerou o report de exemplo"

    return html


@pytest.fixture(scope="session")
def report_padrao(tmp_path_factory) -> Path:
    return montar_report(tmp_path_factory.mktemp("report"), STATS_PADRAO)


@pytest.fixture(scope="session")
def report_com_previstos(tmp_path_factory) -> Path:
    """Report de um make evidencias: com testes manuais previstos."""
    stats = {
        **STATS_PADRAO,
        "testes_manuais_previstos": [
            {
                "ct": "CT900",
                "descricao": "Exporta o espelho",
                "fluxo": "Espelho",
            },
            {
                "ct": "CT901",
                "descricao": "Avisa sem rede",
                "fluxo": "Jornada E2E",
            },
        ],
    }
    return montar_report(tmp_path_factory.mktemp("previstos"), stats)


@pytest.fixture(scope="session")
def outro_report(tmp_path_factory) -> Path:
    """Outro arquivo de report (outro caminho, dados salvos à parte)."""
    return montar_report(tmp_path_factory.mktemp("outro"), STATS_PADRAO)


# Nome próprio: a automação web tem o pytest-playwright, que já define a
# fixture "playwright".
@pytest.fixture(scope="session")
def instancia_playwright():
    with sync_api.sync_playwright() as instancia:
        yield instancia


@pytest.fixture(scope="session", params=["chromium"])
def navegador(request, instancia_playwright):
    instancia = getattr(instancia_playwright, request.param).launch()
    yield instancia
    instancia.close()


class Pagina:
    """Página do report, com os erros de JavaScript registrados."""

    def __init__(self, contexto, caminho: Path):
        self.contexto = contexto
        self.erros: list[str] = []
        self.page = contexto.new_page()
        self.page.on("pageerror", lambda erro: self.erros.append(str(erro)))
        self.page.on("dialog", lambda dialogo: dialogo.accept())
        self.page.goto(caminho.as_uri())
        self.page.wait_for_selector("tr.collapsible")

    def abrir_outro(self, caminho: Path) -> "Pagina":
        """Outro report no mesmo navegador (mesmos dados salvos)."""
        return Pagina(self.contexto, caminho)

    def recarregar(self):
        self.page.reload()
        self.page.wait_for_selector("tr.collapsible")

    def adicionar(self, *, melhoria=False, ct="", status="", fluxo=""):
        """Inclui um teste manual (ou uma melhoria) e preenche os campos."""
        seletor = (
            ".qa-adicionar-melhoria"
            if melhoria
            else ".qa-adicionar-teste:not(.qa-adicionar-melhoria)"
        )
        bloco = ".qa-melhorias-tabela" if melhoria else ".qa-bloco-manuais"

        self.page.click(seletor)
        linha = self.page.locator(f"{bloco} tr.qa-manual-row").last

        if ct:
            linha.locator(".qa-manual-teste").fill(ct)

        if status:
            linha.locator("[data-chave=resultado]").select_option(status)

        if fluxo:
            linha.locator(".qa-fluxo-botao").click()
            self.page.keyboard.type(fluxo)
            # Sair do campo: recolhe e reposiciona a linha pelo fluxo.
            self.page.locator(".qa-bloco-titulo").first.click()
            self.page.wait_for_timeout(50)

        return linha


@pytest.fixture(scope="session")
def webkit(instancia_playwright):
    """WebKit, o motor do Safari (IndexedDB e downloads em arquivo local)."""
    instancia = instancia_playwright.webkit.launch()
    yield instancia
    instancia.close()


@pytest.fixture
def abrir(navegador):
    """abrir(caminho) -> Pagina num contexto limpo (sem nada salvo)."""
    yield from _abridor(navegador)


@pytest.fixture
def abrir_no_webkit(webkit):
    yield from _abridor(webkit)


def _abridor(navegador):
    contextos = []
    paginas = []

    def _abrir(caminho: Path) -> Pagina:
        contexto = navegador.new_context(
            viewport={"width": 1400, "height": 900}, accept_downloads=True
        )
        contextos.append(contexto)
        pagina = Pagina(contexto, caminho)
        paginas.append(pagina)
        return pagina

    yield _abrir

    for pagina in paginas:
        assert pagina.erros == [], f"erro de JavaScript: {pagina.erros}"

    for contexto in contextos:
        contexto.close()
