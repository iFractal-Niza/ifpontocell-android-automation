from time import sleep
from typing import Optional

from selenium.common.exceptions import WebDriverException

from pages.android_locators import android_id, android_text_contains
from pages.base_page import BasePage


class UnlockPage(BasePage):
    SCREEN_NAME = "unlock"

    PIN_TAP_INTERVAL = 0.12

    # === Locators Android confirmados no projeto de referência ===
    BOTAO_DIGITO_1 = android_id("number1")
    TELA_CRIAR_PIN = android_id("number1")
    TELA_UNLOCK = android_id("relative_first_access")

    # Compatibilidade com flows existentes: no Android a presença do teclado
    # numérico é o marcador estável disponível para criação/confirmação do PIN.
    TEXTO_CRIAR_PIN = BOTAO_DIGITO_1
    TEXTO_CONFIRMAR_PIN = BOTAO_DIGITO_1
    TEXTO_TELA_UNLOCK = TELA_UNLOCK

    # Popup não existe no projeto Android de referência; fallback textual.
    BOTAO_AGORA_NAO = android_text_contains("Agora não")

    @staticmethod
    def _validar_pin(pin: str) -> None:
        if not isinstance(pin, str):
            raise TypeError("O PIN deve ser informado como string.")
        if len(pin) != 4 or not pin.isdigit():
            raise ValueError("O PIN deve conter exatamente 4 dígitos numéricos.")

    @staticmethod
    def _locator_digito(numero: str) -> tuple[str, str]:
        return android_id(f"number{numero}")

    def tratar_popup_salvar_senha_se_existir(self) -> bool:
        return self._click_if_visible(
            self.BOTAO_AGORA_NAO,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
            element_name="agora_nao_salvar_senha",
        )

    def esta_na_tela_criar_pin(self, timeout: Optional[float] = None) -> bool:
        return self._is_visible(
            self.BOTAO_DIGITO_1,
            timeout=self.DEFAULT_TIMEOUT if timeout is None else timeout,
        )

    def validar_tela_criar_pin(self) -> bool:
        return self.esta_na_tela_criar_pin()

    def esta_na_tela_confirmacao_pin(self, timeout: Optional[float] = None) -> bool:
        # O projeto Android legado não expõe um locator exclusivo da etapa de
        # confirmação. O teclado numberN permanece presente nas duas etapas.
        return self._is_visible(
            self.BOTAO_DIGITO_1,
            timeout=self.DEFAULT_TIMEOUT if timeout is None else timeout,
        )

    def validar_tela_confirmacao_pin(self) -> bool:
        return self.esta_na_tela_confirmacao_pin()

    def esta_na_tela_unlock(self, timeout: Optional[float] = None) -> bool:
        timeout_resolvido = self.LONG_TIMEOUT if timeout is None else timeout
        return self._is_visible(self.TELA_UNLOCK, timeout=timeout_resolvido)

    def digitar_pin(self, pin: str) -> None:
        self._validar_pin(pin)
        for numero in pin:
            self._click(
                self._locator_digito(numero),
                timeout=self.DEFAULT_TIMEOUT,
                element_name=f"digito_pin_{numero}",
            )
            sleep(self.PIN_TAP_INTERVAL)

    def criar_pin(self, pin: str) -> None:
        assert self.esta_na_tela_criar_pin(
            timeout=self.SHORT_TIMEOUT
        ), "A tela de criação do PIN não foi exibida."
        self.digitar_pin(pin)

    def confirmar_pin(self, pin: str) -> None:
        # A confirmação usa o mesmo teclado Android; aguarda o componente
        # permanecer disponível após a primeira entrada antes de digitar.
        assert self.esta_na_tela_confirmacao_pin(
            timeout=self.LONG_TIMEOUT
        ), "O teclado de confirmação do PIN não foi exibido."
        self.digitar_pin(pin)

    def configurar_pin(self, pin: str) -> None:
        self._validar_pin(pin)
        self.criar_pin(pin)
        self.confirmar_pin(pin)

    def desbloquear_com_pin(self, pin: str) -> None:
        self._validar_pin(pin)
        assert self.esta_na_tela_unlock(), "A tela de desbloqueio não foi exibida."
        self.digitar_pin(pin)
