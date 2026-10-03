from pages.android_locators import android_text
from pages.home_page import HomePage


class VoltarParaHomeMixin:
    """
    Voltar da navBar para a Home, compartilhado pelas telas abertas pelo
    menu lateral (listas de documentos, Estado de Humor...).

    Requer, na classe que usa: NOME_TELA, SCREEN_NAME e os métodos da
    BasePage (_click_with_fallback). Declarar antes de BasePage nas bases.
    """

    # Botão de texto "VOLTAR" das telas abertas pelo menu (no iOS, ao
    # lado da seta). PENDENTE: confirmar no Inspector se há resource-id
    # (PENDENCIAS_LOCATORS_ANDROID.md).
    BOTAO_VOLTAR_TEXTO = android_text("VOLTAR")

    def _tocar_voltar(self) -> None:
        """
        Volta uma tela, sem validar o destino: quem chama confere para
        qual tela voltou.

        Tenta o botão de texto "VOLTAR" e, sem ele, o voltar do sistema
        (driver.back), que no Android cobre a seta da toolbar.
        """
        if self._click_if_visible(
            self.BOTAO_VOLTAR_TEXTO,
            timeout=self.SHORT_TIMEOUT,
            element_name=f"botao_voltar_{self.SCREEN_NAME}_texto",
        ):
            return

        self.driver.back()

    def voltar_para_home(self) -> HomePage:
        self._tocar_voltar()

        home_page = HomePage(self.driver)

        assert home_page.esta_na_home(timeout=home_page.LONG_TIMEOUT), (
            f"A Home não foi exibida após voltar de {self.NOME_TELA}."
        )

        return home_page
