"""
Segundo período ou pular (tests.support.documentos): com um documento
só, volta à Home e pula; com dois ou mais, devolve o segundo.
"""

from unittest.mock import Mock

import pytest

from tests.support.documentos import segundo_periodo_ou_pular


def _pagina(periodos: list[str]) -> Mock:
    pagina = Mock()
    pagina.NOME_TELA = "Informe de Rendimentos"
    pagina.periodos_do_mais_recente.return_value = periodos
    return pagina


def test_devolve_o_segundo_mais_recente():
    pagina = _pagina(["IR-2026", "IR-2025", "IR-2024"])

    assert segundo_periodo_ou_pular(pagina) == "IR-2025"
    pagina.voltar_para_home.assert_not_called()


def test_um_documento_so_volta_para_home_e_pula():
    pagina = _pagina(["IR-2026"])

    with pytest.raises(pytest.skip.Exception, match="só 1 documento"):
        segundo_periodo_ou_pular(pagina)

    # A sessão é compartilhada: pular com a tela aberta quebraria o
    # próximo teste.
    pagina.voltar_para_home.assert_called_once()
