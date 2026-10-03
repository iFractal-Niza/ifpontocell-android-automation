from time import monotonic, sleep
from typing import Callable, Optional

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    InvalidArgumentException,
    NoAlertPresentException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.timeouts import (
    DEFAULT_TIMEOUT,
    LONG_TIMEOUT,
    MAX_TIMEOUT,
    OPTIONAL_POPUP_TIMEOUT,
    SHORT_TIMEOUT,
)
from utils.logger import get_logger


logger = get_logger(__name__)


class BasePage:
    SCREEN_NAME = "base"

    SHORT_TIMEOUT = SHORT_TIMEOUT
    DEFAULT_TIMEOUT = DEFAULT_TIMEOUT
    LONG_TIMEOUT = LONG_TIMEOUT
    MAX_TIMEOUT = MAX_TIMEOUT
    OPTIONAL_POPUP_TIMEOUT = OPTIONAL_POPUP_TIMEOUT

    POLL_FREQUENCY = 0.2

    # === Inicialização ===
    def __init__(
        self,
        driver,
        timeout: Optional[int] = None,
    ):
        """
        Inicializa o Page Object com o driver e o timeout padrão.

        Quando nenhum timeout é informado, utiliza o valor definido
        em DEFAULT_TIMEOUT.
        """
        self.driver = driver
        self.timeout = (
            self.DEFAULT_TIMEOUT
            if timeout is None
            else timeout
        )

        self._log_info(
            "Página inicializada",
            event="page_initialized",
            timeout=self.timeout,
        )

    # === Logs ===
    def _log_info(
        self,
        message: str,
        **extra,
    ) -> None:
        """Registra uma mensagem informativa com o contexto da tela."""
        logger.info(
            message,
            extra={
                "screen": self.SCREEN_NAME,
                **extra,
            },
        )

    def _log_warning(
        self,
        message: str,
        **extra,
    ) -> None:
        """Registra um alerta com o contexto da tela."""
        logger.warning(
            message,
            extra={
                "screen": self.SCREEN_NAME,
                **extra,
            },
        )

    def _log_error(
        self,
        message: str,
        **extra,
    ) -> None:
        """Registra um erro com o contexto da tela."""
        logger.error(
            message,
            extra={
                "screen": self.SCREEN_NAME,
                **extra,
            },
        )

    # === Timeouts e esperas ===
    def _resolve_timeout(
        self,
        timeout: Optional[int] = None,
    ) -> int:
        """
        Resolve o timeout efetivo da operação.

        Impede valores negativos e limita o timeout ao máximo
        configurado para evitar esperas excessivas.
        """
        effective_timeout = (
            self.timeout
            if timeout is None
            else timeout
        )

        if effective_timeout < 0:
            raise ValueError(
                "O timeout não pode ser negativo."
            )

        if effective_timeout > self.MAX_TIMEOUT:
            self._log_warning(
                "Timeout limitado ao valor máximo configurado",
                event="timeout_clamped",
                requested_timeout=effective_timeout,
                max_timeout=self.MAX_TIMEOUT,
            )
            return self.MAX_TIMEOUT

        return effective_timeout

    def _wait(
        self,
        timeout: Optional[int] = None,
    ) -> WebDriverWait:
        """
        Cria uma espera explícita utilizando o timeout resolvido.
        """
        return WebDriverWait(
            self.driver,
            self._resolve_timeout(timeout),
            poll_frequency=self.POLL_FREQUENCY,
        )

    # === Suporte a interações nativas ===
    def _hide_keyboard_if_possible(self) -> bool:
        """
        Tenta ocultar o teclado sem interromper o fluxo em caso de falha.
        """
        try:
            self.driver.hide_keyboard()

            self._log_info(
                "Teclado ocultado",
                event="keyboard_hidden",
            )
            return True

        except WebDriverException:
            return False

    def _try_accept_ios_alert(self) -> bool:
        """
        Tenta aceitar um alerta nativo exibido pelo app.
        """
        try:
            self.driver.switch_to.alert.accept()

            self._log_info(
                "Alerta nativo aceito",
                event="native_alert_accepted",
            )
            return True

        except (
            NoAlertPresentException,
            WebDriverException,
        ):
            return False

    def _try_dismiss_ios_alert(self) -> bool:
        """
        Tenta dispensar um alerta nativo exibido pelo app.
        """
        try:
            self.driver.switch_to.alert.dismiss()

            self._log_info(
                "Alerta nativo dispensado",
                event="native_alert_dismissed",
            )
            return True

        except (
            NoAlertPresentException,
            WebDriverException,
        ):
            return False

    def _try_resolve_ios_alert(self) -> bool:
        """
        Tenta resolver um alerta nativo aceitando-o ou dispensando-o.
        """
        return (
            self._try_accept_ios_alert()
            or self._try_dismiss_ios_alert()
        )

    def _force_tap_element(
        self,
        element,
        element_name: str,
    ) -> None:
        """
        Executa um tap no centro do elemento como fallback de clique.
        """
        location = element.location
        size = element.size

        x = int(
            location["x"]
            + (size["width"] / 2)
        )
        y = int(
            location["y"]
            + (size["height"] / 2)
        )

        self._log_warning(
            "Executando tap forçado no elemento",
            event="element_force_tap_started",
            element=element_name,
            x=x,
            y=y,
        )

        self.driver.execute_script(
            "mobile: clickGesture",
            {"x": x, "y": y},
        )

        self._log_info(
            "Tap forçado executado",
            event="element_force_tap_finished",
            element=element_name,
        )

    # === Estado dos elementos ===
    def _is_visible(
        self,
        locator,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Verifica se o elemento fica visível dentro do timeout.
        """
        try:
            self._wait(timeout).until(
                EC.visibility_of_element_located(
                    locator
                )
            )
            return True

        except TimeoutException:
            return False

    def _exists(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ) -> bool:
        """
        Verifica se o elemento está presente na hierarquia da tela.
        """
        try:
            self._wait(timeout).until(
                EC.presence_of_element_located(
                    locator
                )
            )
            return True

        except TimeoutException:
            self._log_info(
                "Elemento não encontrado",
                event="element_not_present",
                element=element_name,
            )
            return False

    # === Esperas de elementos ===
    def _wait_for_visible(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ):
        """
        Aguarda o elemento ficar visível e retorna sua referência.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        self._log_info(
            "Aguardando visibilidade do elemento",
            event="wait_visible_started",
            element=element_name,
            timeout=effective_timeout,
        )

        try:
            element = self._wait(
                effective_timeout
            ).until(
                EC.visibility_of_element_located(
                    locator
                ),
                message=(
                    f"{element_name} não ficou visível em "
                    f"{effective_timeout}s. Locator: {locator}"
                ),
            )

        except TimeoutException:
            self._log_error(
                "Elemento não ficou visível",
                event="wait_visible_timeout",
                element=element_name,
                locator=str(locator),
                timeout=effective_timeout,
            )
            raise

        self._log_info(
            "Elemento visível",
            event="wait_visible_finished",
            element=element_name,
        )

        return element

    def _wait_for_clickable(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ):
        """
        Aguarda o elemento ficar clicável e retorna sua referência.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        self._log_info(
            "Aguardando disponibilidade do elemento para clique",
            event="wait_clickable_started",
            element=element_name,
            timeout=effective_timeout,
        )

        try:
            element = self._wait(
                effective_timeout
            ).until(
                EC.element_to_be_clickable(
                    locator
                ),
                message=(
                    f"{element_name} não ficou clicável em "
                    f"{effective_timeout}s. Locator: {locator}"
                ),
            )

        except TimeoutException:
            self._log_error(
                "Elemento não ficou disponível para clique",
                event="wait_clickable_timeout",
                element=element_name,
                locator=str(locator),
                timeout=effective_timeout,
            )
            raise

        self._log_info(
            "Elemento disponível para clique",
            event="wait_clickable_finished",
            element=element_name,
        )

        return element

    # === Busca de elementos ===
    def _find(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ):
        """
        Aguarda a presença do elemento e retorna sua referência.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        self._log_info(
            "Buscando elemento",
            event="element_find_started",
            element=element_name,
            timeout=effective_timeout,
        )

        try:
            element = self._wait(
                effective_timeout
            ).until(
                EC.presence_of_element_located(
                    locator
                ),
                message=(
                    f"{element_name} não foi encontrado em "
                    f"{effective_timeout}s. Locator: {locator}"
                ),
            )

        except TimeoutException:
            self._log_error(
                "Elemento não encontrado",
                event="element_find_timeout",
                element=element_name,
                locator=str(locator),
                timeout=effective_timeout,
            )
            raise

        self._log_info(
            "Elemento encontrado",
            event="element_found",
            element=element_name,
        )

        return element

    # === Interações ===
    def _click_with_retry(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ) -> None:
        """
        Executa o clique com estratégias progressivas de fallback.

        Ordem:
        1. Clique padrão no elemento clicável.
        2. Tratamento de possível alerta nativo.
        3. Nova tentativa no elemento visível.
        4. Tap forçado no centro do elemento.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )
        initial_error: Optional[Exception] = None

        self._hide_keyboard_if_possible()

        try:
            element = self._wait_for_clickable(
                locator,
                timeout=effective_timeout,
                element_name=element_name,
            )
            element.click()
            return

        except (
            TimeoutException,
            WebDriverException,
        ) as error:
            initial_error = error

            self._log_warning(
                "Falha ao realizar o clique padrão",
                event="element_click_default_failed",
                element=element_name,
            )

        alert_resolved = (
            self._try_resolve_ios_alert()
        )

        if alert_resolved:
            self._log_info(
                "Alerta nativo tratado antes da nova tentativa",
                event="element_click_ios_alert_resolved",
                element=element_name,
            )

        try:
            element = self._wait_for_visible(
                locator,
                timeout=self.SHORT_TIMEOUT,
                element_name=element_name,
            )

            try:
                element.click()
                return

            except WebDriverException:
                self._force_tap_element(
                    element=element,
                    element_name=element_name,
                )
                return

        except (
            TimeoutException,
            WebDriverException,
        ) as final_error:
            self._log_error(
                "Falha ao clicar no elemento",
                event="element_click_failed",
                element=element_name,
                locator=str(locator),
            )

            raise final_error from initial_error

    def _click(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ) -> None:
        """
        Executa o clique utilizando a estratégia de retry da BasePage.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        self._log_info(
            "Iniciando clique no elemento",
            event="element_click_started",
            element=element_name,
            timeout=effective_timeout,
        )

        self._click_with_retry(
            locator,
            timeout=effective_timeout,
            element_name=element_name,
        )

        self._log_info(
            "Clique realizado",
            event="element_clicked",
            element=element_name,
        )

    def _click_if_visible(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ) -> bool:
        """
        Clica no elemento quando ele está disponível.

        Retorna False quando o elemento não fica clicável dentro
        do timeout informado.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        try:
            element = self._wait_for_clickable(
                locator,
                timeout=effective_timeout,
                element_name=element_name,
            )

        except TimeoutException:
            self._log_info(
                "Elemento não estava disponível para clique",
                event="element_not_available_for_click",
                element=element_name,
            )
            return False

        try:
            element.click()

        except WebDriverException:
            self._force_tap_element(
                element=element,
                element_name=element_name,
            )

        self._log_info(
            "Clique condicional realizado",
            event="conditional_click_finished",
            element=element_name,
        )

        return True

    def _click_with_fallback(
        self,
        primary_locator,
        fallback_locator,
        primary_name: str = "elemento_principal",
        fallback_name: str = "elemento_fallback",
        timeout: Optional[int] = None,
    ) -> None:
        """
        Tenta clicar no locator principal e utiliza o fallback
        quando o primeiro não está disponível.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        if self._click_if_visible(
            primary_locator,
            timeout=self.SHORT_TIMEOUT,
            element_name=primary_name,
        ):
            self._log_info(
                "Locator principal utilizado",
                event="primary_locator_used",
                element=primary_name,
            )
            return

        self._log_warning(
            "Locator fallback será utilizado",
            event="fallback_locator_used",
            element=primary_name,
            fallback_element=fallback_name,
        )

        self._click(
            fallback_locator,
            timeout=effective_timeout,
            element_name=fallback_name,
        )

    # === Inputs e textos ===
    def _type(
        self,
        locator,
        text: str,
        field_name: str,
        timeout: Optional[int] = None,
        sensitive: bool = False,
    ) -> None:
        """
        Limpa e preenche um campo de texto.

        Quando send_keys falha, utiliza mobile:type como fallback.
        Valores sensíveis são ocultados nos logs.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        field = self._wait_for_clickable(
            locator,
            timeout=effective_timeout,
            element_name=field_name,
        )

        field.click()

        try:
            field.clear()

        except WebDriverException:
            self._log_warning(
                "Não foi possível limpar o campo antes do preenchimento",
                event="field_clear_failed",
                field=field_name,
            )

        log_value = (
            "***"
            if sensitive
            else text
        )

        self._log_info(
            "Preenchendo campo",
            event="field_fill_started",
            field=field_name,
            value=log_value,
        )

        try:
            field.send_keys(text)

        except WebDriverException:
            self._log_warning(
                "send_keys falhou; repetindo preenchimento no Android",
                event="send_keys_failed_android_retry",
                field=field_name,
            )
            field.click()
            field.send_keys(text)

        self._log_info(
            "Campo preenchido",
            event="field_filled",
            field=field_name,
        )

    def _clear_field(
        self,
        locator,
        timeout: Optional[int] = None,
        field_name: str = "campo",
    ) -> None:
        """
        Tenta limpar o conteúdo de um campo.
        """
        effective_timeout = self._resolve_timeout(
            timeout
        )

        field = self._wait_for_clickable(
            locator,
            timeout=effective_timeout,
            element_name=field_name,
        )

        field.click()

        try:
            field.clear()

            self._log_info(
                "Campo limpo",
                event="field_cleared",
                field=field_name,
            )

        except WebDriverException:
            self._log_warning(
                "Não foi possível limpar o campo",
                event="field_clear_failed",
                field=field_name,
            )

    def _get_text(
        self,
        locator,
        timeout: Optional[int] = None,
        element_name: str = "elemento",
    ) -> str:
        """
        Aguarda a visibilidade do elemento e retorna seu texto.
        """
        element = self._wait_for_visible(
            locator,
            timeout=timeout,
            element_name=element_name,
        )

        text = element.text

        self._log_info(
            "Texto do elemento capturado",
            event="element_text_captured",
            element=element_name,
        )

        return text

    # === Elementos opcionais ===
    def _obter_elemento_visivel_imediatamente(
        self,
        locator: tuple[str, str],
    ):
        """
        Consulta a árvore atual sem adicionar wait por locator.
        """
        try:
            elementos = self.driver.find_elements(*locator)
        except WebDriverException:
            return None

        for elemento in elementos:
            try:
                if elemento.is_displayed():
                    return elemento
            except (
                StaleElementReferenceException,
                WebDriverException,
            ):
                continue

        return None

    def _esta_visivel_imediatamente(
        self,
        locator: tuple[str, str],
    ) -> bool:
        return (
            self._obter_elemento_visivel_imediatamente(locator)
            is not None
        )

    # === Alertas com mensagem desconhecida ===
    def _obter_texto_desconhecido_do_alerta(
        self,
        titulo_locator: tuple[str, str],
        botao_ok_locator: tuple[str, str],
        textos_conhecidos: set[str],
    ) -> Optional[str]:
        """
        Best-effort: detecta um alerta com título/botão já conhecidos,
        mas cuja mensagem ainda não tem locator específico.

        TODO: validar no Appium Inspector se a heurística abaixo
        (primeiro StaticText visível fora do título/botão) sempre
        captura o texto do alerta, e não texto de outro elemento da
        tela. A suposição é que o restante da tela fica visible=false
        enquanto o alerta está em primeiro plano — mesmo comportamento
        documentado em _wait_for_absence. Ajustar aqui se um falso
        positivo aparecer em execução real.
        """
        if not self._is_visible(
            titulo_locator,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
        ):
            return None

        if not self._is_visible(
            botao_ok_locator,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
        ):
            return None

        ignorar = textos_conhecidos | {"ifPontoCell", "OK"}

        try:
            elementos = self.driver.find_elements(
                AppiumBy.CLASS_NAME,
                "android.widget.TextView",
            )
        except WebDriverException:
            return None

        for elemento in elementos:
            try:
                if not elemento.is_displayed():
                    continue

                texto = (elemento.text or "").strip()

            except (
                StaleElementReferenceException,
                WebDriverException,
            ):
                continue

            if texto and texto not in ignorar:
                return texto

        return None

    def _wait_for_absence(
        self,
        locator: tuple[str, str],
        timeout: float,
    ) -> bool:
        """
        Aguarda o elemento deixar de estar visível na árvore.

        Não usa EC.invisibility_of_element_located porque essa
        condição trata visible=false como sucesso. No iOS isso gera
        falso positivo: o UiAutomator2 reporta visible=false para modais
        ainda montados durante a animação de saída, e o chamador
        seguiria em frente com o popup cobrindo a tela.
        """
        limite = monotonic() + timeout

        while True:
            if not self._esta_visivel_imediatamente(locator):
                return True

            if monotonic() >= limite:
                return False

            sleep(self.POLL_FREQUENCY)

    def _dismiss_if_present(
        self,
        locator: tuple[str, str],
        timeout: float,
        element_name: str,
    ) -> bool:
        """
        Toca em um elemento opcional. Nunca levanta por ausência.

        Utiliza presença em vez de visibilidade porque o UiAutomator2
        reporta visible=false para elementos presentes na árvore
        durante a animação de apresentação de modais.

        Não passa pelo _click_with_retry de propósito: aquele caminho
        é estrito por contrato e só faz sentido quando o elemento é
        obrigatório para o cenário.

        Retorna True apenas quando o toque foi executado. Isso não
        significa que o popup fechou.
        """
        try:
            elemento = self._wait(timeout).until(
                EC.presence_of_element_located(locator)
            )

        except TimeoutException:
            self._log_info(
                "Elemento opcional ausente",
                event="optional_element_absent",
                element=element_name,
            )
            return False

        try:
            self.driver.execute_script(
                "mobile: clickGesture",
                {"elementId": elemento.id},
            )

        except InvalidArgumentException:
            # Parâmetro inválido é erro de programação, não ausência
            # de elemento. Precisa ser barulhento.
            raise

        except (
            StaleElementReferenceException,
            WebDriverException,
        ) as error:
            self._log_warning(
                "Elemento opcional desapareceu antes do toque",
                event="optional_element_vanished",
                element=element_name,
                error=str(error),
            )
            return False

        self._log_info(
            "Toque em elemento opcional executado",
            event="optional_element_tapped",
            element=element_name,
            interaction="click_gesture",
        )

        return True

    # === Popups opcionais ===
    def _handle_optional_popup(
        self,
        check_method: Callable[[], bool],
        action_method: Callable[[], None],
        popup_name: str,
    ) -> bool:
        """
        Trata um popup opcional sem interromper o fluxo principal.

        Retorna True quando o popup é tratado pelo método informado
        ou por meio de um alerta nativo do iOS.
        """
        self._log_info(
            "Iniciando tratamento do popup opcional",
            event="optional_popup_handle_started",
            popup=popup_name,
        )

        try:
            if not check_method():
                self._log_info(
                    "Popup opcional não estava visível",
                    event="optional_popup_not_present",
                    popup=popup_name,
                )
                return False

            action_method()

            self._log_info(
                "Popup opcional tratado",
                event="optional_popup_handled",
                popup=popup_name,
            )
            return True

        except Exception:
            if self._try_resolve_ios_alert():
                self._log_info(
                    "Popup resolvido por alerta nativo",
                    event="optional_popup_resolved_by_ios_alert",
                    popup=popup_name,
                )
                return True

            self._log_warning(
                "Não foi possível tratar o popup opcional",
                event="optional_popup_handle_failed",
                popup=popup_name,
            )
            return False