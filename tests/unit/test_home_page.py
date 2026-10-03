"""
Lógica da HomePage que não depende da tela: leitura da data/hora do
registro. O texto é injetado no lugar do _get_text.
"""

from datetime import datetime, timedelta

import pytest

from pages.home_page import HomePage


@pytest.fixture
def home(monkeypatch):
    pagina = HomePage(driver=None)

    def com_texto(texto: str) -> HomePage:
        monkeypatch.setattr(pagina, "_get_text", lambda *a, **k: texto)
        return pagina

    return com_texto


def test_interpreta_data_hora_exibida(home):
    pagina = home("Dia 28/09/2026 às 10:23:52")

    assert pagina.obter_data_hora_registro() == datetime(
        2026, 9, 28, 10, 23, 52
    )


def test_texto_fora_do_formato_falha_com_o_texto_lido(home):
    pagina = home("Registrado em 28/09")

    with pytest.raises(AssertionError, match="Registrado em 28/09"):
        pagina.obter_data_hora_registro()


def test_hora_recente_dentro_da_tolerancia(home):
    agora = datetime.now() - timedelta(seconds=30)
    pagina = home(f"Dia {agora:%d/%m/%Y} às {agora:%H:%M:%S}")

    assert pagina.validar_hora_registro_recente(tolerancia_segundos=120)


def test_hora_antiga_fora_da_tolerancia(home):
    antiga = datetime.now() - timedelta(minutes=10)
    pagina = home(f"Dia {antiga:%d/%m/%Y} às {antiga:%H:%M:%S}")

    assert not pagina.validar_hora_registro_recente(tolerancia_segundos=120)


# === Reconhecimento da Home ===
def _home_com_visiveis(*visiveis) -> HomePage:
    pagina = HomePage(driver=None)
    pagina._esta_visivel_imediatamente = lambda locator: locator in visiveis
    return pagina


def test_registrar_visivel_e_home():
    pagina = _home_com_visiveis(HomePage.BOTAO_REGISTRAR)

    assert pagina._home_esta_pronta_imediatamente()


def test_so_a_aba_ponto_nao_e_home():
    # Caso real: lista da Assinatura do Espelho, com a barra de abas.
    pagina = _home_com_visiveis(
        HomePage.ABA_PONTO, HomePage.ABA_PONTO_FALLBACK
    )

    assert not pagina._home_esta_pronta_imediatamente()


def test_alerta_de_atualizacao_cobrindo_nao_e_home():
    pagina = _home_com_visiveis(
        HomePage.BOTAO_REGISTRAR, HomePage.POPUP_ATUALIZACAO_ALERTA
    )

    assert not pagina._home_esta_pronta_imediatamente()
