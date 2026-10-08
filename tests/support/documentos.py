"""
Apoio aos testes das listas de documentos (Holerite, Informe...).
"""

import pytest
from qa_report.evidencias import capturar_evidencia

from pages.compartilhado.lista_documentos_page import ListaDocumentosPage


def segundo_periodo_ou_pular(pagina: ListaDocumentosPage) -> str:
    """
    Segundo período mais recente da lista; pula o teste se houver só um.

    Ter um documento só é questão de massa de teste, não defeito do
    app: o teste é pulado (fica visível em "Pulados", com o motivo), não
    reprovado. Antes de pular, registra o print da lista como evidência
    e volta à Home — a tela já foi aberta para contar os documentos e a
    sessão é compartilhada com os próximos testes.
    """
    periodos = pagina.periodos_do_mais_recente()

    if len(periodos) < 2:
        capturar_evidencia(
            pagina.driver,
            f"{pagina.NOME_TELA} com um documento só ({periodos[0]})",
        )
        pagina.voltar_para_home()

        pytest.skip(
            f"{pagina.NOME_TELA}: o usuário tem só 1 documento "
            f"({periodos[0]}); o cenário do segundo mais recente precisa "
            "de pelo menos dois."
        )

    return periodos[1]
