from datetime import date
from time import monotonic, sleep

from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
)

from pages.android_locators import android_id, android_text_matches
from pages.base_page import BasePage
from utils.ponto import dia_do_painel, horario_da_marcacao, mesma_chave
from utils.texto import normalizar_texto


class PainelPontoPage(BasePage):
    """
    Page: painel do dia na tela Ponto (aba PONTO da Home).

    Data do dia com as setas (dia anterior / posterior, sem limite para
    nenhum lado), as marcações do dia, os cards (atividade laboral,
    status do momento, jornada diária) e os totais do espelho, que
    abrem e fecham pela seta ao lado do título.

    Separada da HomePage, que cuida dos popups, do registro de ponto e
    da navegação.
    """

    SCREEN_NAME = "painel_ponto"

    # === Confirmados no Inspector (Home) ===
    SETA_DIA_ANTERIOR = android_id("carregarDadosMenos")
    SETA_DIA_POSTERIOR = android_id("carregarDadosMais")

    # O ícone da seta (abrirFecharTotalizador) não é clicável: o toque
    # vai para o cabeçalho dos totais.
    BOTAO_TOTAIS = android_id("topTotalizador")

    # "Sábado, 03 de Outubro de 2026".
    DATA = android_id("data")

    # Título e período dos totais: no iOS um texto só ("TOTAIS DO
    # ESPELHO ... Período de ..."); no Android, dois TextViews.
    TITULO_TOTAIS = android_id("textViewTituloTotais")
    PERIODO_TOTAIS = android_id("textViewPeriodoTotais")

    # Faixa horizontal das marcações (no iOS, sem id).
    FAIXA_MARCACOES = android_id("include_registros")

    # PENDENTE: as marcações registradas. No iOS, textos "10:47 horas"
    # (ou "10:47e horas"); mesmo padrão até o XML de um dia com marcação
    # (PENDENCIAS_LOCATORS_ANDROID.md).
    MARCACOES = android_text_matches(".* horas")

    # Rótulo de cada card ("RÓTULO, valor").
    CARDS = ("ATIVIDADE LABORAL", "STATUS DO MOMENTO", "JORNADA DIÁRIA")

    # Itens dos totais, na ordem da tela.
    ITENS_TOTAIS = (
        "INTERJORNADA",
        "TOTAL DE HORAS",
        "DESCONTOS",
        "HORAS NOTURNAS",
        "HORAS EXTRAS",
    )

    # Valores dos cards (confirmado): textview_valor_ponto, com o
    # content-desc "RÓTULO valor" ("STATUS DO MOMENTO Folga"). No iOS,
    # textos "RÓTULO, valor". O rótulo é comparado no Python, normalizado
    # (mesma_chave): o app varia espaços e caixa.
    # PENDENTE: os itens dos totais abertos (assumido o mesmo componente).
    TEXTOS_ROTULO_VALOR = android_id("textview_valor_ponto")

    # Primeiro item dos totais (uma palavra só): diz se estão abertos.
    # PENDENTE: por texto até o XML com os totais abertos.
    PRIMEIRO_ITEM_TOTAIS = android_text_matches("(?i)interjornada.*")

    # === Leitura ===
    def _textos(self, locator, atributo: str = "text") -> list[str]:
        textos = []

        try:
            elementos = self.driver.find_elements(*locator)
        except WebDriverException:
            return []

        for elemento in elementos:
            try:
                textos.append(
                    normalizar_texto(elemento.get_attribute(atributo))
                )
            except (StaleElementReferenceException, WebDriverException):
                continue

        return textos

    # Rótulos conhecidos: no Android o content-desc não separa rótulo e
    # valor por vírgula ("STATUS DO MOMENTO Folga").
    def _separar_rotulo(self, texto: str) -> tuple[str, str] | None:
        chave = mesma_chave(texto)

        for rotulo in (*self.CARDS, *self.ITENS_TOTAIS):
            prefixo = mesma_chave(rotulo)

            if chave == prefixo or chave.startswith(prefixo + " "):
                return prefixo, normalizar_texto(texto)[len(rotulo) :].strip()

        return None

    def _valores_por_rotulo(self) -> dict[str, str]:
        """{"jornada diaria": "42%", "total de horas": "28:58", ...}."""
        valores = {}

        for texto in self._textos(
            self.TEXTOS_ROTULO_VALOR, atributo="content-desc"
        ):
            separado = self._separar_rotulo(texto)

            if separado:
                rotulo, valor = separado
                valores[rotulo] = valor

        return valores

    def _valores(self, rotulos) -> dict[str, str | None]:
        valores = self._valores_por_rotulo()

        return {rotulo: valores.get(mesma_chave(rotulo)) for rotulo in rotulos}

    def esta_visivel(self, timeout: float | None = None) -> bool:
        return self._is_visible(self.DATA, timeout=timeout)

    def data_exibida(self) -> str:
        assert self.esta_visivel(timeout=self.LONG_TIMEOUT), (
            "A data do painel da tela Ponto não foi exibida."
        )

        textos = self._textos(self.DATA)

        return textos[0] if textos else ""

    def marcacoes(self) -> list[str]:
        """Horários das marcações do dia exibido, na ordem: ["10:47", ...]."""
        return [
            horario
            for horario in map(
                horario_da_marcacao, self._textos(self.MARCACOES)
            )
            if horario
        ]

    # Rolagens da faixa de marcações ao procurar um horário: com muitas
    # marcações no dia, as últimas ficam fora da tela.
    MAX_ROLAGENS_MARCACOES = 3

    def _rolar_marcacoes(self) -> None:
        """
        Arrasta a faixa de marcações da direita para a esquerda. No iOS
        a faixa não tem id (arrasto na altura da 1ª marcação); no Android
        é o include_registros (swipeGesture do UiAutomator2).
        """
        try:
            faixa = self.driver.find_element(*self.FAIXA_MARCACOES)
        except WebDriverException:
            return

        self.driver.execute_script(
            "mobile: swipeGesture",
            {"elementId": faixa.id, "direction": "left", "percent": 0.6},
        )

    def aguardar_marcacao(self, horario: str, timeout: float) -> bool:
        """
        Espera o horário ("14:03") aparecer na faixa de marcações do dia
        exibido. Sem ele na tela, rola a faixa (até MAX_ROLAGENS_MARCACOES
        vezes) e volta a procurar até o timeout.
        """
        limite = monotonic() + timeout
        rolagens = 0

        while True:
            if horario in self.marcacoes():
                return True

            if monotonic() >= limite:
                return False

            if rolagens < self.MAX_ROLAGENS_MARCACOES and self.marcacoes():
                self._rolar_marcacoes()
                rolagens += 1

            sleep(self.POLL_FREQUENCY)

    def cards(self) -> dict[str, str | None]:
        """
        {"ATIVIDADE LABORAL": "3h + 24min", ...}; None se o card faltar,
        "" se estiver sem valor (dia futuro: "ATIVIDADE LABORAL, ").
        """
        return self._valores(self.CARDS)

    # === Navegação entre os dias ===
    def _tocar_seta_e_aguardar_outra_data(self, seta, nome: str) -> str:
        anterior = self.data_exibida()

        self._click(seta, timeout=self.DEFAULT_TIMEOUT, element_name=nome)

        limite = monotonic() + self.LONG_TIMEOUT

        while monotonic() < limite:
            atual = self._textos(self.DATA)

            if atual and atual[0] != anterior:
                self._log_info(
                    "Dia do painel trocado",
                    event="painel_ponto_dia_trocado",
                    de=anterior,
                    para=atual[0],
                )
                return atual[0]

            sleep(self.POLL_FREQUENCY)

        raise AssertionError(
            f"A data do painel continuou {anterior!r} depois de tocar na "
            f"seta ({nome})."
        )

    def ir_para_dia_anterior(self) -> str:
        """Toca na seta da esquerda; devolve a nova data exibida."""
        return self._tocar_seta_e_aguardar_outra_data(
            self.SETA_DIA_ANTERIOR, "seta_dia_anterior"
        )

    def ir_para_dia_posterior(self) -> str:
        """Toca na seta da direita; devolve a nova data exibida."""
        return self._tocar_seta_e_aguardar_outra_data(
            self.SETA_DIA_POSTERIOR, "seta_dia_posterior"
        )

    def dia_exibido(self) -> date:
        return dia_do_painel(self.data_exibida())

    # Limite de toques para chegar a um dia (ex.: execução interrompida
    # que deixou o painel longe de hoje).
    MAX_TOQUES_ATE_O_DIA = 10

    def ir_para(self, dia: date) -> None:
        """Toca nas setas até o painel mostrar 'dia'."""
        for _ in range(self.MAX_TOQUES_ATE_O_DIA):
            exibido = self.dia_exibido()

            if exibido == dia:
                return

            if exibido > dia:
                self.ir_para_dia_anterior()
            else:
                self.ir_para_dia_posterior()

        assert self.dia_exibido() == dia, (
            f"O painel não chegou a {dia:%d/%m/%Y} em "
            f"{self.MAX_TOQUES_ATE_O_DIA} toques nas setas."
        )

    # === Totais do espelho ===
    def texto_dos_totais(self) -> str:
        """
        "TOTAIS DO ESPELHO Período de 01/10/2026 a 31/10/2026": título e
        período juntos, como o texto único do iOS.
        """
        assert self._is_visible(
            self.TITULO_TOTAIS, timeout=self.LONG_TIMEOUT
        ), "O título TOTAIS DO ESPELHO não foi exibido na tela Ponto."

        partes = self._textos(self.TITULO_TOTAIS) + self._textos(
            self.PERIODO_TOTAIS
        )

        return " ".join(partes)

    def totais_abertos(self) -> bool:
        return self._esta_visivel_imediatamente(self.PRIMEIRO_ITEM_TOTAIS)

    def totais(self) -> dict[str, str | None]:
        """{"INTERJORNADA": "01:10", ...}; None se o item faltar."""
        return self._valores(self.ITENS_TOTAIS)

    def abrir_totais(self) -> None:
        self._click(
            self.BOTAO_TOTAIS,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_totais",
        )

        assert self._is_visible(
            self.PRIMEIRO_ITEM_TOTAIS, timeout=self.LONG_TIMEOUT
        ), "Os totais do espelho não abriram ao tocar na seta."

    def fechar_totais(self) -> None:
        self._click(
            self.BOTAO_TOTAIS,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_totais",
        )

        assert self._wait_for_absence(
            self.PRIMEIRO_ITEM_TOTAIS, timeout=self.LONG_TIMEOUT
        ), "Os totais do espelho continuaram abertos ao tocar na seta."
