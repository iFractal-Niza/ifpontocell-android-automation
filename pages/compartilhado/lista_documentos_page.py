from collections.abc import Callable
from functools import cached_property

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from pages.android_locators import (
    android_id,
    android_id_prefixo,
    android_pendente,
)
from pages.base_page import BasePage
from pages.compartilhado.visualizador_documento_page import (
    VisualizadorDocumentoPage,
)
from pages.menu_page import MenuLateralPage
from pages.navegacao import VoltarParaHomeMixin


class ListaDocumentosPage(VoltarParaHomeMixin, BasePage):
    """
    Base das telas que listam documentos por período, abertas pelo menu
    lateral: uma lista em que cada linha tem o período ("Setembro 2026",
    "IR-2026") e o botão de visualizar, que abre o
    VisualizadorDocumentoPage.

    Mesma lógica do iOS. PENDENTE: ids das telas Android (lista, item,
    período, visualizar) a capturar no Inspector
    (PENDENCIAS_LOCATORS_ANDROID.md).

    Subclasses definem só o que muda entre as telas:

    - NOME_TELA / OPCAO_MENU / SLUG_VISIBILIDADE
    - TABELA, PREFIXO_CELULA, ID_LABEL_PERIODO
    - interpretar_periodo: texto -> valor ordenável (utils.periodo)
    """

    # === Definidos pelas subclasses ===
    NOME_TELA: str
    OPCAO_MENU: str
    # Chave em app_config.bts que liga/desliga a tela no servidor.
    SLUG_VISIBILIDADE: str
    TABELA: tuple[str, str]
    # No iOS o sufixo do id da célula (holerite.cellCompetencia_599) é o
    # id interno do documento: a célula é localizada pelo prefixo do id e
    # escolhida pelo texto. No Android, prefixo do resource-id.
    PREFIXO_CELULA: str
    ID_LABEL_PERIODO: str
    interpretar_periodo: Callable[[str], object]

    # === Comuns ===
    # Buscado sempre dentro da célula, nunca na tela toda.
    BOTAO_VISUALIZAR = android_pendente("lista_documentos_btnVisualizar")

    # === Composição ===
    @cached_property
    def menu_lateral(self) -> MenuLateralPage:
        return MenuLateralPage(self.driver)

    # === Locators derivados ===
    @property
    def _celula(self) -> tuple[str, str]:
        return android_id_prefixo(self.PREFIXO_CELULA)

    @property
    def _label_periodo(self) -> tuple[str, str]:
        return android_id(self.ID_LABEL_PERIODO)

    # === Acesso à tela ===
    def acessar(self) -> None:
        """
        Abre a tela pelo menu lateral a partir da Home.
        """
        self._log_info(
            f"Acessando {self.NOME_TELA}",
            event="document_list_open_started",
        )

        self.menu_lateral.acessar(self.OPCAO_MENU)

        assert self.esta_na_tela(timeout=self.LONG_TIMEOUT), (
            f"A tela '{self.NOME_TELA}' não foi exibida após selecionar a "
            "opção no menu lateral. Se a opção não aparece no menu, "
            f"verifique app_config.bts.{self.SLUG_VISIBILIDADE}.visible "
            "no servidor."
        )

        self._log_info(
            f"{self.NOME_TELA} acessado",
            event="document_list_open_finished",
        )

    def esta_na_tela(self, timeout: float | None = None) -> bool:
        is_visible = self._is_visible(self.TABELA, timeout=timeout)

        self._log_info(
            f"Verificação da tela {self.NOME_TELA} executada",
            event="document_list_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    # === Períodos ===
    def listar_periodos(self) -> list[str]:
        """
        Textos dos períodos na ordem exibida.
        """
        textos = []

        for elemento in self.driver.find_elements(*self._label_periodo):
            try:
                texto = (elemento.text or "").strip()
            except (StaleElementReferenceException, WebDriverException):
                continue

            if texto:
                textos.append(texto)

        self._log_info(
            f"Períodos de {self.NOME_TELA} listados",
            event="document_list_periods_listed",
            total=len(textos),
            periodos=textos,
        )

        return textos

    def periodos_do_mais_recente(self) -> list[str]:
        """
        Períodos exibidos, do mais recente para o mais antigo.

        Ordenados pelo valor interpretado, não pela posição na lista:
        não depende da ordenação da tela (coberta por teste unitário).
        """
        periodos = self.listar_periodos()

        assert periodos, (
            f"A tela {self.NOME_TELA} não exibiu nenhum documento. Verifique "
            "se o usuário de homologação ainda tem documentos publicados."
        )

        return sorted(
            periodos,
            key=type(self).interpretar_periodo,
            reverse=True,
        )

    def periodo_mais_recente(self) -> str:
        return self.periodos_do_mais_recente()[0]

    def _celula_do_periodo(self, periodo: str):
        encontrados = []

        for celula in self.driver.find_elements(*self._celula):
            try:
                texto = celula.find_element(*self._label_periodo).text
            except (NoSuchElementException, StaleElementReferenceException):
                continue

            encontrados.append((texto or "").strip())

            if (texto or "").strip() == periodo:
                return celula

        raise AssertionError(
            f"Período {periodo!r} não encontrado em {self.NOME_TELA}. "
            f"Exibidos: {encontrados}."
        )

    # === Documento ===
    def visualizar(self, periodo: str) -> VisualizadorDocumentoPage:
        """
        Abre o documento do período informado e confirma que o
        visualizador mostra esse mesmo período no título.
        """
        celula = self._celula_do_periodo(periodo)

        try:
            botao = celula.find_element(*self.BOTAO_VISUALIZAR)
        except NoSuchElementException as erro:
            raise AssertionError(
                f"O período {periodo!r} não tem o botão 'visualizar'."
            ) from erro

        botao.click()

        self._log_info(
            f"Visualização de {self.NOME_TELA} acionada",
            event="document_view_tapped",
            periodo=periodo,
        )

        visualizador = VisualizadorDocumentoPage(self.driver)

        assert visualizador.esta_aberto(timeout=self.LONG_TIMEOUT), (
            f"O documento de {periodo} não abriu: o visualizador "
            "(botão Salvar) não foi exibido."
        )

        titulo_confere = visualizador.exibe_titulo(
            periodo,
            timeout=self.SHORT_TIMEOUT,
        )

        assert titulo_confere, (
            f"O visualizador abriu, mas não mostra {periodo!r} no título."
        )

        return visualizador

    def voltar_do_visualizador(
        self,
        visualizador: VisualizadorDocumentoPage,
    ) -> None:
        """
        Fecha o documento e confirma o retorno à lista.
        """
        visualizador.voltar()

        assert self.esta_na_tela(timeout=self.LONG_TIMEOUT), (
            f"A lista de {self.NOME_TELA} não foi exibida após fechar o "
            "documento."
        )
