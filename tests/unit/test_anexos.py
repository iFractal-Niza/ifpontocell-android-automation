"""
O que o report anexa nesta automação (observability.anexos): o driver
dentro das fixtures, o print e a árvore da tela na falha e o vídeo. O
resto do report é o plugin qa_observability.relatorio (testado no pacote).
"""

from types import SimpleNamespace

import pytest
from qa_observability import relatorio

from observability import anexos


class _Driver:
    def __init__(self, salva=True):
        self.salva = salva

    def save_screenshot(self, path):
        if self.salva:
            with open(path, "wb") as arquivo:
                arquivo.write(b"\x89PNG-falso")
        return self.salva


@pytest.fixture
def prints(monkeypatch, tmp_path):
    monkeypatch.setattr(
        anexos.pastas, "screenshots_dir", lambda: str(tmp_path)
    )
    return tmp_path


def _item(**funcargs):
    return SimpleNamespace(name="test_x", funcargs=funcargs)


# === Driver nas fixtures (pela configuração) ===
def test_fixture_de_driver_direto():
    driver = _Driver()

    assert relatorio.obter_sessao(_item(driver_e2e=driver)) is driver


def test_page_ou_sessao_expoe_o_driver():
    driver = _Driver()
    home = SimpleNamespace(driver=driver)

    assert relatorio.obter_sessao(_item(home_para_marcacao=home)) is driver


def test_ignora_valores_sem_driver():
    item = _item(
        test_data={"APP_LOGIN_INVALIDO": "x"},
        celular_api=SimpleNamespace(session=object()),
        algo_com_driver_none=SimpleNamespace(driver=None),
    )

    assert relatorio.obter_sessao(item) is None


# === Na falha ===
def test_falha_anexa_o_print_e_a_arvore(prints):
    driver = _Driver()
    driver.page_source = "<?xml version='1.0'?><AppiumAUT/>"
    report_extras = []

    anexos.na_falha(
        _item(driver=driver), SimpleNamespace(when="call"), report_extras
    )

    assert [extra["name"] for extra in report_extras] == [
        "Print da falha",
        "Árvore da tela",
    ]
    assert list(prints.glob("*.png"))
    assert list(prints.glob("*_arvore.xml"))


def test_print_nao_salvo_nao_e_anexado(prints):
    report_extras = []

    assert not anexos.anexar_print_da_falha(
        report_extras, _Driver(salva=False), "test_x", "call"
    )
    assert report_extras == []


def test_sem_driver_nao_anexa_nada():
    report_extras = []

    anexos.na_falha(_item(), SimpleNamespace(when="setup"), report_extras)

    assert report_extras == []


def test_sem_arvore_nao_anexa(prints):
    class SemSessao:
        @property
        def page_source(self):
            raise RuntimeError("sessão perdida")

    report_extras = []

    assert not anexos.anexar_arvore_da_tela(report_extras, SemSessao(), "x")
    assert report_extras == []


# === Vídeo ===
def test_video_so_entra_na_chamada(tmp_path):
    arquivo = tmp_path / "CT014.mp4"
    arquivo.write_bytes(b"mp4")
    item = SimpleNamespace(caminho_do_video=str(arquivo))
    report_extras = []

    anexos.na_etapa(item, SimpleNamespace(when="setup"), report_extras)
    assert report_extras == []

    anexos.na_etapa(item, SimpleNamespace(when="call"), report_extras)
    assert report_extras[0]["name"] == "Vídeo do teste"


# === Plugins no conftest ===
def test_report_e_o_plugin_do_pacote():
    import conftest

    assert "qa_observability.relatorio" in conftest.pytest_plugins
    assert "qa_observability.tabela" in conftest.pytest_plugins
