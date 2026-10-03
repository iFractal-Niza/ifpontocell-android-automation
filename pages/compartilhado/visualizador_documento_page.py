from pages.alertas import AlertaAppMixin
from pages.android_locators import android_pendente, android_text
from pages.base_page import BasePage


class VisualizadorDocumentoPage(AlertaAppMixin, BasePage):
    """
    Page: visualizador de documento por competência (ids "visualizar.*").

    Aberto pelo "visualizar" das listas de documentos
    (ListaDocumentosPage: Holerite, Informe de Rendimentos). Os rótulos
    de anterior/próximo ("ver o ponto do dia anterior") indicam que o
    componente também é usado no Espelho.

    O Holerite e o Informe são renderizados sem texto acessível
    (colaborador, valores): o que dá para validar é o período no título.
    O comprovante de registro de ponto (aba STATUS) tem o texto inteiro
    num TextView (texto()).
    """

    SCREEN_NAME = "visualizador_documento"

    # PENDENTE: ids do visualizador no Android (iOS: visualizar.*).
    BOTAO_ANTERIOR = android_pendente("visualizar_btnAnterior")
    BOTAO_PROXIMO = android_pendente("visualizar_btnProximo")
    BOTAO_SALVAR = android_pendente("visualizar_btnSalvar")
    BOTAO_COMPARTILHAR = android_pendente("visualizar_btnCompartilhar")
    BOTAO_VOLTAR = android_pendente("visualizar_btnVoltar")

    # Botão de texto "VOLTAR" ao lado da seta (no iOS, sem id técnico).
    # Fallback caso a seta não esteja disponível.
    BOTAO_VOLTAR_TEXTO = android_text("VOLTAR")

    # Texto do documento (comprovante do registro de ponto). No iOS, o
    # XCUIElementTypeTextView.
    TEXTO_DOCUMENTO = android_pendente("visualizar_texto")

    @staticmethod
    def _titulo(texto: str) -> tuple[str, str]:
        # O título não tem id próprio (no iOS): pelo texto ("Setembro
        # 2026").
        return android_text(texto)

    def esta_aberto(self, timeout: float | None = None) -> bool:
        """
        Reconhece o visualizador pelo botão Salvar, que é exclusivo dele.
        """
        is_visible = self._is_visible(self.BOTAO_SALVAR, timeout=timeout)

        self._log_info(
            "Verificação do visualizador de documento executada",
            event="document_viewer_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def exibe_titulo(
        self,
        texto: str,
        timeout: float | None = None,
    ) -> bool:
        is_visible = self._is_visible(
            self._titulo(texto),
            timeout=timeout,
        )

        self._log_info(
            "Título do documento verificado",
            event="document_viewer_title_checked",
            titulo=texto,
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def texto(self) -> str:
        """
        Texto acessível do documento, quando ele tem (comprovante de
        registro de ponto); "" quando não tem.
        """
        if not self._is_visible(
            self.TEXTO_DOCUMENTO, timeout=self.LONG_TIMEOUT
        ):
            return ""

        return (
            self._find(
                self.TEXTO_DOCUMENTO, element_name="texto_documento"
            ).text
            or ""
        )

    def voltar(self) -> None:
        """
        Fecha o visualizador. Quem chama valida a tela de origem.
        """
        self._click_with_fallback(
            self.BOTAO_VOLTAR,
            self.BOTAO_VOLTAR_TEXTO,
            primary_name="botao_voltar_visualizador",
            fallback_name="botao_voltar_visualizador_texto",
            timeout=self.DEFAULT_TIMEOUT,
        )

    def salvar(self) -> None:
        """
        Salva o documento e fecha o alerta de confirmação.
        """
        self._click(
            self.BOTAO_SALVAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_salvar_documento",
        )

        self.confirmar_alerta(
            "Arquivo salvo com sucesso.",
            acao="tocar em SALVAR",
        )
