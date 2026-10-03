from functools import cached_property

from pages.alertas import AlertaAppMixin
from pages.android_locators import android_text
from pages.base_page import BasePage
from pages.menu_page import MenuPerfilPage
from pages.navegacao import VoltarParaHomeMixin


class AlterarSenhaBasePage(AlertaAppMixin, VoltarParaHomeMixin, BasePage):
    """
    O comum às duas abas da tela "Alterar Senha" (menu do perfil ->
    ALTERAR SENHA): entrar pelo menu, o título e a troca de aba. Cada aba
    tem a sua page: AlterarPinPage (SENHA 4 DÍGITOS) e
    AlterarSenhaSistemaPage (SENHA SISTEMA).
    """

    NOME_TELA = "Alterar Senha"

    # Nome da aba (no iOS, dentro do controle alterarSenha.segTipoSenha).
    # PENDENTE: pelo texto da aba até o XML da tela.
    ABA = ""

    # PENDENTE: por texto, como no iOS, até o XML da tela.
    TITULO = android_text("ALTERAR SENHA")

    # === Composição ===
    @cached_property
    def menu_perfil(self) -> MenuPerfilPage:
        return MenuPerfilPage(self.driver)

    # === Acesso ===
    @classmethod
    def _locator_aba(cls, aba: str) -> tuple[str, str]:
        return android_text(aba)

    def _abrir_tela_na_aba(self) -> None:
        self.menu_perfil.acessar(MenuPerfilPage.ALTERAR_SENHA)

        assert self._is_visible(self.TITULO, timeout=self.LONG_TIMEOUT), (
            "A tela 'Alterar Senha' não foi exibida após tocar em ALTERAR "
            "SENHA no menu do perfil."
        )

        self._click(
            self._locator_aba(self.ABA),
            timeout=self.DEFAULT_TIMEOUT,
            element_name=f"aba_{self.ABA.lower().replace(' ', '_')}",
        )
