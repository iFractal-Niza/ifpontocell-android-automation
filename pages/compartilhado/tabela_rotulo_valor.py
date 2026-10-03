from dataclasses import dataclass, field

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from pages.android_locators import android_id
from utils.texto import normalizar_texto


@dataclass
class ConteudoTabela:
    # Todos os textos da tela, na ordem, normalizados.
    textos: list[str] = field(default_factory=list)
    # Pares rótulo + valor: {"VERSÃO": "2.7.3", "COLABORADOR": ...}.
    campos: dict[str, str] = field(default_factory=dict)


def agrupar_rotulo_valor(textos: list[str]) -> list[list[str]]:
    """
    Agrupa os textos da tela, na ordem, como as células do iOS: rótulo
    em caixa alta seguido de um valor que não é rótulo vira [rótulo,
    valor]; o resto, [texto].
    """
    celulas: list[list[str]] = []
    indice = 0

    while indice < len(textos):
        texto = textos[indice]
        seguinte = textos[indice + 1] if indice + 1 < len(textos) else None

        if texto.isupper() and seguinte and not seguinte.isupper():
            celulas.append([texto, seguinte])
            indice += 2
            continue

        celulas.append([texto])
        indice += 1

    return celulas


class TabelaRotuloValorMixin:
    """
    Leitura de telas de rótulo + valor (Dados Pessoais, Sobre o
    aplicativo), sem ids técnicos para os valores.

    No iOS cada célula da tabela traz rótulo e valor. No Android não há
    células: lê os TextViews da área de conteúdo (sem barra de cima e
    abas), na ordem, e agrupa rótulo em caixa alta + valor
    (agrupar_rotulo_valor). Rola até não aparecer texto novo.

    PENDENTE: estrutura deduzida do iOS; confirmar no Inspector
    (PENDENCIAS_LOCATORS_ANDROID.md).

    Requer os métodos da BasePage. Declarar antes de BasePage nas bases.
    """

    # Área de conteúdo das telas (confirmado na Home): fora dela ficam a
    # barra de cima e as abas.
    TABELA = android_id("nav_host_fragment")
    CLASSE_TEXTO = "android.widget.TextView"

    # Quantas vezes rolar atrás de textos novos. 0 para tela que cabe
    # inteira (lê uma vez, sem rolar).
    MAX_ROLAGENS = 4

    def _textos_da_tela(self) -> list[str]:
        textos = []

        for elemento in self.driver.find_element(*self.TABELA).find_elements(
            AppiumBy.CLASS_NAME, self.CLASSE_TEXTO
        ):
            try:
                texto = normalizar_texto(elemento.text)
            except StaleElementReferenceException:
                continue

            if texto:
                textos.append(texto)

        return textos

    def _textos_das_celulas(self) -> list[list[str]]:
        return agrupar_rotulo_valor(self._textos_da_tela())

    def _rolar_para_baixo(self) -> None:
        try:
            tabela = self.driver.find_element(*self.TABELA)
            self.driver.execute_script(
                "mobile: scrollGesture",
                {"elementId": tabela.id, "direction": "down", "percent": 0.75},
            )
        except (NoSuchElementException, WebDriverException):
            pass

    def ler_conteudo(self) -> ConteudoTabela:
        """
        Lê todas as células, rolando (até MAX_ROLAGENS vezes) até não
        aparecer célula nova.
        """
        conteudo = ConteudoTabela()
        vistas: set[tuple[str, ...]] = set()

        for leitura in range(self.MAX_ROLAGENS + 1):
            novas = [
                celula
                for celula in self._textos_das_celulas()
                if tuple(celula) not in vistas
            ]

            if not novas and vistas:
                break

            for celula in novas:
                vistas.add(tuple(celula))

                if len(celula) == 2 and celula[0].isupper():
                    conteudo.campos[celula[0]] = celula[1]

                conteudo.textos.extend(
                    texto for texto in celula if texto not in conteudo.textos
                )

            if leitura < self.MAX_ROLAGENS:
                self._rolar_para_baixo()

        self._log_info(
            "Conteúdo da tabela lido",
            event="table_content_read",
            tela=self.SCREEN_NAME,
            campos=conteudo.campos,
        )

        return conteudo
