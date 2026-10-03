"""
Tela de autorização do aparelho (após criar o PIN, no fluxo original).

O projeto Android de referência não tem essa tela: o primeiro acesso
ativa o celular pela API (flows._ativar_celular_antes_unlock), e os
fluxos não a sondam (garantir_tela_login, no iOS, sim: cada sondagem
custaria 2s à toa). Mantida, com a mesma API do iOS, para quando a
build Android voltar a exibi-la.
"""

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC

from pages.android_locators import (
    android_id,
    android_text,
    android_text_contains,
)
from pages.base_page import BasePage


class AutorizacaoPage(BasePage):
    SCREEN_NAME = "autorizacao"

    # === Tela de autorização ===
    # PENDENTE: só se a build Android atual voltar a exibir essa etapa.
    BOTAO_AUTORIZACAO_REALIZADA = android_id(
        "btn_confirmar_autorizacao",
        "deviceAuthorization.btnConfirmar",
    )

    # === Modal de bloqueio ===
    MODAL_APARELHO_INATIVO = android_text_contains("Aparelho inativo")
    BOTAO_OK_MODAL = android_text("OK")

    # === Estado da tela de autorização ===
    def esta_na_tela_autorizacao(
        self,
        timeout: float | None = None,
    ) -> bool:
        """
        Verifica a presença da tela de autorização.

        O botão pode estar presente na árvore enquanto não visível
        durante a atualização da tela (visto no iOS). Por isso, a
        identificação utiliza presença em vez de visibilidade.
        """
        timeout_resolvido = self.LONG_TIMEOUT if timeout is None else timeout

        try:
            self._wait(timeout_resolvido).until(
                EC.presence_of_element_located(
                    self.BOTAO_AUTORIZACAO_REALIZADA
                )
            )

            is_present = True

        except TimeoutException:
            is_present = False

        self._log_info(
            "Validação da tela de autorização executada",
            event="authorization_screen_checked",
            status=("present" if is_present else "not_present"),
        )

        return is_present

    def validar_tela_autorizacao(
        self,
        timeout: float | None = None,
    ) -> bool:
        return self.esta_na_tela_autorizacao(
            timeout=timeout,
        )

    # === Ações ===
    def clicar_autorizacao_realizada(
        self,
        timeout: float | None = None,
    ) -> None:
        """
        Aciona o botão principal de autorização realizada.

        Utiliza mobile: clickGesture pelo elementId: toca mesmo com o
        botão presente na árvore e ainda não marcado como visível.
        """
        timeout_resolvido = (
            self.DEFAULT_TIMEOUT if timeout is None else timeout
        )

        try:
            elemento = self._wait(timeout_resolvido).until(
                EC.presence_of_element_located(
                    self.BOTAO_AUTORIZACAO_REALIZADA
                )
            )

        except TimeoutException as error:
            raise TimeoutException(
                "botao_autorizacao_realizada não foi encontrado "
                f"em {timeout_resolvido}s. "
                f"Locator: {self.BOTAO_AUTORIZACAO_REALIZADA}"
            ) from error

        self.driver.execute_script(
            "mobile: clickGesture",
            {"elementId": elemento.id},
        )

        self._log_info(
            "Confirmação de autorização executada",
            event="authorization_confirmation_clicked",
            interaction="mobile_click_gesture",
        )

    def clicar_ok_modal(
        self,
        timeout: float | None = None,
    ) -> None:
        """
        Fecha o modal de aparelho inativo.
        """
        self._click(
            self.BOTAO_OK_MODAL,
            timeout=(self.DEFAULT_TIMEOUT if timeout is None else timeout),
            element_name="botao_ok_modal_aparelho_inativo",
        )

        self._log_info(
            "Modal de aparelho inativo fechado",
            event="inactive_device_modal_closed",
        )

    # === Estado do modal ===
    def exibe_modal_aparelho_inativo(
        self,
        timeout: float | None = None,
    ) -> bool:
        """
        Verifica se o modal de aparelho inativo está visível.
        """
        is_visible = self._is_visible(
            self.MODAL_APARELHO_INATIVO,
            timeout=(self.SHORT_TIMEOUT if timeout is None else timeout),
        )

        self._log_info(
            "Visibilidade do modal de aparelho inativo verificada",
            event="inactive_device_modal_checked",
            status=("visible" if is_visible else "not_visible"),
        )

        return is_visible

    def _aguardar_modal_visivel(
        self,
        timeout: float,
    ) -> bool:
        """
        Aguarda a exibição do modal de aparelho inativo.
        """
        try:
            self._wait(timeout).until(
                EC.visibility_of_element_located(self.MODAL_APARELHO_INATIVO)
            )
            return True

        except TimeoutException:
            return False

    def _aguardar_modal_invisivel(
        self,
        timeout: float,
    ) -> bool:
        """
        Aguarda o fechamento do modal de aparelho inativo.
        """
        try:
            self._wait(timeout).until(
                EC.invisibility_of_element_located(self.MODAL_APARELHO_INATIVO)
            )
            return True

        except TimeoutException:
            return False

    # === Retry de bloqueio ===
    def validar_bloqueio_com_retry(
        self,
        tentativas: int = 5,
        intervalo: float = 2,
        timeout_modal: float = 3,
    ) -> bool:
        """
        Valida o bloqueio do aparelho com novas tentativas.

        Em cada tentativa, aciona a autorização e verifica
        a exibição do modal de aparelho inativo.
        """
        for tentativa in range(
            1,
            tentativas + 1,
        ):
            self._log_info(
                "Iniciando tentativa de validação do bloqueio",
                event="retry_block_validation",
                attempt=tentativa,
            )

            self.clicar_autorizacao_realizada()

            if self.exibe_modal_aparelho_inativo(
                timeout=timeout_modal,
            ):
                self._log_info(
                    "Bloqueio do aparelho validado",
                    event="block_validation_success",
                    attempt=tentativa,
                )
                return True

            self._log_warning(
                "Modal de bloqueio ainda não exibido; "
                "aguardando nova tentativa",
                event="block_validation_retry",
                attempt=tentativa,
                intervalo=intervalo,
            )

            if self._aguardar_modal_visivel(
                timeout=intervalo,
            ):
                self._log_info(
                    "Bloqueio validado durante a espera entre tentativas",
                    event="block_validation_success_during_wait",
                    attempt=tentativa,
                )
                return True

        self._log_error(
            "Não foi possível validar o bloqueio do aparelho",
            event="block_validation_failed",
            total_attempts=tentativas,
        )

        return False

    # === Retry de liberação ===
    def validar_liberacao_com_retry(
        self,
        tentativas: int = 5,
        intervalo: float = 2,
        timeout_modal: float = 3,
    ) -> bool:
        """
        Valida a liberação do aparelho com novas tentativas.

        Em cada tentativa, aciona a autorização e verifica
        a ausência do modal de aparelho inativo. Caso o modal
        seja exibido, fecha-o antes da próxima tentativa.
        """
        for tentativa in range(
            1,
            tentativas + 1,
        ):
            self._log_info(
                "Iniciando tentativa de validação da liberação",
                event="retry_release_validation",
                attempt=tentativa,
            )

            self.clicar_autorizacao_realizada()

            if self.exibe_modal_aparelho_inativo(
                timeout=timeout_modal,
            ):
                self._log_warning(
                    "O aparelho permanece bloqueado; "
                    "aguardando nova tentativa",
                    event="release_validation_retry",
                    attempt=tentativa,
                    intervalo=intervalo,
                )

                self.clicar_ok_modal()

                self._aguardar_modal_invisivel(
                    timeout=intervalo,
                )

                continue

            # Pós-condição positiva: a ausência do modal de bloqueio
            # não prova que a autorização aconteceu. Se o toque não
            # chegou no botão, o app não reage e nenhum modal aparece
            # — o que antes era lido como sucesso. A prova é a tela
            # de autorização ter saído.
            if self._wait_for_absence(
                self.BOTAO_AUTORIZACAO_REALIZADA,
                timeout=intervalo,
            ):
                self._log_info(
                    "Liberação do aparelho validada",
                    event="release_validation_success",
                    attempt=tentativa,
                )
                return True

            self._log_warning(
                "O toque em AUTORIZAÇÃO REALIZADA não teve efeito: "
                "nem modal de bloqueio, nem saída da tela",
                event="authorization_tap_without_effect",
                attempt=tentativa,
            )

        self._log_error(
            "Não foi possível validar a liberação do aparelho",
            event="release_validation_failed",
            total_attempts=tentativas,
        )

        return False
