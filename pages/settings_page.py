from functools import cached_property
from typing import Optional

from pages.android_locators import android_id
from pages.base_page import BasePage
from pages.home_page import HomePage
from pages.menu_page import MenuLateralPage


class SettingsPage(BasePage):
    SCREEN_NAME = "settings"

    @cached_property
    def menu_lateral(self) -> MenuLateralPage:
        return MenuLateralPage(self.driver)

    # Confirmado no projeto Android de referência.
    MARCADOR_TELA_AJUSTES = android_id("linearAjustes")

    # PENDENTE: confirmar os resource-ids exatos no Appium Inspector.
    SWITCH_CONFIRMACAO_FOTO = android_id(
        "switchConfirmacaoFoto", "switch_confirmacao_foto"
    )
    SWITCH_LEMBRETE_REGISTRO_PONTO = android_id(
        "switchLembreteRegistroPonto", "switch_lembrete_registro_ponto"
    )

    def acessar_ajustes_aplicativo(self) -> None:
        self.menu_lateral.acessar(MenuLateralPage.AJUSTES_APLICATIVO)
        assert self.esta_na_tela_ajustes(), (
            "A tela 'Ajustes do Aplicativo' não foi exibida."
        )

    def voltar_para_home(self) -> HomePage:
        self.driver.back()
        home_page = HomePage(self.driver)
        assert home_page.esta_na_home(timeout=home_page.LONG_TIMEOUT), (
            "A Home não foi exibida após retornar dos Ajustes."
        )
        return home_page

    def voltar(self) -> HomePage:
        return self.voltar_para_home()

    def esta_na_tela_ajustes(self, timeout: Optional[float] = None) -> bool:
        return self._is_visible(
            self.MARCADOR_TELA_AJUSTES,
            timeout=self.LONG_TIMEOUT if timeout is None else timeout,
        )

    def validar_tela_ajustes(self) -> bool:
        return self.esta_na_tela_ajustes()

    def _switch_esta_habilitado(self, locator, element_name: str) -> bool:
        elemento = self._wait_for_visible(locator, element_name=element_name)
        valor = (elemento.get_attribute("checked") or "").strip().lower()
        return valor in {"1", "true"}

    def confirmacao_foto_esta_habilitada(self) -> bool:
        return self._switch_esta_habilitado(
            self.SWITCH_CONFIRMACAO_FOTO, "switch_confirmacao_foto"
        )

    def validar_confirmacao_foto_habilitada(self) -> bool:
        return self.confirmacao_foto_esta_habilitada()

    def lembrete_registro_ponto_esta_habilitado(self) -> bool:
        return self._switch_esta_habilitado(
            self.SWITCH_LEMBRETE_REGISTRO_PONTO,
            "switch_lembrete_registro_ponto",
        )

    def validar_lembrete_registro_ponto_habilitado(self) -> bool:
        return self.lembrete_registro_ponto_esta_habilitado()
