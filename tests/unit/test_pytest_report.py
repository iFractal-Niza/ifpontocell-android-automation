"""
Descoberta do driver para o screenshot de falha
(observability.pytest_report.obter_driver_ativo).
"""

import re
from pathlib import Path
from types import SimpleNamespace

from observability.pytest_report import (
    corrigir_troca_de_video,
    marcar_pulados,
    obter_driver_ativo,
    pytest_unconfigure,
)


class _Driver:
    def save_screenshot(self, path):  # pragma: no cover - só a interface
        return True


def _item(**funcargs):
    return SimpleNamespace(funcargs=funcargs)


def test_fixture_de_driver_direto():
    driver = _Driver()

    assert obter_driver_ativo(_item(driver_e2e=driver)) is driver


def test_page_ou_sessao_expoe_o_driver():
    driver = _Driver()
    home = SimpleNamespace(driver=driver)

    assert obter_driver_ativo(_item(home_para_marcacao=home)) is driver


def test_fixture_fora_da_lista_tambem_e_encontrada():
    # Caso real: home_autenticada (Holerite/Informe) ficou sem
    # screenshot porque não estava na lista de fixtures conhecidas.
    driver = _Driver()

    item = _item(home_autenticada=SimpleNamespace(driver=driver))

    assert obter_driver_ativo(item) is driver


def test_fixtures_conhecidas_tem_preferencia():
    preferido, outro = _Driver(), _Driver()

    item = _item(
        qualquer_coisa=SimpleNamespace(driver=outro),
        driver_e2e=preferido,
    )

    assert obter_driver_ativo(item) is preferido


def test_ignora_valores_sem_driver():
    item = _item(
        test_data={"APP_LOGIN_INVALIDO": "x"},
        app_pin="1234",
        celular_api=SimpleNamespace(session=object()),
        algo_com_driver_none=SimpleNamespace(driver=None),
    )

    assert obter_driver_ativo(item) is None


# === Imagens embutidas (anexar_imagem) ===
def test_imagem_e_embutida_em_base64_e_ganha_legenda(tmp_path):
    import base64

    from observability import pytest_report

    png = tmp_path / "print.png"
    png.write_bytes(b"\x89PNG-falso")
    report_extras = []

    anexou = pytest_report.anexar_imagem(
        report_extras, str(png), "Print da falha"
    )

    assert anexou is True
    assert report_extras[0]["format_type"] == "image"
    # Conteúdo embutido, não o caminho da máquina que rodou.
    assert (
        report_extras[0]["content"]
        == base64.b64encode(b"\x89PNG-falso").decode()
    )
    assert report_extras[0]["name"] == "Print da falha"


def test_arquivo_ausente_nao_anexa(tmp_path):
    from observability import pytest_report

    report_extras = []

    assert (
        pytest_report.anexar_imagem(
            report_extras, str(tmp_path / "nao.png"), "x"
        )
        is False
    )
    assert report_extras == []


# === Falha no setup: driver numa fixture intermediária ===
def _definicao(valor, erro=None):
    return SimpleNamespace(cached_result=(valor, None, erro))


def test_driver_de_fixture_montada_fora_do_funcargs():
    # Caso real: home_autenticada falha no setup; a sessão que ela usa
    # já subiu, mas não está em funcargs (o teste não a pede direto).
    driver = _Driver()
    item = SimpleNamespace(
        funcargs={},
        _request=SimpleNamespace(
            _fixture_defs={
                "test_data": _definicao({"pin": "1234"}),
                "app_session_e2e_registro_ponto": _definicao(
                    SimpleNamespace(driver=driver)
                ),
            }
        ),
    )

    assert obter_driver_ativo(item) is driver


def test_fixture_que_falhou_nao_conta():
    item = SimpleNamespace(
        funcargs={},
        _request=SimpleNamespace(
            _fixture_defs={
                "home_autenticada": _definicao(
                    None, erro=(RuntimeError, RuntimeError("x"), None)
                ),
            }
        ),
    )

    assert obter_driver_ativo(item) is None


def test_estrutura_interna_diferente_nao_quebra():
    item = SimpleNamespace(funcargs={}, _request=SimpleNamespace())

    assert obter_driver_ativo(item) is None


# === Árvore da tela na falha ===
def test_arvore_da_tela_e_anexada_e_salva(tmp_path, monkeypatch):
    from observability import pytest_report

    monkeypatch.setattr(pytest_report, "SCREENSHOTS_DIR", str(tmp_path))
    driver = SimpleNamespace(page_source="<?xml version='1.0'?><AppiumAUT/>")
    report_extras = []

    assert pytest_report.anexar_arvore_da_tela(report_extras, driver, "test_x")
    assert report_extras[0]["name"] == "Árvore da tela"
    assert list(tmp_path.glob("*_arvore.xml"))


def test_sem_arvore_nao_anexa(monkeypatch):
    from observability import pytest_report

    class SemSessao:
        @property
        def page_source(self):
            raise RuntimeError("sessão perdida")

    report_extras = []

    assert (
        pytest_report.anexar_arvore_da_tela(report_extras, SemSessao(), "x")
        is False
    )
    assert report_extras == []


# === Aviso de pulados (o Makefile abre o report) ===
def test_pulados_grava_a_quantidade(tmp_path):
    arquivo = tmp_path / ".pulados"

    marcar_pulados(3, str(arquivo))

    assert arquivo.read_text(encoding="utf-8") == "3"


def test_sem_pulados_apaga_o_aviso(tmp_path):
    arquivo = tmp_path / ".pulados"
    arquivo.write_text("2", encoding="utf-8")

    marcar_pulados(0, str(arquivo))

    assert not arquivo.exists()


# === Correção da troca de vídeo no app.js do pytest-html ===
def _app_js_da_lib():
    import pytest_html

    return (
        Path(pytest_html.__file__).parent / "resources" / "app.js"
    ).read_text(encoding="utf-8")


def test_troca_de_video_ganha_load_no_app_js_da_lib():
    # Usa o app.js instalado: se uma versão nova da lib mudar o trecho,
    # o teste avisa.
    corrigido = corrigir_troca_de_video(_app_js_da_lib())

    assert re.search(
        r"sourceEl\.src = media\.path\n\n.*\n.*\n\s*videoEl\.load\(\)\n",
        corrigido,
    )


def test_correcao_da_troca_de_video_nao_duplica():
    uma_vez = corrigir_troca_de_video(_app_js_da_lib())

    assert corrigir_troca_de_video(uma_vez) == uma_vez
    assert uma_vez.count("videoEl.load()") == 1


def test_unconfigure_corrige_o_html_gravado(tmp_path):
    relatorio = tmp_path / "report.html"
    relatorio.write_text(
        "<script>\n    sourceEl.src = media.path\n</script>",
        encoding="utf-8",
    )

    pytest_unconfigure(
        SimpleNamespace(option=SimpleNamespace(htmlpath=str(relatorio)))
    )

    assert "    videoEl.load()\n" in relatorio.read_text(encoding="utf-8")
