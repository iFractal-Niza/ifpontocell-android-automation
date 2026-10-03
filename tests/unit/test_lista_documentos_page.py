"""
Escolha do período mais recente nas listas de documentos
(ListaDocumentosPage e subclasses). Os textos lidos da tela são
injetados no lugar de listar_periodos.
"""

import pytest

from pages.holerite.holerite_page import HoleritePage
from pages.informe_rendimentos.informe_rendimentos_page import (
    InformeRendimentosPage,
)


@pytest.fixture
def com_periodos(monkeypatch):
    def criar(classe, textos: list[str]):
        pagina = classe(driver=None)
        monkeypatch.setattr(pagina, "listar_periodos", lambda: textos)
        return pagina

    return criar


# === Holerite (competência) ===
def test_holerite_mais_recente_pela_data_e_nao_pela_posicao(com_periodos):
    pagina = com_periodos(
        HoleritePage, ["Janeiro 2026", "Setembro 2026", "Dezembro 2025"]
    )

    assert pagina.periodo_mais_recente() == "Setembro 2026"


def test_holerite_mais_recente_na_virada_do_ano(com_periodos):
    pagina = com_periodos(HoleritePage, ["Dezembro 2025", "Janeiro 2026"])

    assert pagina.periodo_mais_recente() == "Janeiro 2026"


def test_holerite_periodo_ilegivel_mostra_o_texto(com_periodos):
    pagina = com_periodos(HoleritePage, ["Setembro/2026"])

    with pytest.raises(ValueError, match="Setembro/2026"):
        pagina.periodo_mais_recente()


# === Informe de Rendimentos (exercício) ===
def test_informe_mais_recente_pelo_ano(com_periodos):
    pagina = com_periodos(InformeRendimentosPage, ["IR-2025", "IR-2026"])

    assert pagina.periodo_mais_recente() == "IR-2026"


def test_informe_periodo_ilegivel_mostra_o_texto(com_periodos):
    pagina = com_periodos(InformeRendimentosPage, ["IRPF 2026"])

    with pytest.raises(ValueError, match="IRPF 2026"):
        pagina.periodo_mais_recente()


# === Comum ===
@pytest.mark.parametrize("classe", [HoleritePage, InformeRendimentosPage])
def test_lista_vazia_falha_com_orientacao(com_periodos, classe):
    with pytest.raises(AssertionError, match="documentos publicados"):
        com_periodos(classe, []).periodo_mais_recente()


@pytest.mark.parametrize("classe", [HoleritePage, InformeRendimentosPage])
def test_subclasse_define_todos_os_atributos_da_base(classe):
    # Esquecer um atributo só apareceria no emulador, no meio do teste.
    for atributo in (
        "NOME_TELA",
        "OPCAO_MENU",
        "SLUG_VISIBILIDADE",
        "TABELA",
        "PREFIXO_CELULA",
        "ID_LABEL_PERIODO",
        "interpretar_periodo",
    ):
        assert getattr(classe, atributo, None), (
            f"{classe.__name__} não definiu {atributo}"
        )


# === Ordenação (base do segundo mais recente) ===
def test_holerite_segundo_na_ordem(com_periodos):
    pagina = com_periodos(
        HoleritePage, ["Janeiro 2026", "Setembro 2026", "Agosto 2026"]
    )

    assert pagina.periodos_do_mais_recente()[1] == "Agosto 2026"


def test_informe_segundo_na_ordem(com_periodos):
    pagina = com_periodos(InformeRendimentosPage, ["IR-2026", "IR-2025"])

    assert pagina.periodos_do_mais_recente()[1] == "IR-2025"


def test_periodos_do_mais_recente_ordena_pelo_valor(com_periodos):
    pagina = com_periodos(
        HoleritePage, ["Dezembro 2025", "Setembro 2026", "Janeiro 2026"]
    )

    assert pagina.periodos_do_mais_recente() == [
        "Setembro 2026",
        "Janeiro 2026",
        "Dezembro 2025",
    ]
