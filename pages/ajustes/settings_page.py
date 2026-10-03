from functools import cached_property

from pages.android_locators import android_id
from pages.base_page import BasePage
from pages.home_page import HomePage
from pages.menu_page import MenuLateralPage


class SettingsPage(BasePage):
    """
    Page: tela "Ajustes do aplicativo" (menu lateral -> AJUSTES DO APLICATIVO).
    Navegação até a tela: MenuLateralPage.
    """

    SCREEN_NAME = "settings"

    # === Composição ===
    @cached_property
    def menu_lateral(self) -> MenuLateralPage:
        return MenuLateralPage(self.driver)

    # === Tela de ajustes ===
    # Confirmado no Inspector (o linearAjustes do projeto de referência
    # não existe na build atual).
    MARCADOR_TELA_AJUSTES = android_id("header_ajustes")

    # === Configurações iniciais ===
    # PENDENTE: confirmar os resource-ids exatos no Appium Inspector
    # (PENDENCIAS_LOCATORS_ANDROID.md).
    SWITCH_CONFIRMACAO_FOTO = android_id(
        "switchConfirmacaoFoto", "switch_confirmacao_foto"
    )

    SWITCH_LEMBRETE_REGISTRO_PONTO = android_id(
        "switchLembreteRegistroPonto", "switch_lembrete_registro_ponto"
    )

    # === Acesso aos ajustes ===
    def acessar_ajustes_aplicativo(self) -> None:
        """
        Acessa a tela de Ajustes do Aplicativo a partir da Home.

        Pré-condição:
        - Home carregada (navBarPrincipal visível).
        """
        self._log_info(
            "Acessando Ajustes do Aplicativo",
            event="settings_open_started",
        )

        self.menu_lateral.acessar(
            MenuLateralPage.AJUSTES_APLICATIVO,
        )

        assert self.esta_na_tela_ajustes(), (
            "A tela 'Ajustes do Aplicativo' não foi exibida "
            "após selecionar a opção no menu lateral."
        )

        self._log_info(
            "Ajustes do Aplicativo acessado",
            event="settings_open_finished",
        )

    # === Navegação ===
    def voltar_para_home(self) -> HomePage:
        """
        Retorna dos Ajustes do Aplicativo para a Home.
        """
        self._log_info(
            "Retornando dos Ajustes do Aplicativo",
            event="settings_back_started",
        )

        # Voltar do sistema: os Ajustes não têm botão de voltar com
        # resource-id no projeto de referência.
        self.driver.back()

        home_page = HomePage(self.driver)

        assert home_page.esta_na_home(
            timeout=home_page.LONG_TIMEOUT,
        ), "A Home não foi exibida após retornar dos Ajustes do Aplicativo."

        self._log_info(
            "Retorno dos Ajustes do Aplicativo concluído",
            event="settings_back_finished",
        )

        return home_page

    def voltar(self) -> HomePage:
        """
        Mantido por compatibilidade com chamadas existentes.
        """
        return self.voltar_para_home()

    # === Validação da tela ===
    def esta_na_tela_ajustes(
        self,
        timeout: float | None = None,
    ) -> bool:
        """
        Valida a tela pelo cabeçalho técnico dos Ajustes (header_ajustes),
        sem depender do título visual.
        """
        timeout_resolvido = self.LONG_TIMEOUT if timeout is None else timeout

        is_visible = self._is_visible(
            self.MARCADOR_TELA_AJUSTES,
            timeout=timeout_resolvido,
        )

        self._log_info(
            "Validação da tela de ajustes executada",
            event="settings_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_tela_ajustes(self) -> bool:
        return self.esta_na_tela_ajustes()

    # === Estado dos switches ===
    def _obter_valor_switch(
        self,
        locator: tuple[str, str],
        element_name: str,
    ) -> str:
        elemento = self._wait_for_visible(
            locator,
            element_name=element_name,
        )

        # UiAutomator2: o estado do Switch vem em "checked".
        valor = elemento.get_attribute("checked") or ""

        self._log_info(
            "Estado do switch consultado",
            event="settings_switch_state_checked",
            element=element_name,
            value=valor,
        )

        return valor.strip().lower()

    def _switch_esta_habilitado(
        self,
        locator: tuple[str, str],
        element_name: str,
    ) -> bool:
        valor = self._obter_valor_switch(
            locator=locator,
            element_name=element_name,
        )

        return valor in {
            "1",
            "true",
        }

    # === Confirmação de foto ===
    def confirmacao_foto_esta_habilitada(self) -> bool:
        is_enabled = self._switch_esta_habilitado(
            locator=self.SWITCH_CONFIRMACAO_FOTO,
            element_name="switch_confirmacao_foto",
        )

        self._log_info(
            "Validação da confirmação de foto executada",
            event="photo_confirmation_checked",
            status="enabled" if is_enabled else "disabled",
        )

        return is_enabled

    def validar_confirmacao_foto_habilitada(self) -> bool:
        return self.confirmacao_foto_esta_habilitada()

    # === Lembrete para registro do ponto ===
    def lembrete_registro_ponto_esta_habilitado(self) -> bool:
        is_enabled = self._switch_esta_habilitado(
            locator=self.SWITCH_LEMBRETE_REGISTRO_PONTO,
            element_name="switch_lembrete_registro_ponto",
        )

        self._log_info(
            "Validação do lembrete de ponto executada",
            event="point_reminder_checked",
            status="enabled" if is_enabled else "disabled",
        )

        return is_enabled

    def validar_lembrete_registro_ponto_habilitado(self) -> bool:
        return self.lembrete_registro_ponto_esta_habilitado()
