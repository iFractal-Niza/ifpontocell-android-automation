from functools import cached_property
from time import monotonic, sleep

from pages.android_locators import android_id
from pages.autenticacao.onboarding_page import OnboardingPage
from pages.base_page import BasePage
from pages.menu_page import MenuPerfilPage


class ZerarDadosPage(BasePage):
    """
    Page: diálogo "Apagar dados do aplicativo" (menu do perfil -> ZERAR
    DADOS). NÃO só fecha o diálogo; SIM apaga os dados do usuário no
    aparelho e o app volta ao primeiro acesso (onboarding).
    """

    SCREEN_NAME = "zerar_dados"

    # PENDENTE: provisório pelo diálogo genérico do app (o mesmo da
    # confirmação do registro de ponto no projeto de referência).
    # Título e mensagem (titulo()/mensagem() no iOS) entram com o
    # test_zerar_dados (PENDENCIAS_LOCATORS_ANDROID.md).
    DIALOGO = android_id("linear_dialog_geral", "relativeDialogPopUp")
    BOTAO_NAO = android_id("btnEsquerdo")
    BOTAO_SIM = android_id("btnDireito")

    # === Composição ===
    @cached_property
    def menu_perfil(self) -> MenuPerfilPage:
        return MenuPerfilPage(self.driver)

    # === Diálogo ===
    def abrir_confirmacao(self) -> None:
        self.menu_perfil.acessar(MenuPerfilPage.ZERAR_DADOS)

        assert self._is_visible(self.DIALOGO, timeout=self.LONG_TIMEOUT), (
            "O diálogo 'Apagar dados do aplicativo' não foi exibido após "
            "tocar em ZERAR DADOS no menu do perfil."
        )

    def _responder(self, botao: tuple[str, str], nome: str) -> None:
        self._click(botao, timeout=self.DEFAULT_TIMEOUT, element_name=nome)

        assert self._wait_for_absence(
            self.DIALOGO, timeout=self.DEFAULT_TIMEOUT
        ), f"O diálogo de zerar dados não fechou após tocar em {nome}."

    def cancelar(self) -> None:
        """
        NÃO: fecha o diálogo e mantém os dados. O menu do perfil continua
        aberto por trás.
        """
        self._responder(self.BOTAO_NAO, "botao_nao_zerar_dados")

    def confirmar(self) -> None:
        """SIM: apaga os dados do usuário neste aparelho."""
        self._responder(self.BOTAO_SIM, "botao_sim_zerar_dados")

        self._log_info(
            "Dados do aplicativo apagados",
            event="app_data_erased",
        )

    # === Depois de apagar ===
    def voltou_ao_primeiro_acesso(self, timeout: float) -> bool:
        """
        O app voltou a uma das telas iniciais do onboarding (boas-vindas,
        informações importantes ou configurar aplicativo), tratando o
        pedido de notificações se ele aparecer.
        """
        onboarding = OnboardingPage(self.driver)
        limite = monotonic() + timeout

        while monotonic() < limite:
            onboarding.fechar_popup_notificacoes_se_existir()

            if (
                onboarding.esta_na_tela_boas_vindas()
                or onboarding.esta_na_tela_informacoes_importantes()
                or onboarding.esta_na_tela_configurar_aplicativo()
            ):
                return True

            sleep(self.POLL_FREQUENCY)

        return False
