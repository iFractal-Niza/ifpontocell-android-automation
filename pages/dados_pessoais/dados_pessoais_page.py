from functools import cached_property

from pages.android_locators import android_id, android_text
from pages.base_page import BasePage
from pages.menu_page import MenuPerfilPage
from pages.navegacao import VoltarParaHomeMixin
from utils.texto import normalizar_texto


class DadosPessoaisPage(VoltarParaHomeMixin, BasePage):
    """
    Page: tela "Dados Pessoais" (menu do perfil -> DADOS PESSOAIS).

    Como no iOS, só o nome do colaborador interessa ao teste. No Android
    o valor do COLABORADOR tem id próprio (nome) e é lido direto; os
    demais rótulos (EMPRESA, DEPARTAMENTO, MATRÍCULA) não são lidos.
    """

    SCREEN_NAME = "dados_pessoais"
    NOME_TELA = "Dados Pessoais"

    ROTULO_COLABORADOR = "COLABORADOR"

    # Confirmado no Inspector.
    CABECALHO = android_id("header_dados_pessoais")
    ROTULO_COLABORADOR_LOCATOR = android_text(ROTULO_COLABORADOR)
    VALOR_COLABORADOR = android_id("nome")

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
        elemento = self._obter_elemento_visivel_imediatamente(
            self.VALOR_COLABORADOR
        )

        if elemento is None:
            return ""

        return normalizar_texto(elemento.text)
