from pages.android_locators import android_id, android_text, android_text_contains

from config.timeouts import OPTIONAL_POPUP_TIMEOUT
from pages.base_page import BasePage


class OnboardingPage(BasePage):
    SCREEN_NAME = "onboarding"

    # === Locators Android (projeto de referência) ===
    BOTAO_PROXIMO_BOAS_VINDAS = android_id("btn_confirmar_informacao")
    BOTAO_INICIAR_CONFIGURACAO = android_id("btn_confirmar_informacao")
    CAMPO_NOME_SISTEMA = android_id("editTextSistema")
    BOTAO_PROXIMO_SISTEMA = android_id("btn_confirmar")

    # Conteúdo: fallback textual; validar resource-id no Inspector se necessário.
    TITULO_BOAS_VINDAS = android_text_contains("bem-vindo")
    TITULO_CONFIGURAR_APLICATIVO = android_text_contains("Configurar")

    # Permission Controller Android.
    BOTAO_ALERTA_NAO_PERMITIR = android_id(
        "com.android.permissioncontroller:id/permission_deny_button",
        "com.android.packageinstaller:id/permission_deny_button",
    )
    BOTAO_ALERTA_PERMITIR = android_id(
        "com.android.permissioncontroller:id/permission_allow_button",
        "com.android.permissioncontroller:id/permission_allow_foreground_only_button",
        "com.android.packageinstaller:id/permission_allow_button",
    )

    # Popups: não há resource-id técnico no projeto Android de referência.
    POPUP_SISTEMA_NAO_ENCONTRADO_TITULO = android_text("ifPontoCell")
    POPUP_SISTEMA_NAO_ENCONTRADO_MENSAGEM = android_text("Sistema não encontrado.")
    POPUP_SISTEMA_NAO_ENCONTRADO_BOTAO_OK = android_text("OK")
    POPUP_SEM_CONEXAO_MENSAGEM = android_text(
        "A conexão à internet parece estar desativada."
    )

    # Mensagens já conhecidas, usadas para não confundir um alerta
    # reconhecido com um alerta desconhecido (ver alerta_inesperado_*).
    TEXTOS_POPUP_CONHECIDOS = {
        "Sistema não encontrado.",
        "A conexão à internet parece estar desativada.",
    }

    # === Alertas opcionais ===
    def fechar_popup_notificacoes_se_existir(
        self,
        permitir: bool = False,
    ) -> bool:
        self._log_info(
            "Tentando tratar popup de notificações",
            event="notification_popup_handle_started",
            allow_notifications=permitir,
        )

        popup_tratado = (
            self._try_accept_ios_alert()
            if permitir
            else self._try_dismiss_ios_alert()
        )

        if popup_tratado:
            self._log_info(
                "Popup de notificações tratado via alerta nativo",
                event="notification_popup_handled",
                strategy="native_alert",
                allow_notifications=permitir,
            )
            return True

        botao = (
            self.BOTAO_ALERTA_PERMITIR
            if permitir
            else self.BOTAO_ALERTA_NAO_PERMITIR
        )

        nome_botao = (
            "permitir_notificacoes"
            if permitir
            else "nao_permitir_notificacoes"
        )

        popup_tratado = self._click_if_visible(
            botao,
            timeout=OPTIONAL_POPUP_TIMEOUT,
            element_name=nome_botao,
        )

        if popup_tratado:
            self._log_info(
                "Popup de notificações tratado via botão",
                event="notification_popup_handled",
                strategy="button",
                allow_notifications=permitir,
            )
            return True

        self._log_info(
            "Popup de notificações não estava presente",
            event="notification_popup_not_present",
            allow_notifications=permitir,
        )

        return False

    # === Validações de tela ===
    def esta_na_tela_boas_vindas(self) -> bool:
        is_visible = self._is_visible(
            self.BOTAO_PROXIMO_BOAS_VINDAS,
            timeout=self.DEFAULT_TIMEOUT,
        )

        self._log_info(
            "Validação da tela de boas-vindas executada",
            event="welcome_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_tela_boas_vindas(self) -> bool:
        return self.esta_na_tela_boas_vindas()

    def esta_na_tela_informacoes_importantes(self) -> bool:
        is_visible = self._is_visible(
            self.BOTAO_INICIAR_CONFIGURACAO,
            timeout=self.DEFAULT_TIMEOUT,
        )

        self._log_info(
            "Validação da tela de informações importantes executada",
            event="important_info_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def esta_na_tela_configurar_aplicativo(self) -> bool:
        is_visible = self._is_visible(
            self.CAMPO_NOME_SISTEMA,
            timeout=self.LONG_TIMEOUT,
        )

        self._log_info(
            "Validação da tela de configurar aplicativo executada",
            event="configure_app_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_tela_configurar_aplicativo(self) -> bool:
        return self.esta_na_tela_configurar_aplicativo()

    # === Validações de conteúdo ===
    def titulo_boas_vindas_esta_visivel(self) -> bool:
        return self._is_visible(
            self.TITULO_BOAS_VINDAS,
            timeout=self.DEFAULT_TIMEOUT,
        )

    def titulo_configurar_aplicativo_esta_visivel(self) -> bool:
        return self._is_visible(
            self.TITULO_CONFIGURAR_APLICATIVO,
            timeout=self.DEFAULT_TIMEOUT,
        )

    # === Navegação ===
    def clicar_proximo_boas_vindas(self) -> None:
        self._click(
            self.BOTAO_PROXIMO_BOAS_VINDAS,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_proximo_boas_vindas",
        )

    def clicar_iniciar_configuracao(self) -> None:
        self._click(
            self.BOTAO_INICIAR_CONFIGURACAO,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_iniciar_configuracao",
        )

    def clicar_proximo_sistema(self) -> None:
        self._click(
            self.BOTAO_PROXIMO_SISTEMA,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_proximo_sistema",
        )

    # === Campo de sistema ===
    def preencher_nome_sistema(self, nome_sistema: str) -> None:
        self._type(
            self.CAMPO_NOME_SISTEMA,
            nome_sistema,
            field_name="nome_sistema",
            timeout=self.DEFAULT_TIMEOUT,
        )

    def limpar_nome_sistema(self) -> None:
        self._clear_field(
            self.CAMPO_NOME_SISTEMA,
            timeout=self.DEFAULT_TIMEOUT,
            field_name="nome_sistema",
        )

    def informar_nome_sistema_e_avancar(
        self,
        nome_sistema: str,
    ) -> None:
        self._log_info(
            "Informando sistema e avançando",
            event="system_name_submit_started",
        )

        self.preencher_nome_sistema(nome_sistema)
        self.clicar_proximo_sistema()

        self._log_info(
            "Sistema informado e avanço executado",
            event="system_name_submitted",
        )

    def corrigir_nome_sistema_e_avancar(
        self,
        nome_sistema: str,
    ) -> None:
        self._log_info(
            "Corrigindo sistema",
            event="system_name_correction_started",
        )

        self.limpar_nome_sistema()
        self.preencher_nome_sistema(nome_sistema)
        self.clicar_proximo_sistema()

        self._log_info(
            "Sistema corrigido e avanço executado",
            event="system_name_corrected_and_submitted",
        )

    # === Popup de sistema não encontrado ===
    def popup_sistema_nao_encontrado_esta_visivel(self) -> bool:
        """
        Checagem ativa usada no caminho feliz (ver flows.acessar_tela_login
        e flows.garantir_tela_login). Usa OPTIONAL_POPUP_TIMEOUT porque
        aqui o popup normalmente NÃO está presente. Para o caminho
        negativo, onde o popup É esperado, use
        validar_popup_sistema_nao_encontrado().
        """
        is_visible = self._is_visible(
            self.POPUP_SISTEMA_NAO_ENCONTRADO_MENSAGEM,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
        )

        self._log_info(
            "Verificação do popup de sistema não encontrado executada",
            event="system_not_found_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_popup_sistema_nao_encontrado(self) -> bool:
        mensagem_visivel = self._is_visible(
            self.POPUP_SISTEMA_NAO_ENCONTRADO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT,
        )

        if not mensagem_visivel:
            self._log_info(
                "Validação do popup de sistema não encontrado executada",
                event="system_not_found_popup_validated",
                status="invalid",
            )
            return False

        titulo_visivel = self._is_visible(
            self.POPUP_SISTEMA_NAO_ENCONTRADO_TITULO,
            timeout=self.SHORT_TIMEOUT,
        )

        botao_visivel = self._is_visible(
            self.POPUP_SISTEMA_NAO_ENCONTRADO_BOTAO_OK,
            timeout=self.SHORT_TIMEOUT,
        )

        is_valid = titulo_visivel and botao_visivel

        self._log_info(
            "Validação do popup de sistema não encontrado executada",
            event="system_not_found_popup_validated",
            status="valid" if is_valid else "invalid",
        )

        return is_valid

    def obter_mensagem_popup_sistema_nao_encontrado(self) -> str:
        return self._get_text(
            self.POPUP_SISTEMA_NAO_ENCONTRADO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="mensagem_popup_sistema_nao_encontrado",
        )

    def clicar_ok_popup_sistema_nao_encontrado(self) -> None:
        self._click(
            self.POPUP_SISTEMA_NAO_ENCONTRADO_BOTAO_OK,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_ok_popup_sistema_nao_encontrado",
        )

    # === Popup de conexão indisponível ===
    def popup_sem_conexao_esta_visivel(self) -> bool:
        """Checagem ativa; ver nota de timeout em popup_sistema_nao_encontrado_esta_visivel."""
        is_visible = self._is_visible(
            self.POPUP_SEM_CONEXAO_MENSAGEM,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
        )

        self._log_info(
            "Verificação do popup de conexão indisponível executada",
            event="no_connection_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def obter_mensagem_popup_sem_conexao(self) -> str:
        return self._get_text(
            self.POPUP_SEM_CONEXAO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="mensagem_popup_sem_conexao",
        )

    # === Alerta com mensagem desconhecida ===
    def obter_mensagem_alerta_inesperado(self) -> str | None:
        """
        Best-effort: ver TODO em BasePage._obter_texto_desconhecido_do_alerta.
        """
        return self._obter_texto_desconhecido_do_alerta(
            titulo_locator=self.POPUP_SISTEMA_NAO_ENCONTRADO_TITULO,
            botao_ok_locator=self.POPUP_SISTEMA_NAO_ENCONTRADO_BOTAO_OK,
            textos_conhecidos=self.TEXTOS_POPUP_CONHECIDOS,
        )

    # === Fluxo inicial ===
    def preparar_fluxo_inicial(
        self,
        permitir_notificacoes: bool = False,
    ) -> None:
        self._log_info(
            "Preparando fluxo inicial",
            event="onboarding_initial_flow_started",
            allow_notifications=permitir_notificacoes,
        )

        self.fechar_popup_notificacoes_se_existir(
            permitir=permitir_notificacoes,
        )

        if self.esta_na_tela_boas_vindas():
            self.clicar_proximo_boas_vindas()

        if self.esta_na_tela_informacoes_importantes():
            self.clicar_iniciar_configuracao()

        self._log_info(
            "Fluxo inicial finalizado",
            event="onboarding_initial_flow_finished",
        )