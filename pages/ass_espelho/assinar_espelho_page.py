from time import monotonic, sleep

from selenium.common.exceptions import WebDriverException

from pages.alertas import AlertaAppMixin
from pages.android_locators import android_pendente
from pages.base_page import BasePage
from pages.navegacao import VoltarParaHomeMixin
from utils.periodo import extrair_intervalo


class AssinarEspelhoPage(AlertaAppMixin, VoltarParaHomeMixin, BasePage):
    """
    Page: tela "Assinar" do espelho (Impressão -> ASSINAR ESPELHO).

    Nome do colaborador, aceite ("Estou de acordo com o espelho
    referente ao período de: ...") e o botão ASSINAR ESPELHO, que só é
    habilitado com o aceite marcado. Assinar é irreversível no ambiente
    de teste (só excluindo e refazendo o fechamento).
    """

    SCREEN_NAME = "assinar_espelho"
    NOME_TELA = "Assinar"

    # PENDENTE: ids da tela no Android (iOS: assinar.*).
    BOTAO_ACEITE = android_pendente("assinar_btnAceiteCheckbox")

    # Texto do aceite. No iOS, value == "Selecionado" quando marcado; no
    # Android, PENDENTE: assumido o checked do próprio aceite.
    TEXTO_ACEITE = android_pendente("assinar_btnAceiteTexto")

    BOTAO_ASSINAR = android_pendente("assinar_btnAssinar")

    VALOR_ACEITE_MARCADO = "Selecionado"
    MENSAGEM_SUCESSO = "A sua assinatura foi realizada com sucesso!"
    TITULO_SUCESSO = "Assinatura"

    def esta_aberta(self, timeout: float | None = None) -> bool:
        return self._is_visible(self.TEXTO_ACEITE, timeout=timeout)

    def periodo_do_aceite(self) -> str:
        texto = self._find(
            self.TEXTO_ACEITE,
            element_name="texto_aceite",
        ).text

        return extrair_intervalo(texto)

    def aceite_marcado(self) -> bool:
        try:
            valor = self._find(
                self.TEXTO_ACEITE,
                element_name="texto_aceite",
            ).get_attribute("checked")
        except WebDriverException:
            return False

        return (valor or "").strip() == "true"

    def botao_assinar_habilitado(self) -> bool:
        return self._find(
            self.BOTAO_ASSINAR,
            element_name="botao_assinar_espelho",
        ).is_enabled()

    def tocar_assinar(self) -> None:
        """
        Toque real na posição do ASSINAR ESPELHO, mesmo desabilitado
        (o clique padrão espera o botão ficar clicável). Não confirma
        nada: quem chama verifica o efeito.
        """
        botao = self._find(
            self.BOTAO_ASSINAR,
            element_name="botao_assinar_espelho",
        )
        # mobile: tap do XCUITest -> clickGesture do UiAutomator2, que
        # também toca no centro do elemento mesmo desabilitado.
        self.driver.execute_script(
            "mobile: clickGesture",
            {"elementId": botao.id},
        )

    def assinatura_confirmada(self, timeout: float) -> bool:
        return self.alerta_visivel(self.MENSAGEM_SUCESSO, timeout=timeout)

    def marcar_aceite(self) -> None:
        self._click(
            self.BOTAO_ACEITE,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="checkbox_aceite",
        )

        assert self._aguardar(self.aceite_marcado), (
            "O aceite não ficou marcado após tocar no checkbox."
        )

    def assinar(self) -> None:
        """
        Assina o espelho (irreversível) e fecha o alerta de sucesso.
        """
        assert self.botao_assinar_habilitado(), (
            "ASSINAR ESPELHO está desabilitado; marque o aceite antes."
        )

        self._click(
            self.BOTAO_ASSINAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_assinar_espelho",
        )

        self.confirmar_alerta(
            self.MENSAGEM_SUCESSO,
            acao="tocar em ASSINAR ESPELHO",
            titulo=self.TITULO_SUCESSO,
        )

    def voltar(self) -> None:
        self._tocar_voltar()

    def _aguardar(self, condicao, timeout: float | None = None) -> bool:
        limite = monotonic() + (timeout or self.SHORT_TIMEOUT)

        while True:
            if condicao():
                return True

            if monotonic() >= limite:
                return False

            sleep(self.POLL_FREQUENCY)
