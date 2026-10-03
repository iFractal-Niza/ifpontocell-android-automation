import json

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException

from pages.android_locators import android_id, android_text
from pages.base_page import BasePage


class BaseMenuPage(BasePage):
    """
    Base para os menus de navegação do aplicativo.

    Estrutura na árvore: RecyclerView (TABELA) > item com resource-id
    técnico (ex.: menuItemEsquerdoHolerite) > TextView com o texto exibido
    em caixa alta.

    Subclasses definem: botão de abertura, container da lista, opções
    (texto) e o mapa texto -> resource-id técnico.
    """

    SCREEN_NAME = "menu"

    # Definidos pelas subclasses
    BOTAO_ABRIR = None
    TABELA = None
    OPCOES = ()
    IDS_TECNICOS: dict[str, str] = {}

    # Opções que abrem uma tela por cima do menu, fechando-o. Depois do
    # toque numa delas, o menu ainda aberto quer dizer que o app ignorou
    # o toque (visto em vídeo no iOS: o Appium registra o clique e nada
    # muda) e ele é repetido uma vez. Opções fora da lista (ex.: ZERAR
    # DADOS, que abre um alerta e deixa o menu atrás) não são conferidas.
    OPCOES_QUE_FECHAM_O_MENU: frozenset[str] = frozenset()

    # === Locators dinâmicos ===
    @classmethod
    def _locator_opcao(cls, opcao: str) -> tuple[str, str]:
        """
        Locator principal da opção pelo resource-id técnico.

        Sem id mapeado, usa o texto exibido (item ainda não confirmado
        no Inspector).
        """
        id_tecnico = cls.IDS_TECNICOS.get(opcao)

        if id_tecnico is None:
            return android_text(opcao)

        return android_id(id_tecnico)

    @staticmethod
    def _locator_opcao_fallback(opcao: str) -> tuple[str, str]:
        """
        Fallback pelo texto exibido no item do menu.
        """
        return android_text(opcao)

    # === Validação da opção ===
    @classmethod
    def _validar_opcao(cls, opcao: str) -> str:
        """
        Garante que a opção pertence ao menu.

        Falha cedo com a lista de opções válidas em vez de
        estourar timeout procurando um item inexistente.
        """
        opcao_normalizada = opcao.strip().upper()

        if opcao_normalizada in cls.OPCOES:
            return opcao_normalizada

        disponiveis = ", ".join(cls.OPCOES)

        raise ValueError(
            f"Opção '{opcao}' não existe em {cls.SCREEN_NAME}. "
            f"Opções disponíveis: {disponiveis}."
        )

    # === Abertura e estado ===
    def abrir(self) -> None:
        """
        Aciona o botão que exibe o menu.
        """
        self._click(
            self.BOTAO_ABRIR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name=f"botao_abrir_{self.SCREEN_NAME}",
        )

        self._log_info(
            "Menu aberto",
            event="menu_opened",
            menu=self.SCREEN_NAME,
        )

    def esta_aberto(self, timeout: int | None = None) -> bool:
        """
        Verifica a exibição do menu pela lista (RecyclerView).
        """
        if self.TABELA is None:
            return False

        timeout_resolvido = self.SHORT_TIMEOUT if timeout is None else timeout

        is_visible = self._is_visible(
            self.TABELA,
            timeout=timeout_resolvido,
        )

        self._log_info(
            "Verificação de exibição do menu executada",
            event="menu_visibility_checked",
            menu=self.SCREEN_NAME,
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def abrir_se_necessario(self) -> None:
        """
        Abre o menu somente quando ele ainda não está visível.
        """
        if self.esta_aberto():
            self._log_info(
                "Menu já estava aberto",
                event="menu_already_open",
                menu=self.SCREEN_NAME,
            )
            return

        self.abrir()

    # === Rolagem ===
    def _rolar_ate_opcao(self, opcao: str) -> bool:
        """
        Rola o menu até tornar a opção visível.

        Usa UiScrollable.scrollIntoView, que rola no lado do device até
        o item aparecer. Falha na rolagem não interrompe: o clique
        seguinte acusa a opção ausente.
        """
        locator = self._locator_opcao(opcao)

        if self._is_visible(locator, timeout=self.SHORT_TIMEOUT):
            return True

        self._log_info(
            "Rolando o menu para localizar a opção",
            event="menu_scroll_attempt",
            menu=self.SCREEN_NAME,
            option=opcao,
        )

        id_tecnico = self.IDS_TECNICOS.get(opcao)
        alvo = (
            "new UiSelector().resourceIdMatches("
            f"{json.dumps(f'(.*:id/)?{id_tecnico}')})"
            if id_tecnico
            else f"new UiSelector().text({json.dumps(opcao)})"
        )

        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                "new UiScrollable(new UiSelector().scrollable(true))"
                f".scrollIntoView({alvo})",
            )
        except WebDriverException:
            self._log_warning(
                "Rolagem do menu não encontrou a opção",
                event="menu_scroll_failed",
                menu=self.SCREEN_NAME,
                option=opcao,
            )

        return self._is_visible(locator, timeout=self.SHORT_TIMEOUT)

    # === Navegação ===
    def acessar(self, opcao: str) -> None:
        """
        Abre o menu, se necessário, e seleciona a opção informada.

        A opção pode ser passada em qualquer caixa; a comparação
        é normalizada para o texto em caixa alta exibido no app.
        """
        opcao_normalizada = self._validar_opcao(opcao)

        self._log_info(
            "Acessando opção do menu",
            event="menu_option_access_started",
            menu=self.SCREEN_NAME,
            option=opcao_normalizada,
        )

        self.abrir_se_necessario()
        self._rolar_ate_opcao(opcao_normalizada)

        self._click_with_fallback(
            self._locator_opcao(opcao_normalizada),
            self._locator_opcao_fallback(opcao_normalizada),
            primary_name=f"opcao_{opcao_normalizada.lower()}",
            fallback_name=(f"opcao_{opcao_normalizada.lower()}_fallback"),
            timeout=self.DEFAULT_TIMEOUT,
        )

        if opcao_normalizada in self.OPCOES_QUE_FECHAM_O_MENU:
            self._garantir_que_o_toque_abriu(opcao_normalizada)

        self._log_info(
            "Opção do menu acionada",
            event="menu_option_accessed",
            menu=self.SCREEN_NAME,
            option=opcao_normalizada,
        )

    def opcao_esta_visivel(
        self,
        opcao: str,
        timeout: int | None = None,
    ) -> bool:
        """
        Verifica a exibição de uma opção específica do menu.
        """
        opcao_normalizada = self._validar_opcao(opcao)

        return self._is_visible(
            self._locator_opcao(opcao_normalizada),
            timeout=(self.SHORT_TIMEOUT if timeout is None else timeout),
        )

    def listar_opcoes_visiveis(self) -> list[str]:
        """
        Retorna as opções do menu presentes na árvore atual.

        Útil para validar a composição do menu conforme o perfil
        do usuário autenticado.
        """
        visiveis = [
            opcao
            for opcao in self.OPCOES
            if self.driver.find_elements(*self._locator_opcao(opcao))
        ]

        self._log_info(
            "Opções visíveis do menu listadas",
            event="menu_visible_options_listed",
            menu=self.SCREEN_NAME,
            visible_count=len(visiveis),
        )

        return visiveis

    def _garantir_que_o_toque_abriu(self, opcao: str) -> None:
        """
        Confere que o menu fechou depois do toque na opção; se não
        fechou, toca de novo uma vez (tap pelas coordenadas).

        A espera é longa de propósito: com a transição ainda em curso, o
        segundo toque cairia na tela nova.
        """
        if self._wait_for_absence(self.TABELA, timeout=self.DEFAULT_TIMEOUT):
            return

        elemento = self._obter_elemento_visivel_imediatamente(
            self._locator_opcao(opcao)
        )

        if elemento is None:
            return

        self._log_warning(
            "Menu continuou aberto após o toque; repetindo uma vez",
            event="menu_option_tap_retry",
            menu=self.SCREEN_NAME,
            option=opcao,
        )

        self._force_tap_element(
            elemento, element_name=f"opcao_{opcao.lower()}"
        )

        assert self._wait_for_absence(
            self.TABELA, timeout=self.DEFAULT_TIMEOUT
        ), (
            f"O menu continuou aberto depois de tocar em {opcao} duas vezes: "
            "o app não respondeu ao toque."
        )


class MenuLateralPage(BaseMenuPage):
    """
    Menu lateral acionado pelo botão de navegação da Home.
    """

    SCREEN_NAME = "menu_lateral"

    BOTAO_ABRIR = android_id("menu_esquerdo")
    TABELA = android_id("recyclerviewMenuEsquerdo")

    # === Opções ===
    AJUDA = "AJUDA"
    AJUSTES_APLICATIVO = "AJUSTES DO APLICATIVO"
    ASSINATURA_ESPELHO = "ASSINATURA DO ESPELHO"
    # Textos do Android (Inspector); no iOS: "COMUNICADOS" e
    # "ESTADO DO HUMOR".
    COMUNICADOS = "COMUNICADO"
    ESTADO_HUMOR = "ESTADO DE HUMOR"
    FERIAS = "FÉRIAS"
    HOLERITE = "HOLERITE"
    INFORME_RENDIMENTOS = "INFORME DE RENDIMENTOS"

    OPCOES = (
        AJUDA,
        AJUSTES_APLICATIVO,
        ASSINATURA_ESPELHO,
        COMUNICADOS,
        ESTADO_HUMOR,
        FERIAS,
        HOLERITE,
        INFORME_RENDIMENTOS,
    )

    # texto exibido -> resource-id técnico. Confirmados no Inspector:
    # ajuda, ajustes, assinatura do espelho, comunicado, estado de humor
    # (férias, holerite e informe não apareceram para o usuário de teste).
    IDS_TECNICOS = {
        AJUDA: "menuItemEsquerdoAjuda",
        AJUSTES_APLICATIVO: "menuItemEsquerdoAjustes",
        ASSINATURA_ESPELHO: "menuItemEsquerdoAssinaturaEspelho",
        COMUNICADOS: "menuItemEsquerdoComunicado",
        ESTADO_HUMOR: "menuItemEsquerdoEstadoHumor",
        FERIAS: "menuItemEsquerdoFerias",
        HOLERITE: "menuItemEsquerdoHolerite",
        INFORME_RENDIMENTOS: "menuItemEsquerdoInformeRendimento",
    }


class MenuPerfilPage(BaseMenuPage):
    """
    Menu do perfil acionado pelo avatar da barra superior.
    """

    SCREEN_NAME = "menu_perfil"

    BOTAO_ABRIR = android_id("menu_direito")
    TABELA = android_id("recyclerviewMenuDireito")

    # === Opções ===
    ACESSAR_SISTEMA = "ACESSAR SISTEMA"
    ALTERAR_IDIOMA = "ALTERAR IDIOMA"
    ALTERAR_SENHA = "ALTERAR SENHA"
    DADOS_PESSOAIS = "DADOS PESSOAIS"
    PERMISSOES = "PERMISSÕES"
    PRIVACIDADE = "PRIVACIDADE"
    SOBRE_APLICATIVO = "SOBRE O APLICATIVO"
    ZERAR_DADOS = "ZERAR DADOS"

    OPCOES = (
        ACESSAR_SISTEMA,
        ALTERAR_IDIOMA,
        ALTERAR_SENHA,
        DADOS_PESSOAIS,
        PERMISSOES,
        PRIVACIDADE,
        SOBRE_APLICATIVO,
        ZERAR_DADOS,
    )

    # Confirmadas abrindo tela própria no iOS; as demais não são
    # conferidas.
    OPCOES_QUE_FECHAM_O_MENU = frozenset(
        {ALTERAR_SENHA, DADOS_PESSOAIS, PRIVACIDADE, SOBRE_APLICATIVO}
    )

    # texto exibido -> resource-id técnico (projeto Android de referência)
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
