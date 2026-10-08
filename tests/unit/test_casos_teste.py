"""
Execução por ID de caso de teste (tests.fixtures.casos_teste, --ct) e o
ID no título do report.
"""

from types import SimpleNamespace

import pytest
from qa_observability.relatorio import titulo_do_item

from tests.fixtures.casos_teste import id_do_item, separar_por_ct


def _item(identificador: str | None, nome: str = "test_x", doc: str = ""):
    marker = (
        None
        if identificador is None
        else SimpleNamespace(args=(identificador,))
    )

    return SimpleNamespace(
        nodeid=f"tests/app/test_login.py::{nome}",
        function=SimpleNamespace(__doc__=doc),
        get_closest_marker=lambda nome_marker: marker,
    )


def test_id_do_item():
    assert id_do_item(_item("CT004")) == "CT004"
    assert id_do_item(_item(None)) == ""


def test_sem_a_opcao_roda_tudo():
    items = [_item("CT001"), _item(None)]

    assert separar_por_ct(items, "") == (items, [])


def test_seleciona_os_ids_pedidos():
    primeiro, segundo, terceiro = _item("CT001"), _item("CT002"), _item(None)

    selecionados, descartados = separar_por_ct(
        [primeiro, segundo, terceiro],
        " ct002 , CT001",
    )

    assert selecionados == [primeiro, segundo]
    assert descartados == [terceiro]


def test_id_inexistente_e_erro_de_uso():
    with pytest.raises(pytest.UsageError, match="CT999"):
        separar_por_ct([_item("CT001")], "CT001,CT999")


def test_titulo_do_report_leva_o_id_na_frente():
    item = _item("CT004", doc="Valida erro ao informar login inválido.")

    assert titulo_do_item(item) == (
        "CT004 · Valida erro ao informar login inválido"
    )


def test_titulo_sem_ct_fica_sem_prefixo():
    assert titulo_do_item(_item(None, nome="test_senha_invalida")) == (
        "Senha invalida"
    )
