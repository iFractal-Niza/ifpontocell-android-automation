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


# === Seção visível (Android: o índice rolado some da árvore) ===
def _titulo(texto: str, resource_id: str, y: int = 300) -> Mock:
    elemento = _elemento(texto)
    elemento.get_attribute.side_effect = lambda nome: (
        resource_id if nome == "resource-id" else None
    )
    elemento.rect = {"y": y}
    elemento.is_displayed.return_value = True
    return elemento


def _pagina_com_ocorrencias(ocorrencias: list) -> PrivacidadePage:
    driver = Mock()
    driver.find_element.return_value.rect = {"y": 200, "height": 1800}
    driver.find_elements.return_value = ocorrencias
    return PrivacidadePage(driver)


TITULO = "3. Os direitos dos titulares"


def test_secao_sozinha_na_arvore_conta_como_visivel():
    # Caso real: depois de rolar, o item do índice saiu da árvore.
    secao = _titulo(TITULO, "br.com.ifractal.Stou:id/os_direitos")

    assert _pagina_com_ocorrencias([secao]).secao_esta_visivel(TITULO, 0)


def test_so_o_item_do_indice_nao_conta_como_secao():
    item = _titulo(TITULO, "br.com.ifractal.Stou:id/indice_os_direitos")

    assert not _pagina_com_ocorrencias([item]).secao_esta_visivel(TITULO, 0)


def test_secao_fora_da_area_nao_conta():
    secao = _titulo(TITULO, "br.com.ifractal.Stou:id/os_direitos", y=2500)

    assert not _pagina_com_ocorrencias([secao]).secao_esta_visivel(TITULO, 0)
