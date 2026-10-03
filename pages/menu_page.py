from pages.android_locators import android_id, android_text
from pages.base_page import BasePage


class BaseMenuPage(BasePage):
    SCREEN_NAME = "menu"
    BOTAO_ABRIR = None
    TABELA = None
    OPCOES = ()
    IDS_TECNICOS: dict[str, str] = {}

    @classmethod
    def _locator_opcao(cls, opcao: str) -> tuple[str, str]:
        return android_id(cls.IDS_TECNICOS.get(opcao, opcao))

    @staticmethod
    def _locator_opcao_fallback(opcao: str) -> tuple[str, str]:
        return android_text(opcao)

    @classmethod
    def _validar_opcao(cls, opcao: str) -> str:
        normalizada = opcao.strip().upper()
        if normalizada not in cls.OPCOES:
            raise ValueError(
                f"Opção '{opcao}' não existe em {cls.SCREEN_NAME}. "
                f"Opções disponíveis: {', '.join(cls.OPCOES)}."
            )
        return normalizada

    def abrir(self) -> None:
        self._click(
            self.BOTAO_ABRIR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name=f"botao_abrir_{self.SCREEN_NAME}",
        )
        if self.TABELA:
            assert self._is_visible(
                self.TABELA,
                timeout=self.DEFAULT_TIMEOUT,
            ), f"O {self.SCREEN_NAME} não foi exibido."

    def esta_aberto(self, timeout: int | None = None) -> bool:
        return bool(self.TABELA) and self._is_visible(
            self.TABELA,
            timeout=self.SHORT_TIMEOUT if timeout is None else timeout,
        )

    def abrir_se_necessario(self) -> None:
        if not self.esta_aberto(timeout=self.OPTIONAL_POPUP_TIMEOUT):
            self.abrir()

    def _rolar_ate_opcao(self, opcao: str) -> bool:
        locator = self._locator_opcao(opcao)
        if self._is_visible(locator, timeout=self.SHORT_TIMEOUT):
            return True

        # UiScrollable mantém a rolagem no lado Android e evita gestures iOS.
        technical_id = self.IDS_TECNICOS.get(opcao)
        if technical_id:
            try:
                from appium.webdriver.common.appiumby import AppiumBy
                selector = (
                    'new UiScrollable(new UiSelector().scrollable(true))'
                    '.scrollIntoView(new UiSelector()'
                    f'.resourceIdMatches("(.*:id/)?{technical_id}"))'
                )
                self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, selector)
            except Exception:
                pass

        return self._is_visible(locator, timeout=self.SHORT_TIMEOUT)

    def acessar(self, opcao: str) -> None:
        normalizada = self._validar_opcao(opcao)
        self.abrir_se_necessario()
        self._rolar_ate_opcao(normalizada)
        self._click_with_fallback(
            self._locator_opcao(normalizada),
            self._locator_opcao_fallback(normalizada),
            primary_name=f"opcao_{normalizada.lower()}",
            fallback_name=f"opcao_{normalizada.lower()}_fallback",
            timeout=self.DEFAULT_TIMEOUT,
        )

    def opcao_esta_visivel(self, opcao: str, timeout: int | None = None) -> bool:
        normalizada = self._validar_opcao(opcao)
        return self._is_visible(
            self._locator_opcao(normalizada),
            timeout=self.SHORT_TIMEOUT if timeout is None else timeout,
        )

    def listar_opcoes_visiveis(self) -> list[str]:
        return [
            opcao for opcao in self.OPCOES
            if self.driver.find_elements(*self._locator_opcao(opcao))
        ]


class MenuLateralPage(BaseMenuPage):
    SCREEN_NAME = "menu_lateral"
    BOTAO_ABRIR = android_id("menu_esquerdo")
    TABELA = android_id("recyclerviewMenuEsquerdo")

    AJUDA = "AJUDA"
    AJUSTES_APLICATIVO = "AJUSTES DO APLICATIVO"
    ASSINATURA_ESPELHO = "ASSINATURA DO ESPELHO"
    COMUNICADOS = "COMUNICADOS"
    FERIAS = "FÉRIAS"
    HOLERITE = "HOLERITE"
    INFORME_RENDIMENTOS = "INFORME DE RENDIMENTOS"

    OPCOES = (
        AJUDA, AJUSTES_APLICATIVO, ASSINATURA_ESPELHO,
        COMUNICADOS, FERIAS, HOLERITE, INFORME_RENDIMENTOS,
    )
    IDS_TECNICOS = {
        AJUDA: "menuItemEsquerdoAjuda",
        AJUSTES_APLICATIVO: "menuItemEsquerdoAjustes",
        ASSINATURA_ESPELHO: "menuItemEsquerdoAssinaturaEspelho",
        COMUNICADOS: "menuItemEsquerdoComunicado",
        FERIAS: "menuItemEsquerdoFerias",
        HOLERITE: "menuItemEsquerdoHolerite",
        INFORME_RENDIMENTOS: "menuItemEsquerdoInformeRendimento",
    }


class MenuPerfilPage(BaseMenuPage):
    SCREEN_NAME = "menu_perfil"
    BOTAO_ABRIR = android_id("menu_direito")
    TABELA = android_id("recyclerviewMenuDireito")

    ACESSAR_SISTEMA = "ACESSAR SISTEMA"
    ALTERAR_IDIOMA = "ALTERAR IDIOMA"
    ALTERAR_SENHA = "ALTERAR SENHA"
    DADOS_PESSOAIS = "DADOS PESSOAIS"
    PERMISSOES = "PERMISSÕES"
    PRIVACIDADE = "PRIVACIDADE"
    SOBRE_APLICATIVO = "SOBRE O APLICATIVO"
    ZERAR_DADOS = "ZERAR DADOS"

    OPCOES = (
        ACESSAR_SISTEMA, ALTERAR_IDIOMA, ALTERAR_SENHA, DADOS_PESSOAIS,
        PERMISSOES, PRIVACIDADE, SOBRE_APLICATIVO, ZERAR_DADOS,
    )
    IDS_TECNICOS = {
        ACESSAR_SISTEMA: "menuItemDireitoAcessoSistema",
        ALTERAR_IDIOMA: "menuItemDireitoIdioma",
        ALTERAR_SENHA: "menuItemDireitoAlterarSenha",
        DADOS_PESSOAIS: "menuItemDireitoDadosPessoais",
        PERMISSOES: "menuItemDireitoPermissoes",
        PRIVACIDADE: "menuItemDireitoPrivacidade",
        SOBRE_APLICATIVO: "menuItemDireitoSobre",
        ZERAR_DADOS: "menuItemDireitoZerarDados",
    }
