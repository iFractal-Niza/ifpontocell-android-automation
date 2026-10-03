import pytest

from pages.holerite.holerite_page import HoleritePage
from tests.support.documentos import segundo_periodo_ou_pular


@pytest.mark.ct("CT016")
@pytest.mark.smoke
def test_visualizar_holerite_mais_recente(home_autenticada):
    """
    Valida a abertura e o salvamento do holerite da competência mais
    recente.

    Fronteira: Home -> menu -> Holerite -> visualizar o mais recente
    -> documento da mesma competência -> salvar -> OK -> Holerite
    -> Home.

    O conteúdo do documento não tem texto acessível; a validação é a
    competência exibida no título do visualizador.

    Usa a sessão compartilhada da jornada: rodando depois do E2E,
    reaproveita o login; rodando isolado, faz o primeiro acesso.

    Pré-condição externa: o usuário de homologação tem holerites
    publicados (hoje, Janeiro a Setembro de 2026). A escolha do mais
    recente é coberta por teste unitário.
    """
    holerite_page = HoleritePage(home_autenticada.driver)
    holerite_page.acessar()

    competencia = holerite_page.periodo_mais_recente()

    visualizador = holerite_page.visualizar(competencia)

    visualizador.salvar()

    # Volta até a Home: a sessão é compartilhada com os próximos testes.
    holerite_page.voltar_do_visualizador(visualizador)
    holerite_page.voltar_para_home()


@pytest.mark.ct("CT017")
@pytest.mark.regression
def test_visualizar_holerite_segundo_mais_recente(home_autenticada):
    """
    Valida a abertura do holerite da segunda competência mais recente,
    sem salvar.

    Fronteira: Home -> menu -> Holerite -> visualizar o segundo mais
    recente -> documento da mesma competência -> Holerite -> Home.

    Cobre a abertura de um documento que não é o do topo da lista. O
    salvar já é coberto pelo teste do mais recente. Com um holerite só,
    o teste é pulado (massa de teste, não defeito).
    """
    holerite_page = HoleritePage(home_autenticada.driver)
    holerite_page.acessar()

    competencia = segundo_periodo_ou_pular(holerite_page)

    visualizador = holerite_page.visualizar(competencia)

    holerite_page.voltar_do_visualizador(visualizador)
    holerite_page.voltar_para_home()
