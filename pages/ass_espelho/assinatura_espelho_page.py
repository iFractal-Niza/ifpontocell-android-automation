from functools import cached_property
from time import monotonic, sleep

from qa_report.evidencias import capturar_evidencia
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)

from pages.alertas import AlertaAppMixin
from pages.android_locators import (
    android_id_prefixo,
    android_pendente,
    android_text_contains,
)
from pages.ass_espelho.impressao_espelho_page import ImpressaoEspelhoPage
from pages.base_page import BasePage
from pages.menu_page import MenuLateralPage
from pages.navegacao import VoltarParaHomeMixin
from utils.ass_espelho import EspelhoAssinatura
from utils.periodo import extrair_intervalo


class AssinaturaEspelhoPage(AlertaAppMixin, VoltarParaHomeMixin, BasePage):
    """
    Page: tela "Assinatura do Espelho" (menu lateral -> ASSINATURA DO
    ESPELHO).

    Um item por mês fechado, com ASSINAR (ou "ASSINADO", mesmo botão) e
    o botão de expandir, que mostra os totais do período e o botão de
    visualizar (abre a ImpressaoEspelhoPage). Sem nenhum fechamento, o
    app mostra o alerta "Sem assinatura".
    """

    SCREEN_NAME = "assinatura_espelho"
    NOME_TELA = "Assinatura do Espelho"

    # PENDENTE: ids da tela no Android (iOS: assinatura.*). No iOS o
    # período vem do name da célula ("assinatura.cellCompetencia_Período
    # de 01/08/2026 a 31/08/2026"); no Android ids de item costumam ser
    # fixos, e o período pode precisar vir dos textos da célula.
    TABELA = android_pendente("assinatura_lista")
    CELULA = android_id_prefixo("PENDENTE_assinatura_item")
    LABEL_COMPETENCIA = android_pendente("assinatura_lblCompetencia")

    # Mesmo botão para os dois estados: texto "ASSINAR" ou "ASSINADO".
    BOTAO_ASSINAR = android_pendente("assinatura_btnAssinar")
    BOTAO_EXPANDIR = android_pendente("assinatura_btnExpandir")

    # Conteúdo expandido (um item expandido por vez).
    BOTAO_VISUALIZAR = android_pendente("assinaturaContent_btnVisualizar")

    TOTAIS = android_text_contains("TOTAIS DO ESPELHO")

    ROTULO_ASSINADO = "ASSINADO"
    MENSAGEM_SEM_ASSINATURA = "Sem assinatura"

    # === Composição ===
    @cached_property
    def menu_lateral(self) -> MenuLateralPage:
        return MenuLateralPage(self.driver)

    # === Acesso ===
    def acessar(self) -> bool:
        """
        Abre a tela pelo menu lateral.

        Retorna False quando o app mostra "Sem assinatura" (nenhum
        fechamento para o usuário); o alerta é fechado e a tela fica
        vazia. True quando a lista de espelhos é exibida.
        """
        self.menu_lateral.acessar(MenuLateralPage.ASSINATURA_ESPELHO)

        limite = monotonic() + self.LONG_TIMEOUT

        while monotonic() < limite:
            if self.alerta_visivel(
                self.MENSAGEM_SEM_ASSINATURA,
                timeout=0,
            ):
                # Evidência antes do OK: depois dele o alerta some e o
                # teste que depende de massa é pulado.
                capturar_evidencia(
                    self.driver,
                    "Alerta 'Sem assinatura' (nenhum espelho fechado)",
                )
                self.confirmar_alerta(
                    self.MENSAGEM_SEM_ASSINATURA,
                    acao="abrir a Assinatura do Espelho",
                )
                return False

            if self._esta_visivel_imediatamente(self.CELULA):
                return True

            sleep(self.POLL_FREQUENCY)

        raise AssertionError(
            "A tela 'Assinatura do Espelho' não exibiu nem a lista de "
            "espelhos nem o alerta 'Sem assinatura'. Se a opção não "
            "aparece no menu, verifique app_config.bts.assinatura_espelho."
            "visible no servidor."
        )

    def esta_na_tela(self, timeout: float | None = None) -> bool:
        return self._is_visible(self.TABELA, timeout=timeout)

    # === Espelhos ===
    def espelhos(self) -> list[EspelhoAssinatura]:
        """Espelhos exibidos, com período e status de assinatura."""
        lidos = []

        for celula in self.driver.find_elements(*self.CELULA):
            try:
                competencia = (
                    celula.find_element(*self.LABEL_COMPETENCIA).text or ""
                ).strip()
                # No iOS, o name da célula; no Android, o resource-id
                # (PENDENTE: ver TABELA).
                periodo = extrair_intervalo(
                    celula.get_attribute("resource-id")
                )
                rotulo = celula.find_element(*self.BOTAO_ASSINAR).text
            except (NoSuchElementException, StaleElementReferenceException):
                continue

            lidos.append(
                EspelhoAssinatura(
                    competencia=competencia,
                    periodo=periodo,
                    assinado=(rotulo or "").strip() == self.ROTULO_ASSINADO,
                )
            )

        self._log_info(
            "Espelhos listados",
            event="espelhos_listed",
            espelhos=[
                f"{e.competencia} ({'assinado' if e.assinado else 'pendente'})"
                for e in lidos
            ],
        )

        return lidos

    def _celula(self, competencia: str):
        for celula in self.driver.find_elements(*self.CELULA):
            try:
                texto = celula.find_element(*self.LABEL_COMPETENCIA).text
            except (NoSuchElementException, StaleElementReferenceException):
                continue

            if (texto or "").strip() == competencia:
                return celula

        raise AssertionError(
            f"Espelho de {competencia!r} não encontrado na lista."
        )

    def esta_assinado(self, competencia: str) -> bool:
        rotulo = (
            self._celula(competencia).find_element(*self.BOTAO_ASSINAR).text
        )

        return (rotulo or "").strip() == self.ROTULO_ASSINADO

    # === Expandir e visualizar ===
    def expandir(self, espelho: EspelhoAssinatura) -> str:
        """
        Expande o espelho e devolve o texto dos totais, conferindo que é
        do mesmo período.
        """
        self._celula(espelho.competencia).find_element(
            *self.BOTAO_EXPANDIR
        ).click()

        totais = self._get_text(
            self.TOTAIS,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="totais_espelho",
        )

        assert extrair_intervalo(totais) == espelho.periodo, (
            f"Os totais exibidos não são do período de {espelho.competencia} "
            f"({espelho.periodo}): {totais!r}."
        )

        return totais

    def visualizar(self, espelho: EspelhoAssinatura) -> ImpressaoEspelhoPage:
        """
        Abre a Impressão do espelho já expandido e confere o mês.
        """
        self._click(
            self.BOTAO_VISUALIZAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_visualizar_espelho",
        )

        impressao = ImpressaoEspelhoPage(self.driver)

        assert impressao.esta_aberta(
            espelho.competencia,
            timeout=self.LONG_TIMEOUT,
        ), f"A Impressão do espelho de {espelho.competencia} não foi exibida."

        return impressao
