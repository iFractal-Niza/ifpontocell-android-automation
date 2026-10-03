import pytest

from pages.estado_humor.estado_humor_page import EstadoHumorPage


@pytest.mark.ct("CT020")
@pytest.mark.smoke
def test_registrar_humor(home_autenticada):
    """
    Valida o registro de um humor e a volta à tela do Estado de Humor.

    Fronteira: Home -> menu -> Estado de Humor -> escolher humor ->
    confirmar -> Estado de Humor -> Home.

    Não valida os percentuais do mês: o objetivo é o fluxo de registro
    completar sem travar o app.

    Usa a sessão compartilhada da jornada: rodando depois do E2E,
    reaproveita o login; rodando isolado, faz o primeiro acesso.
    """
    humor_page = EstadoHumorPage(home_autenticada.driver)
    humor_page.acessar()

    humor_page.registrar_humor("Feliz")

    # Volta à Home: a sessão é compartilhada com os próximos testes.
    humor_page.voltar_para_home()
