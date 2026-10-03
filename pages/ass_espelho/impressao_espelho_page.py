from pages.alertas import AlertaAppMixin
from pages.android_locators import android_pendente, android_text
from pages.ass_espelho.assinar_espelho_page import AssinarEspelhoPage
from pages.base_page import BasePage
from pages.navegacao import VoltarParaHomeMixin


class ImpressaoEspelhoPage(AlertaAppMixin, VoltarParaHomeMixin, BasePage):
    """
    Page: tela "Impressão" do espelho (Assinatura do Espelho -> expandir
    -> visualizar).

    Diferente do VisualizadorDocumentoPage do Holerite/Informe
    (visualizar.*): ids impressao.*. O botão ASSINAR ESPELHO mostra
    "ASSINADO" quando o mês já foi assinado. SALVAR depende de permissão
    do usuário no ifPonto. COMPARTILHAR não é coberto (share sheet do
    sistema).
    """

    SCREEN_NAME = "impressao_espelho"
    NOME_TELA = "Impressão"

    # PENDENTE: título por texto, como no iOS; botões sem id conhecido
    # no Android (iOS: impressao.*).
    TITULO = android_text("Impressão")
    BOTAO_ASSINAR = android_pendente("impressao_btnAssinar")
    BOTAO_SALVAR = android_pendente("impressao_btnSalvar")

    ROTULO_ASSINADO = "ASSINADO"

    @staticmethod
    def _competencia(competencia: str) -> tuple[str, str]:
        # O mês não tem id próprio (no iOS): pelo texto ("Agosto 2026").
        return android_text(competencia)

    def esta_aberta(
        self,
        competencia: str,
        timeout: float | None = None,
    ) -> bool:
        """Impressão aberta mostrando o mês informado."""
        return self._is_visible(self.TITULO, timeout=timeout) and (
            self._is_visible(
                self._competencia(competencia),
                timeout=self.SHORT_TIMEOUT,
            )
        )

    def assinado(self) -> bool:
        rotulo = self._find(
            self.BOTAO_ASSINAR,
            element_name="botao_assinar_impressao",
        ).text

        return (rotulo or "").strip() == self.ROTULO_ASSINADO

    def salvar_disponivel(self, timeout: float | None = None) -> bool:
        """
        SALVAR só aparece para usuário com permissão de salvar no ifPonto.
        """
        return self._is_visible(
            self.BOTAO_SALVAR,
            timeout=self.SHORT_TIMEOUT if timeout is None else timeout,
        )

    def salvar(self) -> None:
        self._click(
            self.BOTAO_SALVAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_salvar_impressao",
        )

        # Sem ponto final, diferente do "Arquivo salvo com sucesso." do
        # visualizador do Holerite/Informe.
        self.confirmar_alerta(
            "Arquivo salvo com sucesso",
            acao="tocar em SALVAR na Impressão do espelho",
        )

    def abrir_assinatura(self) -> AssinarEspelhoPage:
        assert not self.assinado(), (
            "O espelho já está assinado: a Impressão mostra ASSINADO."
        )

        self._click(
            self.BOTAO_ASSINAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_assinar_impressao",
        )

        assinar_page = AssinarEspelhoPage(self.driver)

        assert assinar_page.esta_aberta(timeout=self.LONG_TIMEOUT), (
            "A tela de assinatura não foi exibida após tocar em ASSINAR "
            "ESPELHO na Impressão."
        )

        return assinar_page

    def voltar(self) -> None:
        self._tocar_voltar()
