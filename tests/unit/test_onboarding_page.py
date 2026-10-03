"""
Passagem pelo boas-vindas do onboarding
(OnboardingPage._passar_pelo_boas_vindas): toca PRÓXIMO até a tela
seguinte aparecer. As telas são reconhecidas pelo contêiner: o botão de
avançar é o mesmo resource-id no boas-vindas e nas informações
importantes.
"""

from unittest.mock import Mock

from pages.autenticacao.onboarding_page import OnboardingPage


def _pagina(visiveis_por_toque: list[set]) -> OnboardingPage:
    """
    visiveis_por_toque[n]: locators visíveis depois do toque n+1 (o
    estado não muda até o toque seguinte).
    """
    pagina = OnboardingPage(Mock())
    pagina.DEFAULT_TIMEOUT = 0.01
    pagina.POLL_FREQUENCY = 0
    estado = {"toques": 0}

    def tocar():
        estado["toques"] += 1

    def visivel(locator):
        return locator in visiveis_por_toque[estado["toques"] - 1]

    pagina.clicar_proximo_boas_vindas = tocar
    pagina._esta_visivel_imediatamente = visivel
    pagina._estado = estado
    return pagina


def test_um_toque_basta_quando_a_tela_seguinte_aparece():
    pagina = _pagina([{OnboardingPage.TELA_INFORMACOES_IMPORTANTES}])

    pagina._passar_pelo_boas_vindas()

    assert pagina._estado["toques"] == 1


def test_botao_repetido_nao_conta_como_tela_seguinte():
    # O botão das informações importantes é o mesmo do boas-vindas: só o
    # contêiner diz que a tela mudou.
    pagina = _pagina(
        [
            {
                OnboardingPage.TELA_BOAS_VINDAS,
                OnboardingPage.BOTAO_INICIAR_CONFIGURACAO,
            },
            {OnboardingPage.TELA_INFORMACOES_IMPORTANTES},
        ]
    )

    pagina._passar_pelo_boas_vindas()

    assert pagina._estado["toques"] == 2


def test_toca_de_novo_se_o_boas_vindas_continua():
    pagina = _pagina(
        [
            {OnboardingPage.TELA_BOAS_VINDAS},
            {OnboardingPage.TELA_CONFIGURAR_APLICATIVO},
        ]
    )

    pagina._passar_pelo_boas_vindas()

    assert pagina._estado["toques"] == 2


def test_para_no_limite_de_toques():
    pagina = _pagina(
        [{OnboardingPage.TELA_BOAS_VINDAS}]
        * OnboardingPage.MAX_TOQUES_BOAS_VINDAS
    )

    pagina._passar_pelo_boas_vindas()

    assert pagina._estado["toques"] == OnboardingPage.MAX_TOQUES_BOAS_VINDAS
