from collections.abc import Callable
from time import sleep

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.android_locators import android_id, android_text_contains
from pages.base_page import BasePage


class UnlockPage(BasePage):
    SCREEN_NAME = "unlock"

    # === Configuração do PIN de automação ===
    # Intervalo menor que o do iOS (0,5s): no UiAutomator2 o teclado
    # numberN não é recriado a cada dígito.
    PIN_TAP_INTERVAL = 0.12
    PIN_MIN_TAPS = 4
    PIN_MAX_TAPS = 6
    PIN_TRANSITION_TIMEOUT = 2

    # === Popup de salvar senha ===
    # Não existe no projeto Android de referência; fallback textual.
    BOTAO_AGORA_NAO = android_text_contains("Agora não")

    # === Criação e confirmação do PIN ===
    # Confirmado no Inspector: teclado numberN; a instrução (text_instrucao)
    # diz a etapa. "digitos" sem acento, como o app exibe.
    BOTAO_DIGITO_1 = android_id("number1")
    TEXTO_CRIAR_PIN = android_text_contains("Crie uma senha de 4 digitos")
    TELA_CRIAR_PIN = TEXTO_CRIAR_PIN

    # Confirmação (Inspector): "Entre novamente para confirmar\na senha de
    # acesso rápido criada." Diferente do iOS ("Repita a senha...") e do
    # desbloqueio ("Entre com sua senha").
    TEXTO_CONFIRMAR_PIN = android_text_contains(
        "Entre novamente para confirmar"
    )

    # === Desbloqueio ===
    # Confirmado no Inspector: título "Senha de Acesso Rápido" e
    # instrução (text_instrucao) "Entre com sua senha", como no iOS. Pela
    # instrução: o contêiner (relative_first_access) é o mesmo do
    # boas-vindas e da criação do PIN.
    TEXTO_TELA_UNLOCK = android_text_contains("Entre com sua senha")

    # === Popup de salvar senha ===
    def popup_salvar_senha_esta_visivel(self) -> bool:
        is_visible = self._is_visible(
            self.BOTAO_AGORA_NAO,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
        )

        self._log_info(
            "Verificação do popup de salvar senha executada",
            event="save_password_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def clicar_agora_nao(self) -> None:
        self._click(
            self.BOTAO_AGORA_NAO,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_agora_nao",
        )

    def tratar_popup_salvar_senha_se_existir(self) -> bool:
        return self._handle_optional_popup(
            check_method=self.popup_salvar_senha_esta_visivel,
            action_method=self.clicar_agora_nao,
            popup_name="popup_salvar_senha",
        )

    # === Helpers de estado ===
    # _esta_visivel_imediatamente vem de BasePage.

    def _aguardar_condicao(
        self,
        condicao: Callable[[], bool],
        timeout: float,
    ) -> bool:
        try:
            WebDriverWait(
                self.driver,
                timeout,
                poll_frequency=0.2,
            ).until(lambda _: condicao())
            return True

        except TimeoutException:
            return False

    # === Validações das telas ===
    def esta_na_tela_criar_pin(
        self,
        timeout: float | None = None,
    ) -> bool:
        timeout_resolvido = (
            self.DEFAULT_TIMEOUT if timeout is None else timeout
        )

        is_visible = self._is_visible(
            self.TEXTO_CRIAR_PIN,
            timeout=timeout_resolvido,
        )

        if not is_visible:
            navigation_bar_presente = bool(
                self.driver.find_elements(
                    *self.TELA_CRIAR_PIN,
                )
            )

            teclado_presente = bool(
                self.driver.find_elements(
                    *self.BOTAO_DIGITO_1,
                )
            )

            is_visible = navigation_bar_presente and teclado_presente

        self._log_info(
            "Validação da tela de criação de PIN executada",
            event="create_pin_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_tela_criar_pin(self) -> bool:
        return self.esta_na_tela_criar_pin()

    def esta_na_tela_confirmacao_pin(
        self,
        timeout: float | None = None,
    ) -> bool:
        timeout_resolvido = (
            self.DEFAULT_TIMEOUT if timeout is None else timeout
        )

        is_visible = self._is_visible(
            self.TEXTO_CONFIRMAR_PIN,
            timeout=timeout_resolvido,
        )

        self._log_info(
            "Validação da tela de confirmação de PIN executada",
            event="confirm_pin_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_tela_confirmacao_pin(self) -> bool:
        return self.esta_na_tela_confirmacao_pin()

    def esta_na_tela_unlock(
        self,
        timeout: float | None = None,
    ) -> bool:
        timeout_resolvido = self.LONG_TIMEOUT if timeout is None else timeout

        is_visible = self._is_visible(
            self.TEXTO_TELA_UNLOCK,
            timeout=timeout_resolvido,
        )

        self._log_info(
            "Validação da tela de desbloqueio executada",
            event="unlock_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def aguardar_pronto_para_confirmar_pin(self) -> None:
        if not self._aguardar_condicao(
            condicao=lambda: self._esta_visivel_imediatamente(
                self.TEXTO_CONFIRMAR_PIN,
            ),
            timeout=self.LONG_TIMEOUT,
        ):
            raise AssertionError(
                "A tela de confirmação do PIN não foi exibida."
            )

    # === Validação do PIN ===
    @staticmethod
    def _validar_pin(pin: str) -> None:
        if not isinstance(pin, str):
            raise TypeError("O PIN deve ser informado como string.")

        if len(pin) != 4 or not pin.isdigit():
            raise ValueError(
                "O PIN deve conter exatamente 4 dígitos numéricos."
            )

        if len(set(pin)) != 1:
            raise ValueError(
                "O PIN de automação deve repetir o mesmo dígito. "
                'Configure APP_PIN: "1111" no env.<device>.yaml.'
            )

    @staticmethod
    def _locator_digito(
        numero: str,
    ) -> tuple[str, str]:
        return android_id(f"number{numero}")

    # === Interação com teclado do PIN ===
    def _clicar_digito_pin(
        self,
        numero: str,
        tentativa: int,
        etapa: str,
    ) -> None:
        """
        Obtém uma referência nova antes de cada clique.

        Não reutiliza o WebElement porque a árvore pode ser atualizada
        após o preenchimento de cada indicador do PIN (visto no iOS).
        """
        locator = self._locator_digito(numero)

        for tentativa_elemento in range(1, 3):
            try:
                elemento = WebDriverWait(
                    self.driver,
                    self.DEFAULT_TIMEOUT,
                    poll_frequency=0.2,
                ).until(EC.element_to_be_clickable(locator))

                elemento.click()

                self._log_info(
                    "Dígito do PIN informado",
                    event="pin_digit_tapped",
                    step=etapa,
                    tap_attempt=tentativa,
                    element_attempt=tentativa_elemento,
                )

                sleep(self.PIN_TAP_INTERVAL)
                return

            except (
                StaleElementReferenceException,
                WebDriverException,
            ):
                if tentativa_elemento == 2:
                    raise

                sleep(self.PIN_TAP_INTERVAL)

    def _digitar_ate_transicao(
        self,
        pin: str,
        etapa: str,
        transicao_concluida: Callable[[], bool],
        mensagem_erro: str,
    ) -> None:
        """
        Informa o mesmo dígito até que a tela de destino seja detectada.

        Executa no mínimo quatro toques. Caso algum toque seja perdido
        pelo componente, permite até dois toques adicionais.
        """
        self._validar_pin(pin)
        numero = pin[0]

        self._log_info(
            "Iniciando digitação do PIN",
            event="pin_typing_started",
            step=etapa,
            pin_length=len(pin),
        )

        for tentativa in range(
            1,
            self.PIN_MAX_TAPS + 1,
        ):
            self._clicar_digito_pin(
                numero=numero,
                tentativa=tentativa,
                etapa=etapa,
            )

            if tentativa < self.PIN_MIN_TAPS:
                continue

            if self._aguardar_condicao(
                condicao=transicao_concluida,
                timeout=self.PIN_TRANSITION_TIMEOUT,
            ):
                self._log_info(
                    "Digitação do PIN concluída",
                    event="pin_typing_finished",
                    step=etapa,
                    taps=tentativa,
                )
                return

            if tentativa < self.PIN_MAX_TAPS:
                self._log_info(
                    "Transição do PIN ainda não ocorreu",
                    event="pin_transition_retry",
                    step=etapa,
                    taps=tentativa,
                )

        raise AssertionError(mensagem_erro)

    def digitar_pin_ate(
        self,
        pin: str,
        etapa: str,
        transicao_concluida: Callable[[], bool],
        mensagem_erro: str,
    ) -> None:
        """
        Informa o PIN no teclado numérico até a tela mudar (mesma
        digitação robusta do desbloqueio). Para outras telas com o mesmo
        teclado, como Alterar Senha.
        """
        self._digitar_ate_transicao(
            pin=pin,
            etapa=etapa,
            transicao_concluida=transicao_concluida,
            mensagem_erro=mensagem_erro,
        )

    def digitar_pin(self, pin: str) -> None:
        """
        Método mantido para compatibilidade.

        Executa quatro cliques com nova referência para cada interação.
        """
        self._validar_pin(pin)
        numero = pin[0]

        for tentativa in range(
            1,
            self.PIN_MIN_TAPS + 1,
        ):
            self._clicar_digito_pin(
                numero=numero,
                tentativa=tentativa,
                etapa="digitacao",
            )

    # === Criação do PIN ===
    def criar_pin(self, pin: str) -> None:
        assert self.esta_na_tela_criar_pin(
            timeout=self.SHORT_TIMEOUT,
        ), "A tela de criação do PIN não foi exibida."

        self._digitar_ate_transicao(
            pin=pin,
            etapa="criacao",
            transicao_concluida=lambda: self._esta_visivel_imediatamente(
                self.TEXTO_CONFIRMAR_PIN,
            ),
            mensagem_erro=(
                "A tela de confirmação do PIN não foi exibida "
                "após informar o PIN."
            ),
        )

    # === Confirmação do PIN ===
    def confirmar_pin(self, pin: str) -> None:
        assert self.esta_na_tela_confirmacao_pin(
            timeout=self.SHORT_TIMEOUT,
        ), "A tela de confirmação do PIN não está visível."

        self._digitar_ate_transicao(
            pin=pin,
            etapa="confirmacao",
            transicao_concluida=lambda: (
                not self._esta_visivel_imediatamente(
                    self.TEXTO_CONFIRMAR_PIN,
                )
            ),
            mensagem_erro=(
                "A confirmação do PIN não foi concluída após informar o PIN."
            ),
        )

    # === Configuração do PIN ===
    def configurar_pin(self, pin: str) -> None:
        self._validar_pin(pin)

        self._log_info(
            "Iniciando configuração de PIN",
            event="pin_configuration_started",
            pin_length=len(pin),
        )

        self.criar_pin(pin)
        self.confirmar_pin(pin)

        self._log_info(
            "Configuração de PIN finalizada",
            event="pin_configuration_finished",
            pin_length=len(pin),
        )

    # === PIN recusado ===
    def pin_foi_recusado(self, pin: str) -> bool:
        """
        Digita o PIN (quatro toques) e diz se o app continuou pedindo o
        PIN. Errar não bloqueia: os dígitos tremem e o app pede de novo.
        """
        self.digitar_pin(pin)
        sleep(self.PIN_TRANSITION_TIMEOUT)

        return self.esta_na_tela_unlock(timeout=self.SHORT_TIMEOUT)

    # === Desbloqueio com PIN ===
    def desbloquear_com_pin(self, pin: str) -> None:
        self._validar_pin(pin)

        assert self.esta_na_tela_unlock(), (
            "A tela de desbloqueio não foi exibida."
        )

        self._digitar_ate_transicao(
            pin=pin,
            etapa="desbloqueio",
            transicao_concluida=lambda: (
                not self._esta_visivel_imediatamente(
                    self.TEXTO_TELA_UNLOCK,
                )
            ),
            mensagem_erro=(
                "O desbloqueio não foi concluído após informar o PIN."
            ),
        )
