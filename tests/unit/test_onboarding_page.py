"""
Passagem pelo boas-vindas do onboarding
(OnboardingPage._passar_pelo_boas_vindas): toca PRÓXIMO até a tela
seguinte aparecer.
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
    pagina = _pagina([{OnboardingPage.BOTAO_INICIAR_CONFIGURACAO}])

    pagina._passar_pelo_boas_vindas()

    assert pagina._estado["toques"] == 1


def test_mesmo_id_nas_duas_telas_sai_no_primeiro_toque():
    # Android: PRÓXIMO do boas-vindas e INICIAR das informações
    # importantes têm o mesmo resource-id (btn_confirmar_informacao).
    # Visível depois do toque, ele já conta como a tela seguinte: a
    # repetição de toques do iOS não acontece (PENDENCIAS_LOCATORS_ANDROID.md).
    assert (
        OnboardingPage.BOTAO_PROXIMO_BOAS_VINDAS
        == OnboardingPage.BOTAO_INICIAR_CONFIGURACAO
    )

    pagina = _pagina([{OnboardingPage.BOTAO_PROXIMO_BOAS_VINDAS}] * 4)

    pagina._passar_pelo_boas_vindas()

    assert pagina._estado["toques"] == 1
