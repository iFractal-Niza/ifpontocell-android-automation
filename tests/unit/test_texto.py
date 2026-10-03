"""
Normalização de textos lidos da tela (utils.texto).
"""

from utils.texto import normalizar_texto


def test_traco_tipografico_vira_hifen():
    assert normalizar_texto("145 – SAÚDE — SP") == "145 - SAÚDE - SP"


def test_quebras_e_espacos_viram_um_espaco():
    assert (
        normalizar_texto("  RUA FIACÃO\n DA   SAÚDE  ")
        == "RUA FIACÃO DA SAÚDE"
    )


def test_acentos_e_maiusculas_sao_mantidos():
    assert normalizar_texto("Versão iFractal®") == "Versão iFractal®"


def test_vazio_ou_none():
    assert normalizar_texto("") == ""
    assert normalizar_texto(None) == ""


def test_espaco_nao_separavel_vira_espaco_comum():
    # Caso real: título da Privacidade com espaço especial.
    assert normalizar_texto("3.\u00a0Os direitos dos titulares") == (
        "3. Os direitos dos titulares"
    )


def test_acento_decomposto_vira_composto():
    decomposto = "Introduc\u0327a\u0303o"  # ç e ã em duas partes

    assert normalizar_texto(decomposto) == "Introdução"
