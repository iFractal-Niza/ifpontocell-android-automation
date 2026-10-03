from functools import cached_property

from pages.android_locators import android_pendente, android_text
from pages.base_page import BasePage
from pages.menu_page import MenuLateralPage
from pages.navegacao import VoltarParaHomeMixin


class EstadoHumorPage(VoltarParaHomeMixin, BasePage):
    """
    Page: tela "Estado de Humor" (menu lateral -> ESTADO DE HUMOR).

    Fluxo de registro:
    1. Tela de percentuais do mês + botão
       "Como está o seu humor neste momento?".
    2. Escolha do humor (grade de ícones, um Cell por humor).
    3. Confirmação (CANCELAR / CONFIRMAR), que volta à tela 1.
    """

    SCREEN_NAME = "estado_humor"
    NOME_TELA = "Estado de Humor"

    # Humores exibidos na tela de escolha (no iOS, name de cada Cell).
    HUMORES = (
        "Animado",
        "Entediado",
        "Feliz",
        "Triste",
        "Tranquilo",
        "Aflito",
        "Satisfeito",
        "Irritado",
    )

    # === Tela de percentuais ===
    # PENDENTE: id do botão no Android (iOS: estadoHumor.btnHumor).
    BOTAO_REGISTRAR = android_pendente("estadoHumor_btnHumor")

    # === Confirmação ===
    # PENDENTE: por texto, como no iOS, até o XML da tela.
    BOTAO_CONFIRMAR = android_text("CONFIRMAR")
    BOTAO_CANCELAR = android_text("CANCELAR")

    # === Composição ===
    @cached_property
    def menu_lateral(self) -> MenuLateralPage:
        return MenuLateralPage(self.driver)

    @staticmethod
    def _opcao_humor(humor: str) -> tuple[str, str]:
        # No iOS, a Cell da tela de escolha tem o name do humor
        # ("Animado"); na de percentuais o texto é "Animado, 0%", sem
        # ambiguidade. PENDENTE: pelo texto exato até o XML da tela.
        return android_text(humor)

    # === Acesso à tela ===
    def acessar(self) -> None:
        """
        Abre o Estado de Humor pelo menu lateral a partir da Home.
        """
        self.menu_lateral.acessar(MenuLateralPage.ESTADO_HUMOR)

        assert self.esta_na_tela(timeout=self.LONG_TIMEOUT), (
            "A tela 'Estado de Humor' não foi exibida após selecionar a "
            "opção no menu lateral. Se a opção não aparece no menu, "
            "verifique app_config.bts.mood.visible no servidor."
        )

    def esta_na_tela(self, timeout: float | None = None) -> bool:
        is_visible = self._is_visible(self.BOTAO_REGISTRAR, timeout=timeout)

        self._log_info(
            "Verificação da tela Estado de Humor executada",
            event="mood_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    # === Registro ===
    def registrar_humor(self, humor: str) -> None:
        """
        Registra o humor informado e confirma a volta à tela de
        percentuais (o fluxo completou sem travar o app).
        """
        assert humor in self.HUMORES, (
            f"Humor desconhecido: {humor!r}. Opções: {self.HUMORES}."
        )

        self._click(
            self.BOTAO_REGISTRAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_registrar_humor",
        )

        self._click(
            self._opcao_humor(humor),
            timeout=self.LONG_TIMEOUT,
            element_name=f"opcao_humor_{humor.lower()}",
        )

        assert self._is_visible(
            self.BOTAO_CONFIRMAR,
            timeout=self.DEFAULT_TIMEOUT,
        ), f"A confirmação do humor {humor!r} não foi exibida."

        self._click(
            self.BOTAO_CONFIRMAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_confirmar_humor",
        )

        assert self.esta_na_tela(timeout=self.LONG_TIMEOUT), (
            f"Após confirmar o humor {humor!r}, a tela do Estado de Humor "
            "não voltou a ser exibida."
        )

        self._log_info(
            "Humor registrado",
            event="mood_registered",
            humor=humor,
        )
