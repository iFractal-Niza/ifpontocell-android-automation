"""
Script embutido na página do report (reports/assets/report.js): carga e
codificação para o <script>, e as células da tabela.
"""

from observability.dashboard import load_inline_js
from observability.pytest_report import (
    PROJECT_ROOT,
    _codificar_js_ascii_seguro,
    montar_celula_teste,
)


def test_script_da_pagina_e_encontrado():
    script = load_inline_js(PROJECT_ROOT)

    assert "traduzirFiltros" in script
    assert "abrirImagem" in script


def test_script_ausente_devolve_vazio(tmp_path):
    assert load_inline_js(str(tmp_path)) == ""


def test_acentos_viram_escape_do_javascript():
    codificado = _codificar_js_ascii_seguro("'Duração'")

    assert codificado == "'Dura\\u00e7\\u00e3o'"
    assert codificado.isascii()


def test_script_codificado_nao_fecha_a_tag_script():
    codificado = _codificar_js_ascii_seguro(load_inline_js(PROJECT_ROOT))

    assert codificado.isascii()
    assert "</script" not in codificado.lower()


def test_celula_do_teste_mostra_titulo_e_caminho_em_uma_linha():
    celula = montar_celula_teste(
        '<td class="col-testId">tests/app/test_h.py::test_x::setup</td>',
        "Abre o holerite <mais recente>",
    )

    assert "\n" not in celula
    assert "Abre o holerite &lt;mais recente&gt;" in celula
    assert "tests/app/test_h.py::test_x::setup" in celula


def test_celula_sem_titulo_fica_como_estava():
    original = '<td class="col-testId">tests/app/test_h.py::test_x</td>'

    assert montar_celula_teste(original, "") == original


def test_css_da_pagina_e_ascii_fora_dos_comentarios():
    # O plugin converte o não ASCII do CSS em referências HTML (&#237;),
    # que dentro de <style> não são interpretadas: um "Crítico" num
    # seletor ou um "▸" num content quebrariam. Use escapes do CSS
    # (\0000ED, \0025B8).
    import re
    from pathlib import Path

    for nome in ("style.css", "print.css"):
        css = (Path(PROJECT_ROOT) / "reports" / "assets" / nome).read_text(
            encoding="utf-8"
        )
        sem_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        fora_do_ascii = sorted({c for c in sem_comentarios if ord(c) > 127})

        assert fora_do_ascii == [], f"{nome}: {fora_do_ascii}"
