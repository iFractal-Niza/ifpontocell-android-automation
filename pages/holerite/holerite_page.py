from pages.android_locators import android_pendente
from pages.compartilhado.lista_documentos_page import ListaDocumentosPage
from pages.menu_page import MenuLateralPage
from utils.periodo import interpretar_competencia


class HoleritePage(ListaDocumentosPage):
    """
    Page: tela "Holerite" (menu lateral -> HOLERITE).

    Um holerite por competência ("Setembro 2026").
    """

    SCREEN_NAME = "holerite"
    NOME_TELA = "Holerite"
    OPCAO_MENU = MenuLateralPage.HOLERITE
    SLUG_VISIBILIDADE = "holerite"

    # PENDENTE: ids da tela no Android (iOS: holerite.tblHolerites,
    # holerite.cellCompetencia_*, holerite.lblCompetencia).
    TABELA = android_pendente("holerite_lista")
    PREFIXO_CELULA = "PENDENTE_holerite_item"
    ID_LABEL_PERIODO = "PENDENTE_holerite_competencia"

    interpretar_periodo = staticmethod(interpretar_competencia)
