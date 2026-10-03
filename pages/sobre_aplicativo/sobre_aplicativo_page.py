from functools import cached_property

from pages.android_locators import android_text
from pages.base_page import BasePage
from pages.compartilhado.tabela_rotulo_valor import TabelaRotuloValorMixin
from pages.menu_page import MenuPerfilPage
from pages.navegacao import VoltarParaHomeMixin


class SobreAplicativoPage(
    TabelaRotuloValorMixin, VoltarParaHomeMixin, BasePage
):
    """
    Page: tela "Sobre o aplicativo" (menu do perfil -> SOBRE O
    APLICATIVO).

    Uma tabela: descrição do app, pares rótulo/valor (NOME, VERSÃO,
    DESENVOLVEDOR, PLATAFORMA, STATUS) e os dados da empresa no fim, que
    só entram na árvore depois de rolar (ler_conteudo, do mixin).
    """

    SCREEN_NAME = "sobre_aplicativo"
    NOME_TELA = "Sobre o aplicativo"

    # PENDENTE: por texto, como no iOS, até o XML da tela
    # (PENDENCIAS_LOCATORS_ANDROID.md).
    TITULO = android_text("SOBRE O APLICATIVO")
    ROTULO_VERSAO = android_text("VERSÃO")

    # === Composição ===
    @cached_property
    def menu_perfil(self) -> MenuPerfilPage:
        return MenuPerfilPage(self.driver)

    # === Acesso ===
    def acessar(self) -> None:
        self.menu_perfil.acessar(MenuPerfilPage.SOBRE_APLICATIVO)

        assert self.esta_aberta(timeout=self.LONG_TIMEOUT), (
            "A tela 'Sobre o aplicativo' não foi exibida após tocar em "
            "SOBRE O APLICATIVO no menu do perfil."
        )

    def esta_aberta(self, timeout: float | None = None) -> bool:
        return self._is_visible(self.TITULO, timeout=timeout) and (
            self._is_visible(self.ROTULO_VERSAO, timeout=self.SHORT_TIMEOUT)
        )
