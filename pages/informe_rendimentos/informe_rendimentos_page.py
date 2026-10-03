from pages.android_locators import android_pendente
from pages.compartilhado.lista_documentos_page import ListaDocumentosPage
from pages.menu_page import MenuLateralPage
from utils.periodo import interpretar_exercicio


class InformeRendimentosPage(ListaDocumentosPage):
    """
    Page: tela "Informe de rendimento" (menu lateral -> INFORME DE
    RENDIMENTOS).

    Um informe por exercício ("IR-2026").
    """

    SCREEN_NAME = "informe_rendimentos"
    NOME_TELA = "Informe de Rendimentos"
    OPCAO_MENU = MenuLateralPage.INFORME_RENDIMENTOS
    SLUG_VISIBILIDADE = "informe"

    # PENDENTE: ids da tela no Android (iOS:
    # informeRendimentos.tblInformes, informeRendimentos.cellExercicio_*,
    # informeRendimentos.lblExercicio).
    TABELA = android_pendente("informe_lista")
    PREFIXO_CELULA = "PENDENTE_informe_item"
    ID_LABEL_PERIODO = "PENDENTE_informe_exercicio"

    interpretar_periodo = staticmethod(interpretar_exercicio)
