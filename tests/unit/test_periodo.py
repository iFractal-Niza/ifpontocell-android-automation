from datetime import date

import pytest

from utils.periodo import interpretar_competencia, interpretar_exercicio


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Janeiro 2026", date(2026, 1, 1)),
        ("Setembro 2026", date(2026, 9, 1)),
        ("Dezembro 2025", date(2025, 12, 1)),
        ("Março 2026", date(2026, 3, 1)),
        ("MARÇO 2026", date(2026, 3, 1)),
        ("marco 2026", date(2026, 3, 1)),
        ("  Julho   2026 ", date(2026, 7, 1)),
    ],
)
def test_interpreta_competencia(texto, esperado):
    assert interpretar_competencia(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    ["", None, "Setembro", "2026", "Setembro/2026", "Mês 2026", "Abril 26x"],
)
def test_formato_invalido_falha_mostrando_o_texto(texto):
    with pytest.raises(ValueError, match="Mês AAAA"):
        interpretar_competencia(texto)


def test_ordenacao_por_data_e_nao_por_texto():
    # Em ordem alfabética, "Agosto" viria antes de "Setembro" e
    # "Dezembro 2025" depois de "Abril 2026": só a data ordena certo.
    textos = ["Dezembro 2025", "Setembro 2026", "Agosto 2026", "Abril 2026"]

    ordenadas = sorted(textos, key=interpretar_competencia, reverse=True)

    assert ordenadas == [
        "Setembro 2026",
        "Agosto 2026",
        "Abril 2026",
        "Dezembro 2025",
    ]


# === Exercício (Informe de Rendimentos) ===
@pytest.mark.parametrize(
    "texto, esperado",
    [("IR-2026", 2026), ("IR-2025", 2025), (" ir-2024 ", 2024)],
)
def test_interpreta_exercicio(texto, esperado):
    assert interpretar_exercicio(texto) == esperado


@pytest.mark.parametrize(
    "texto", ["", None, "2026", "IR 2026", "IR-26", "IRPF-2026", "IR-2026x"]
)
def test_exercicio_invalido_falha_mostrando_o_texto(texto):
    with pytest.raises(ValueError, match="IR-AAAA"):
        interpretar_exercicio(texto)
