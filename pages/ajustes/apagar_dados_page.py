import json
from functools import cached_property

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException

from pages.ajustes.settings_page import SettingsPage
from pages.android_locators import (
    android_id,
    android_text,
    android_text_contains,
)
from pages.base_page import BasePage
from pages.zerar_dados.zerar_dados_page import ZerarDadosPage
from utils.texto import normalizar_texto


class ApagarDadosAjustesPage(BasePage):
    """
    Page: botão APAGAR DADOS DO APLICATIVO dos Ajustes do aplicativo e o
    diálogo que ele abre.

    Mesmo texto e mesma ação do ZERAR DADOS do menu do perfil
    (ZerarDadosPage). No iOS o diálogo dos Ajustes é outro componente;
    no Android, ainda não confirmado: os locators vão pelo texto, que
    serve aos dois casos.
    """

    SCREEN_NAME = "apagar_dados_ajustes"

    TEXTO_BOTAO_APAGAR = "APAGAR DADOS DO APLICATIVO"

    # Confirmado no Inspector.
    BOTAO_APAGAR = android_id("btn_apagar_dados")

    # PENDENTE: diálogo por texto até o XML dele aberto pelos Ajustes
    # (PENDENCIAS_LOCATORS_ANDROID.md).
    TITULO = android_text("Apagar dados do aplicativo")
    MENSAGEM = android_text_contains("Ao confirmar esta operação")
    BOTAO_NAO = android_text("NÃO")
    BOTAO_SIM = android_text("SIM")

    # === Composição ===
    @cached_property
    def ajustes(self) -> SettingsPage:
        return SettingsPage(self.driver)

    # === Botão ===
    def _rolar_ate_o_botao(self) -> None:
        """
        O botão fica no fim da tela: em aparelhos menores, abaixo da
        dobra. UiScrollable rola no device até o texto aparecer.
        """
        if self._is_visible(self.BOTAO_APAGAR, timeout=self.SHORT_TIMEOUT):
            return

        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                "new UiScrollable(new UiSelector().scrollable(true))"
                ".scrollIntoView(new UiSelector()"
                f".text({json.dumps(self.TEXTO_BOTAO_APAGAR)}))",
            )
        except WebDriverException:
            pass

    # === Diálogo ===
    def abrir_confirmacao(self, ja_nos_ajustes: bool = False) -> None:
        """
        (Home -> Ajustes do aplicativo ->) APAGAR DADOS DO APLICATIVO.

        ja_nos_ajustes: a tela de Ajustes já está aberta (deixada pelo
        teste do NÃO); só toca no botão.
        """
        if not ja_nos_ajustes:
            self.ajustes.acessar_ajustes_aplicativo()

        self._rolar_ate_o_botao()

        self._click(
            self.BOTAO_APAGAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_apagar_dados_ajustes",
        )

        assert self._is_visible(self.TITULO, timeout=self.LONG_TIMEOUT), (
            "O diálogo 'Apagar dados do aplicativo' não foi exibido após "
            "tocar em APAGAR DADOS DO APLICATIVO nos Ajustes."
        )

    def titulo(self) -> str:
        return normalizar_texto(
            self._find(self.TITULO, element_name="titulo_apagar_dados").text
        )

    def mensagem(self) -> str:
        return normalizar_texto(
            self._find(
                self.MENSAGEM, element_name="mensagem_apagar_dados"
            ).text
        )

    def _responder(self, botao: tuple[str, str], nome: str) -> None:
        self._click(botao, timeout=self.DEFAULT_TIMEOUT, element_name=nome)

        assert self._wait_for_absence(
            self.TITULO, timeout=self.DEFAULT_TIMEOUT
        ), f"O diálogo de apagar dados não fechou após tocar em {nome}."

    def cancelar(self) -> None:
        """NÃO: fecha o diálogo e mantém os dados; continua nos Ajustes."""
        self._responder(self.BOTAO_NAO, "botao_nao_apagar_dados")

    def confirmar(self) -> None:
        """SIM: apaga os dados do usuário neste aparelho."""
        self._responder(self.BOTAO_SIM, "botao_sim_apagar_dados")

        self._log_info(
            "Dados do aplicativo apagados pelos Ajustes",
            event="app_data_erased_from_settings",
        )

    def voltou_ao_primeiro_acesso(self, timeout: float) -> bool:
        """Mesma checagem do ZERAR DADOS do menu do perfil."""
        return ZerarDadosPage(self.driver).voltou_ao_primeiro_acesso(timeout)
