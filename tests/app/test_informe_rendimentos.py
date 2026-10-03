import pytest

from pages.informe_rendimentos.informe_rendimentos_page import (
    InformeRendimentosPage,
)
from tests.support.documentos import segundo_periodo_ou_pular


@pytest.mark.ct("CT018")
@pytest.mark.smoke
def test_visualizar_informe_rendimentos_mais_recente(home_autenticada):
    """
    Valida a abertura e o salvamento do informe de rendimentos do
    exercício mais recente.

    Fronteira: Home -> menu -> Informe de Rendimentos -> visualizar o
    mais recente -> documento do mesmo exercício -> salvar -> OK ->
    lista -> Home.

    Usa a sessão compartilhada da jornada: rodando depois do E2E,
    reaproveita o login; rodando isolado, faz o primeiro acesso.

    Pré-condição externa: o usuário de homologação tem informes
    publicados (hoje, IR-2025 e IR-2026). A escolha do mais recente é
    coberta por teste unitário.
    """
    informe_page = InformeRendimentosPage(home_autenticada.driver)
    informe_page.acessar()

    exercicio = informe_page.periodo_mais_recente()

    visualizador = informe_page.visualizar(exercicio)

    visualizador.salvar()

    # Volta até a Home: a sessão é compartilhada com os próximos testes.
    informe_page.voltar_do_visualizador(visualizador)
    informe_page.voltar_para_home()


@pytest.mark.ct("CT019")
@pytest.mark.regression
def test_visualizar_informe_rendimentos_segundo_mais_recente(
    home_autenticada,
):
    """
    Valida a abertura do informe de rendimentos do segundo exercício
    mais recente, sem salvar.

    Fronteira: Home -> menu -> Informe de Rendimentos -> visualizar o
    segundo mais recente -> documento do mesmo exercício -> lista ->
    Home.

    Cobre a abertura de um documento que não é o do topo da lista. O
    salvar já é coberto pelo teste do mais recente. Com um informe só,
    o teste é pulado (massa de teste, não defeito).
    """
    informe_page = InformeRendimentosPage(home_autenticada.driver)
    informe_page.acessar()

    exercicio = segundo_periodo_ou_pular(informe_page)

    visualizador = informe_page.visualizar(exercicio)

    informe_page.voltar_do_visualizador(visualizador)
    informe_page.voltar_para_home()
