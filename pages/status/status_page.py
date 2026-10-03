from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

from pages.android_locators import (
    android_id,
    android_id_prefixo,
    android_pendente,
)
from pages.base_page import BasePage
from pages.home_page import HomePage
from utils.status import MarcacaoStatus, ler_id_marcacao, mais_recente
from utils.texto import normalizar_texto


class StatusPage(BasePage):
    """
    Page: aba STATUS (barra de baixo).

    Lista as marcações feitas por este app desde o primeiro acesso (o
    Zerar Dados apaga a lista). Cada marcação (status.cellMarcacao_<dia>_
    <código>) traz data, hora, código, status ("Sincronizado"), o
    progresso do envio e o botão COMPROVANTE, que abre o comprovante no
    visualizador de documento (VisualizadorDocumentoPage).

    PENDENTE (Android): no iOS a data e o código da marcação vêm do nome
    da célula (status.cellMarcacao_<dia>_<código>, utils.status). No
    Android, ids de item costumam ser fixos: com o XML da aba, a leitura
    da marcação pode precisar vir dos textos da célula
    (PENDENCIAS_LOCATORS_ANDROID.md).
    """

    SCREEN_NAME = "status"

    # Confirmado no Inspector (barra de baixo da Home).
    ABA_STATUS = android_id("status")
    ABA_PONTO = HomePage.ABA_PONTO

    # PENDENTE: ids da aba no Android (iOS: status.tblMarcacoes,
    # status.cellMarcacao_*, status.lblStatus, status.prgSincronizacao,
    # status.btnComprovante).
    TABELA = android_pendente("status_lista")
    PREFIXO_CELULA = "PENDENTE_status_marcacao"
    CELULAS = android_id_prefixo(PREFIXO_CELULA)

    # Dentro da célula da marcação.
    STATUS = android_pendente("status_lblStatus")
    PROGRESSO = android_pendente("status_prgSincronizacao")
    BOTAO_COMPROVANTE = android_pendente("status_btnComprovante")
    TEXTOS = (AppiumBy.CLASS_NAME, "android.widget.TextView")

    SINCRONIZADO = "Sincronizado"

    # === Acesso ===
    def acessar(self) -> None:
        self._click(
            self.ABA_STATUS,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="aba_status",
        )

        assert self.esta_aberta(timeout=self.LONG_TIMEOUT), (
            "A aba STATUS não foi exibida após tocar em STATUS."
        )

    def esta_aberta(self, timeout: float | None = None) -> bool:
        return self._is_visible(self.TABELA, timeout=timeout)

    def voltar_para_ponto(self) -> HomePage:
        self._click(
            self.ABA_PONTO,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="aba_ponto",
        )

        home = HomePage(self.driver)

        assert home.esta_na_home(timeout=home.LONG_TIMEOUT), (
            "A Home não foi exibida após tocar em PONTO na aba STATUS."
        )

        return home

    # === Marcações ===
    def marcacoes(self) -> list[MarcacaoStatus]:
        marcacoes = []

        try:
            celulas = self.driver.find_elements(*self.CELULAS)
        except WebDriverException:
            return []

        for celula in celulas:
            try:
                # No iOS, o name da célula; no Android, o resource-id.
                marcacao = ler_id_marcacao(celula.get_attribute("resource-id"))
            except (StaleElementReferenceException, WebDriverException):
                continue

            if marcacao:
                marcacoes.append(marcacao)

        return marcacoes

    def marcacao_mais_recente(self) -> MarcacaoStatus | None:
        return mais_recente(self.marcacoes())

    def _celula(self, marcacao: MarcacaoStatus):
        return self.driver.find_element(*android_id(marcacao.id))

    def textos(self, marcacao: MarcacaoStatus) -> list[str]:
        """Textos da célula: rótulos (Data, Hora...) e valores, na ordem."""
        return [
            normalizar_texto(texto.text)
            for texto in self._celula(marcacao).find_elements(*self.TEXTOS)
        ]

    def status(self, marcacao: MarcacaoStatus) -> str:
        try:
            return normalizar_texto(
                self._celula(marcacao).find_element(*self.STATUS).text
            )
        except (NoSuchElementException, WebDriverException):
            return ""

    def progresso(self, marcacao: MarcacaoStatus) -> str:
        try:
            return (
                self._celula(marcacao).find_element(*self.PROGRESSO).text or ""
            )
        except (NoSuchElementException, WebDriverException):
            return ""

    def aguardar_sincronizada(
        self, marcacao: MarcacaoStatus, timeout: float
    ) -> str:
        """
        Espera o status "Sincronizado" (o envio pode levar uns segundos);
        devolve o último status lido.
        """
        lido = ""

        def sincronizada(_) -> bool:
            nonlocal lido
            lido = self.status(marcacao)
            return lido == self.SINCRONIZADO

        try:
            self._wait(timeout).until(sincronizada)
        except TimeoutException:
            pass

        return lido

    def abrir_comprovante(self, marcacao: MarcacaoStatus) -> None:
        self._celula(marcacao).find_element(*self.BOTAO_COMPROVANTE).click()

        self._log_info(
            "Comprovante da marcação aberto",
            event="status_receipt_opened",
            marcacao=marcacao.id,
        )
