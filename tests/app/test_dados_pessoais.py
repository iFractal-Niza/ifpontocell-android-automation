"""
Dados Pessoais (menu do perfil -> DADOS PESSOAIS).
"""

import pytest

from pages.dados_pessoais.dados_pessoais_page import DadosPessoaisPage
from utils.texto import normalizar_texto


@pytest.mark.ct("CT026")
@pytest.mark.regression
def test_dados_pessoais_exibe_o_colaborador(
    home_autenticada,
    monitor_nome_pessoa,
):
    """
    Valida que Dados Pessoais exibe o nome do colaborador logado, o
    mesmo de MONITOR_NOME_PESSOA no env.<device>.yaml.

    Fronteira: Home -> menu do perfil -> DADOS PESSOAIS -> COLABORADOR
    -> Home.
    """
    pagina = DadosPessoaisPage(home_autenticada.driver)
    pagina.acessar()

    exibido = pagina.colaborador()
    esperado = normalizar_texto(monitor_nome_pessoa)

    assert exibido == esperado, (
        f"COLABORADOR exibido {exibido!r}, esperado {esperado!r} "
        "(MONITOR_NOME_PESSOA no env.<device>.yaml)."
    )

    pagina.voltar_para_home()
