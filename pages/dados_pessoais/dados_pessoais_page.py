from functools import cached_property

from pages.android_locators import android_id, android_text
from pages.base_page import BasePage
from pages.compartilhado.tabela_rotulo_valor import TabelaRotuloValorMixin
from pages.menu_page import MenuPerfilPage
from pages.navegacao import VoltarParaHomeMixin


class DadosPessoaisPage(TabelaRotuloValorMixin, VoltarParaHomeMixin, BasePage):
    """
    Page: tela "Dados Pessoais" (menu do perfil -> DADOS PESSOAIS).

    Foto do colaborador, logo da empresa e os pares rótulo/valor EMPRESA,
    COLABORADOR, DEPARTAMENTO e MATRÍCULA (ler_conteudo, do mixin; no iOS
    "DEPTO.:" e "MATRICULA"). Mesma leitura do iOS.
    """

    SCREEN_NAME = "dados_pessoais"
    NOME_TELA = "Dados Pessoais"

    ROTULO_COLABORADOR = "COLABORADOR"

    # A tela cabe inteira: lê uma vez, sem rolar.
    MAX_ROLAGENS = 0

    # Confirmado no Inspector.
    CABECALHO = android_id("header_dados_pessoais")
    TITULO = android_text("DADOS PESSOAIS")
    ROTULO_COLABORADOR_LOCATOR = android_text(ROTULO_COLABORADOR)

    # === Composição ===
    @cached_property
    def menu_perfil(self) -> MenuPerfilPage:
        return MenuPerfilPage(self.driver)

    # === Acesso ===
    def acessar(self) -> None:
        self.menu_perfil.acessar(MenuPerfilPage.DADOS_PESSOAIS)

        assert self.esta_aberta(timeout=self.LONG_TIMEOUT), (
            "A tela 'Dados Pessoais' não foi exibida após tocar em DADOS "
            "PESSOAIS no menu do perfil."
        )

    def esta_aberta(self, timeout: float | None = None) -> bool:
        # Pelo cabeçalho técnico: o texto "DADOS PESSOAIS" também casa
        # com a opção do menu do perfil.
        return self._is_visible(self.CABECALHO, timeout=timeout) and (
            self._is_visible(
                self.ROTULO_COLABORADOR_LOCATOR,
                timeout=self.SHORT_TIMEOUT,
            )
        )

    def colaborador(self) -> str:
        """Nome exibido em COLABORADOR ("" se não aparecer)."""
        return self.ler_conteudo().campos.get(self.ROTULO_COLABORADOR, "")
