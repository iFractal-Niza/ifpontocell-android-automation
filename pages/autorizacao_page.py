"""Compatibilidade do fluxo de autorização após a migração para Android.

O projeto Android de referência não possui uma tela equivalente à autorização
iOS. A ativação continua sendo feita pela API no fluxo de primeiro acesso.
"""
from pages.android_locators import android_id
from pages.base_page import BasePage


class AutorizacaoPage(BasePage):
    SCREEN_NAME = "autorizacao"

    # PENDENTE apenas se a build Android atual voltar a exibir essa etapa.
    MARCADOR_AUTORIZACAO = android_id(
        "btn_confirmar_autorizacao", "deviceAuthorization.btnConfirmar"
    )

    def esta_na_tela_autorizacao(self, timeout=None) -> bool:
        return self._is_visible(
            self.MARCADOR_AUTORIZACAO,
            timeout=self.SHORT_TIMEOUT if timeout is None else timeout,
        )

    def validar_liberacao_com_retry(self, *_, **__) -> bool:
        return not self.esta_na_tela_autorizacao(timeout=self.OPTIONAL_POPUP_TIMEOUT)
