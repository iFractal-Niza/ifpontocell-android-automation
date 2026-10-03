import re
from functools import cached_property
from time import monotonic, sleep

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
)

from pages.android_locators import (
    android_id,
    android_text,
    android_text_matches,
)
from pages.base_page import BasePage
from pages.menu_page import MenuPerfilPage
from pages.navegacao import VoltarParaHomeMixin
from utils.texto import normalizar_texto


class PrivacidadePage(VoltarParaHomeMixin, BasePage):
    """
    Page: tela "Privacidade" (menu do perfil -> PRIVACIDADE).

    "Índice" e os itens do índice no topo; abaixo, a política inteira,
    cada seção aberta por um título igual ao item do índice. Tocar num
    item rola até a seção. Por isso o mesmo texto aparece duas vezes na
    árvore: a primeira ocorrência é o item do índice; a última, o título
    da seção.

    Android (Inspector): TextViews nativos dentro do scrollView; itens
    do índice com id indice_* e títulos das seções com id próprio. A
    árvore só traz o que está na tela: depois de rolar até a seção, o
    item do índice some dela (ver secao_esta_visivel).
    """

    SCREEN_NAME = "privacidade"
    NOME_TELA = "Privacidade"

    ROTULO_INDICE = "Índice"

    # Confirmado no Inspector.
    TITULO = android_text("PRIVACIDADE")
    CABECALHO_INDICE = android_text(ROTULO_INDICE)
    TABELA = android_id("scrollView")
    TEXTOS = (AppiumBy.CLASS_NAME, "android.widget.TextView")

    # Itens do índice: id indice_* (ex.: indice_os_direitos); o título
    # da seção tem o id sem o prefixo (os_direitos).
    PREFIXO_ID_INDICE = ":id/indice_"

    # === Composição ===
    @cached_property
    def menu_perfil(self) -> MenuPerfilPage:
        return MenuPerfilPage(self.driver)

    # === Acesso ===
    def acessar(self) -> None:
        self.menu_perfil.acessar(MenuPerfilPage.PRIVACIDADE)

        assert self.esta_aberta(timeout=self.LONG_TIMEOUT), (
            "A tela 'Privacidade' não foi exibida após tocar em PRIVACIDADE "
            "no menu do perfil."
        )

    def esta_aberta(self, timeout: float | None = None) -> bool:
        # Espera pelo "Índice", que só existe nesta tela: o TITULO
        # ("PRIVACIDADE") também casa com a opção do menu do perfil.
        return self._is_visible(self.CABECALHO_INDICE, timeout=timeout) and (
            self._is_visible(self.TITULO, timeout=self.SHORT_TIMEOUT)
        )

    # === Índice ===
    def indice(self) -> list[str]:
        """
        Itens do índice, na ordem: os textos entre "Índice" e o primeiro
        texto repetido (o título da primeira seção, igual ao 1º item).
        """
        textos = [
            normalizar_texto(elemento.text)
            for elemento in self.driver.find_element(
                *self.TABELA
            ).find_elements(*self.TEXTOS)
        ]

        if self.ROTULO_INDICE not in textos:
            return []

        itens: list[str] = []

        for texto in textos[textos.index(self.ROTULO_INDICE) + 1 :]:
            if texto in itens:
                break

            itens.append(texto)

        return itens

    @staticmethod
    def _padrao_do_titulo(titulo: str) -> str:
        """
        Regex (Java, do UiSelector.textMatches) que aceita qualquer
        espaço entre as palavras: o app pode trocar espaços comuns por
        especiais (caso real no iOS: "3. Os direitos dos titulares").
        """
        return r"\s+".join(re.escape(palavra) for palavra in titulo.split())

    def _ocorrencias(self, titulo: str) -> list:
        """
        Os textos iguais ao título, na ordem da árvore. O texto
        normalizado confirma que é o mesmo título.
        """
        candidatos = self.driver.find_elements(
            *android_text_matches(self._padrao_do_titulo(titulo))
        )

        return [
            elemento
            for elemento in candidatos
            if normalizar_texto(elemento.text) == titulo
        ]

    def tocar_item_do_indice(self, titulo: str) -> None:
        ocorrencias = self._ocorrencias(titulo)

        assert ocorrencias, f"Item {titulo!r} não encontrado no índice."

        ocorrencias[0].click()

        self._log_info(
            "Item do índice da Privacidade tocado",
            event="privacy_index_item_tapped",
            item=titulo,
        )

    def _e_item_do_indice(self, elemento) -> bool:
        return self.PREFIXO_ID_INDICE in (
            elemento.get_attribute("resource-id") or ""
        )

    def secao_esta_visivel(self, titulo: str, timeout: float) -> bool:
        """
        O título da seção (a última ocorrência do texto) está visível
        dentro da área de conteúdo.

        Particularidade do Android: a árvore só traz o que está na tela,
        e o item do índice que rolou para fora some dela. No lugar de
        exigir as duas ocorrências (como no iOS), a seção é a última
        ocorrência que não é item do índice (id sem o prefixo indice_).
        """
        limite = monotonic() + timeout

        while True:
            try:
                area = self.driver.find_element(*self.TABELA).rect
                secoes = [
                    elemento
                    for elemento in self._ocorrencias(titulo)
                    if not self._e_item_do_indice(elemento)
                ]

                if secoes:
                    secao = secoes[-1]
                    topo = secao.rect["y"]

                    if (
                        secao.is_displayed()
                        and area["y"] <= topo < area["y"] + area["height"]
                    ):
                        return True
            except (StaleElementReferenceException, WebDriverException):
                pass

            if monotonic() >= limite:
                return False

            sleep(self.POLL_FREQUENCY)
