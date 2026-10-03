"""
Nome do colaborador nos Dados Pessoais (DadosPessoaisPage.colaborador),
lido pelo id próprio do valor (nome).
"""

from unittest.mock import Mock

from pages.dados_pessoais.dados_pessoais_page import DadosPessoaisPage


def test_colaborador_lido_pelo_id_nome(monkeypatch):
    pagina = DadosPessoaisPage(Mock())
    elemento = Mock()
    elemento.text = " Tester  QA "
    vistos = []

    def visivel(locator):
        vistos.append(locator)
        return elemento

    monkeypatch.setattr(
        pagina, "_obter_elemento_visivel_imediatamente", visivel
    )

    assert pagina.colaborador() == "Tester QA"
    assert vistos == [DadosPessoaisPage.VALOR_COLABORADOR]


def test_sem_colaborador_devolve_vazio(monkeypatch):
    pagina = DadosPessoaisPage(Mock())
    monkeypatch.setattr(
        pagina, "_obter_elemento_visivel_imediatamente", lambda _: None
    )

    assert pagina.colaborador() == ""
