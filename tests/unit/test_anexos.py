"""
O que o report anexa nesta automação: os anexos e o vídeo pelo driver do
Appium vêm do pacote (qa_observability.appium, testado lá); aqui, só a
configuração (observability.automacao).
"""

from types import SimpleNamespace

from qa_observability import relatorio
from qa_observability.appium import anexos
from qa_observability.automacao import atual


class _Driver:
    def save_screenshot(self, path):  # pragma: no cover - só a interface
        return True


def _item(**funcargs):
    return SimpleNamespace(name="test_x", funcargs=funcargs)


def test_configuracao_usa_os_anexos_do_appium():
    automacao = atual()

    assert automacao.sessao_de is anexos.driver_de
    assert automacao.na_falha is anexos.na_falha
    assert automacao.na_etapa is anexos.na_etapa


def test_fixtures_conhecidas_tem_preferencia():
    preferido, outro = _Driver(), _Driver()
    item = _item(
        qualquer_coisa=SimpleNamespace(driver=outro),
        driver_e2e=preferido,
    )

    assert relatorio.obter_sessao(item) is preferido


def test_page_ou_sessao_expoe_o_driver():
    driver = _Driver()
    home = SimpleNamespace(driver=driver)

    assert relatorio.obter_sessao(_item(home_para_marcacao=home)) is driver


def test_report_e_o_video_sao_plugins_do_pacote():
    import conftest

    for plugin in (
        "qa_observability.relatorio",
        "qa_observability.tabela",
        "qa_observability.appium.video",
    ):
        assert plugin in conftest.pytest_plugins
