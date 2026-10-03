"""
Leitura do índice da Privacidade (PrivacidadePage.indice): os textos
entre "Índice" e o primeiro texto repetido (o título da 1ª seção).
"""

from unittest.mock import Mock

from pages.privacidade.privacidade_page import PrivacidadePage


def _elemento(texto: str) -> Mock:
    elemento = Mock()
    elemento.text = texto
    return elemento


def _pagina_com_textos(textos: list[str]) -> PrivacidadePage:
    driver = Mock()
    driver.find_element.return_value.find_elements.return_value = [
        _elemento(texto) for texto in textos
    ]

    return PrivacidadePage(driver)


def test_indice_para_no_titulo_da_primeira_secao():
    pagina = _pagina_com_textos(
        [
            "Índice",
            "1. Introdução",
            "1.1. Objetivo e escopo desta Política",
            "5. Alterações da Política de Privacidade de Dados",
            # Corpo da política: começa repetindo o 1º item.
            "1. Introdução",
            "1.1. Objetivo e escopo desta Política",
            "Esta política aplica-se aos colaboradores...",
        ]
    )

    assert pagina.indice() == [
        "1. Introdução",
        "1.1. Objetivo e escopo desta Política",
        "5. Alterações da Política de Privacidade de Dados",
    ]


def test_sem_cabecalho_do_indice_devolve_vazio():
    assert _pagina_com_textos(["PRIVACIDADE", "texto"]).indice() == []


def test_ocorrencias_aceitam_espaco_especial_e_mantem_a_ordem():
    item = _elemento("3. Os direitos dos titulares")
    secao = _elemento("3. Os direitos dos titulares")
    outro = _elemento("3. Os direitos dos titulares (anexo)")

    driver = Mock()
    driver.find_elements.return_value = [item, outro, secao]
    pagina = PrivacidadePage(driver)

    assert pagina._ocorrencias("3. Os direitos dos titulares") == [item, secao]

    _, seletor = driver.find_elements.call_args.args
    assert "textMatches" in seletor
    assert r"3\\.\\s+Os\\s+direitos" in seletor
