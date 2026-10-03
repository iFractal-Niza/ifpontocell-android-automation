"""
Privacidade (menu do perfil -> PRIVACIDADE).

O texto da política não é validado (parágrafos longos: qualquer ajuste
de redação quebraria o teste); valida-se o índice completo e a navegação
de uma amostra de itens (início, meio e fim da política).
"""

import pytest

from pages.privacidade.privacidade_page import PrivacidadePage

INDICE = (
    "1. Introdução",
    "1.1. Objetivo e escopo desta Política",
    "1.2. Responsabilidades das partes",
    "2. Ciclo de Vida dos Dados",
    "2.1. Coleta de dados",
    "2.2. Uso e acesso aos dados pessoais",
    "2.3. Cancelamento de contrato e eliminação de dados pessoais",
    "2.4. Transferência internacional de dados pessoais",
    "3. Os direitos dos titulares",
    "3.1. Consentimento sobre o uso de dados pessoais",
    "4. Requisitos técnicos na proteção de dados pessoais",
    "5. Alterações da Política de Privacidade de Dados",
)

# Amostra da navegação: início, meio e fim da política.
ITENS_NAVEGADOS = (
    "1. Introdução",
    "3. Os direitos dos titulares",
    "5. Alterações da Política de Privacidade de Dados",
)


@pytest.mark.ct("CT011")
@pytest.mark.regression
def test_privacidade_indice_e_navegacao(home_autenticada):
    """
    Valida o índice da Política de Privacidade e que os itens 1, 3 e 5
    levam às suas seções.

    Fronteira: Home -> menu do perfil -> PRIVACIDADE -> índice completo
    -> para os itens 1, 3 e 5: tocar -> seção visível -> Home -> reabre
    a Privacidade pelo menu -> ... -> Home.

    Entre os itens, a tela é reaberta em vez de rolar de volta ao
    índice: no iOS, depois de rolar, a árvore de acessibilidade ficava
    desatualizada e o índice sumia dela (mantido no Android).
    """
    pagina = PrivacidadePage(home_autenticada.driver)
    pagina.acessar()

    assert pagina.indice() == list(INDICE), (
        f"O índice da Privacidade não confere. Exibido: {pagina.indice()}"
    )

    sem_navegacao = []

    for numero, item in enumerate(ITENS_NAVEGADOS):
        if numero:
            pagina.voltar_para_home()
            pagina.acessar()

        pagina.tocar_item_do_indice(item)

        if not pagina.secao_esta_visivel(item, timeout=pagina.DEFAULT_TIMEOUT):
            sem_navegacao.append(item)

    assert not sem_navegacao, (
        f"Itens do índice que não levaram à seção: {sem_navegacao}."
    )

    pagina.voltar_para_home()
