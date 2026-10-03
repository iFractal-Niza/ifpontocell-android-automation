"""
Textos do painel da tela Ponto (utils.ponto): data do dia, marcações,
período e totais do espelho.
"""

from datetime import date

import pytest

from utils.ponto import (
    data_do_painel,
    dia_do_painel,
    e_total_em_horas,
    horario_da_marcacao,
    ler_jornada,
    mesma_data,
    periodo_dos_totais,
    problema_no_periodo,
    tipo_da_marcacao,
)


@pytest.mark.parametrize(
    ("dia", "esperado"),
    [
        (date(2026, 10, 1), "Quinta, 01 de Outubro de 2026"),
        (date(2026, 9, 29), "Terça, 29 de Setembro de 2026"),
        (date(2026, 10, 3), "Sábado, 03 de Outubro de 2026"),
        (date(2026, 3, 1), "Domingo, 01 de Março de 2026"),
    ],
)
def test_data_do_painel(dia, esperado):
    assert data_do_painel(dia) == esperado


def test_mesma_data_ignora_acento_e_caixa():
    assert mesma_data(
        "SABADO, 03 de outubro de 2026", "Sábado, 03 de Outubro de 2026"
    )
    assert not mesma_data(
        "Sexta, 02 de Outubro de 2026", "Sábado, 03 de Outubro de 2026"
    )


@pytest.mark.parametrize(
    ("texto", "horario"),
    [
        ("10:47 horas", "10:47"),
        ("10:47e horas", "10:47"),
        ("14:32:06", None),
        ("ATIVIDADE LABORAL, 3h + 24min", None),
    ],
)
def test_horario_da_marcacao(texto, horario):
    assert horario_da_marcacao(texto) == horario


def test_periodo_como_a_arvore_mostra():
    texto = "TOTAIS DO ESPELHO \\n Período de 01setembro2026 a 30setembro2026"

    assert periodo_dos_totais(texto) == (date(2026, 9, 1), date(2026, 9, 30))


def test_periodo_que_vira_o_mes_e_o_ano():
    assert periodo_dos_totais("Período de 22dezembro2026 a 21janeiro2027") == (
        date(2026, 12, 22),
        date(2027, 1, 21),
    )


def test_periodo_como_a_tela_mostra():
    assert periodo_dos_totais("Período de 22/09/2026 a 21/10/2026") == (
        date(2026, 9, 22),
        date(2026, 10, 21),
    )


def test_periodo_ilegivel_falha_mostrando_o_texto():
    with pytest.raises(ValueError, match="TOTAIS DO ESPELHO"):
        periodo_dos_totais("TOTAIS DO ESPELHO")


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("01:10", True),
        ("174:30", True),
        ("1:10", True),
        ("1h10", False),
        ("", False),
    ],
)
def test_total_em_horas(texto, esperado):
    assert e_total_em_horas(texto) is esperado


def test_dia_do_painel_le_a_data_exibida():
    assert dia_do_painel("Sexta, 02 de Outubro de 2026") == date(2026, 10, 2)
    assert dia_do_painel("Domingo, 01 de MARÇO de 2026") == date(2026, 3, 1)


def test_dia_do_painel_ilegivel_falha_mostrando_o_texto():
    with pytest.raises(ValueError, match="Amanhã"):
        dia_do_painel("Amanhã")


@pytest.mark.parametrize(
    ("inicio", "fim", "hoje", "ok"),
    [
        # Caso real: o espelho de setembro ainda aparece em 01/10.
        (date(2026, 9, 1), date(2026, 9, 30), date(2026, 10, 1), True),
        (date(2026, 9, 22), date(2026, 10, 21), date(2026, 10, 1), True),
        (date(2026, 2, 1), date(2026, 2, 28), date(2026, 3, 1), True),
        # Começa no futuro.
        (date(2026, 11, 1), date(2026, 11, 30), date(2026, 10, 1), False),
        # Desatualizado: terminou há mais de um mês.
        (date(2026, 7, 1), date(2026, 7, 31), date(2026, 10, 1), False),
        # Não é um mês.
        (date(2026, 9, 1), date(2026, 9, 10), date(2026, 9, 5), False),
    ],
)
def test_periodo_coerente(inicio, fim, hoje, ok):
    assert (problema_no_periodo(inicio, fim, hoje) is None) is ok


def test_jornada_aceita_espaco_ou_virgula():
    esperado = ["08:00", "12:00", "13:00", "18:00"]

    assert ler_jornada("08:00 12:00 13:00 18:00") == esperado
    assert ler_jornada("08:00, 12:00,13:00 , 18:00") == esperado
    assert ler_jornada("") == []


def test_jornada_fora_do_formato_diz_qual_horario():
    with pytest.raises(ValueError, match="8:00"):
        ler_jornada("8:00 12:00")


@pytest.mark.parametrize(
    ("texto", "tipo"),
    [
        ("10:47e horas", "e"),
        ("10:47i horas", "i"),
        ("10:47 horas", ""),
        ("14:32:06", None),
    ],
)
def test_tipo_da_marcacao(texto, tipo):
    assert tipo_da_marcacao(texto) == tipo
