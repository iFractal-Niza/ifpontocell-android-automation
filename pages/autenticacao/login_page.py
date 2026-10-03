from pages.android_locators import android_id, android_text
from pages.base_page import BasePage


class LoginPage(BasePage):
    SCREEN_NAME = "login"

    # === Locators Android (confirmado no Inspector) ===
    # Tela: relative_login_access.
    CAMPO_LOGIN = android_id("editTextLogin")
    CAMPO_SENHA = android_id("editTextSenha")
    BOTAO_VER_SENHA = android_id("btn_senha_ver")

    BOTAO_ENTRAR = android_id("btn_confirmar")
    BOTAO_PROXIMO = BOTAO_ENTRAR

    # Popups: diálogo genérico do app (BasePage.DIALOGO_APP_*, confirmado
    # no Inspector). A mensagem fica pelo texto: é ela que diz qual popup
    # apareceu.
    POPUP_ERRO_TITULO = BasePage.DIALOGO_APP_TITULO
    POPUP_ERRO_MENSAGEM = android_text("Usuário e/ou senha inválidos.")
    POPUP_ERRO_BOTAO_OK = BasePage.DIALOGO_APP_BOTAO_OK
    POPUP_SEM_CONEXAO_MENSAGEM = android_text(
        "A conexão à internet parece estar desativada."
    )

    # Mensagens já conhecidas, usadas para não confundir um alerta
    # reconhecido com um alerta desconhecido (ver alerta_inesperado_*).
    TEXTOS_POPUP_CONHECIDOS = {
        "Usuário e/ou senha inválidos.",
        "A conexão à internet parece estar desativada.",
    }

    # === Validações de tela ===
    def esta_na_tela_login(self) -> bool:
        campo_login_visivel = self._is_visible(
            self.CAMPO_LOGIN,
            timeout=self.LONG_TIMEOUT,
        )

        if not campo_login_visivel:
            self._log_info(
                "Validação de presença da tela de login executada",
                event="login_screen_checked",
                status="not_visible",
            )
            return False

        campo_senha_visivel = self._is_visible(
            self.CAMPO_SENHA,
            timeout=self.SHORT_TIMEOUT,
        )

        is_on_login_screen = campo_login_visivel and campo_senha_visivel

        self._log_info(
            "Validação de presença da tela de login executada",
            event="login_screen_checked",
            status="visible" if is_on_login_screen else "not_visible",
        )

        return is_on_login_screen

    def validar_tela_login(self) -> bool:
        return self.esta_na_tela_login()

    # === Preenchimento ===
    def preencher_login(self, login: str) -> None:
        self._type(
            self.CAMPO_LOGIN,
            login,
            field_name="login",
            timeout=self.DEFAULT_TIMEOUT,
        )

    def limpar_login(self) -> None:
        self._clear_field(
            self.CAMPO_LOGIN,
            timeout=self.DEFAULT_TIMEOUT,
            field_name="login",
        )

    def preencher_senha(self, senha: str) -> None:
        self._type(
            self.CAMPO_SENHA,
            senha,
            field_name="senha",
            timeout=self.DEFAULT_TIMEOUT,
            sensitive=True,
        )

    def limpar_senha(self) -> None:
        self._clear_field(
            self.CAMPO_SENHA,
            timeout=self.DEFAULT_TIMEOUT,
            field_name="senha",
        )

    # === Estado da senha ===
    def obter_tipo_campo_senha(self) -> str:
        elemento = self.driver.find_element(
            *self.CAMPO_SENHA,
        )

        return elemento.get_attribute("password") or ""

    def obter_valor_campo_senha(self) -> str:
        elemento = self.driver.find_element(
            *self.CAMPO_SENHA,
        )

        return elemento.get_attribute("text") or elemento.text or ""

    def senha_esta_oculta(self) -> bool:
        return self.obter_tipo_campo_senha().strip().lower() == "true"

    def senha_esta_visivel(self) -> bool:
        return self.obter_tipo_campo_senha().strip().lower() == "false"

    # === Navegação ===
    def clicar_ver_senha(self) -> None:
        self._click(
            self.BOTAO_VER_SENHA,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_ver_senha",
        )

    def clicar_entrar(self) -> None:
        self._click(
            self.BOTAO_ENTRAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_entrar",
        )

    def clicar_proximo(self) -> None:
        self.clicar_entrar()

    def realizar_login(
        self,
        login: str,
        senha: str,
    ) -> None:
        self._log_info(
            "Iniciando fluxo de login",
            event="login_started",
        )

        self.preencher_login(login)
        self.preencher_senha(senha)
        self.clicar_entrar()

        self._log_info(
            "Fluxo de login executado",
            event="login_submitted",
        )

    # === Popup de credenciais inválidas ===
    def popup_erro_login_esta_visivel(self) -> bool:
        """
        Checagem ativa usada no caminho feliz (ver flows.realizar_login).

        Usa OPTIONAL_POPUP_TIMEOUT porque aqui o popup normalmente NÃO
        está presente — o objetivo é não pagar DEFAULT_TIMEOUT em toda
        execução de login válido. Para o caminho negativo, onde o
        popup É esperado, use validar_popup_erro_login().
        """
        is_visible = self._is_visible(
            self.POPUP_ERRO_MENSAGEM,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
        )

        self._log_info(
            "Verificação do popup de erro de login executada",
            event="login_error_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_popup_erro_login(self) -> bool:
        mensagem_visivel = self._is_visible(
            self.POPUP_ERRO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT,
        )

        if not mensagem_visivel:
            self._log_info(
                "Validação do popup de erro de login executada",
                event="login_error_popup_validated",
                status="invalid",
            )
            return False

        titulo_visivel = self._is_visible(
            self.POPUP_ERRO_TITULO,
            timeout=self.SHORT_TIMEOUT,
        )

        botao_visivel = self._is_visible(
            self.POPUP_ERRO_BOTAO_OK,
            timeout=self.SHORT_TIMEOUT,
        )

        is_valid = titulo_visivel and mensagem_visivel and botao_visivel

        self._log_info(
            "Validação do popup de erro de login executada",
            event="login_error_popup_validated",
            status="valid" if is_valid else "invalid",
        )

        return is_valid

    def obter_mensagem_erro_login(self) -> str:
        return self._get_text(
            self.POPUP_ERRO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="mensagem_erro_login",
        )

    def clicar_ok_popup_erro_login(self) -> None:
        self._click(
            self.POPUP_ERRO_BOTAO_OK,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_ok_popup_erro_login",
        )

    # === Popup de conexão indisponível ===
    def popup_sem_conexao_esta_visivel(self) -> bool:
        """
        Checagem ativa; ver nota de timeout em
        popup_erro_login_esta_visivel.
        """
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
            titulo_locator=self.POPUP_ERRO_TITULO,
            botao_ok_locator=self.POPUP_ERRO_BOTAO_OK,
            textos_conhecidos=self.TEXTOS_POPUP_CONHECIDOS,
        )
