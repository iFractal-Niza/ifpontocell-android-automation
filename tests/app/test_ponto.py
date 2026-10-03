"""
Tela Ponto (aba PONTO da Home): navegação entre os dias e totais do
espelho.

Roda depois do registro de ponto, na mesma sessão, partindo da Home. As
datas esperadas são calculadas a partir de hoje; os números (marcações,
cards, totais) mudam todo dia e não são fixados: confere-se que existem,
o formato e que o painel troca de dia de verdade.
"""

from datetime import date, timedelta

import pytest

from pages.ponto.painel_ponto_page import PainelPontoPage
from utils.ponto import (
    data_do_painel,
    e_total_em_horas,
    mesma_data,
    periodo_dos_totais,
    problema_no_periodo,
)

# Toques nas setas a partir de hoje: dois dias para trás, três para a
# frente (passa de hoje e chega a amanhã) e um para trás, terminando hoje.
SEQUENCIA = (
    ("anterior", -1),
    ("anterior", -2),
    ("posterior", -1),
    ("posterior", 0),
    ("posterior", 1),
    ("anterior", 0),
)

# Num dia futuro, nada foi trabalhado: o card da jornada mostra "---" e
# o status é a escala do dia.
SEM_JORNADA = "---"
ESCALADO = "ESCALADO"
FOLGA = "FOLGA"


def _conferir_data(exibida: str, dia: date) -> None:
    esperada = data_do_painel(dia)

    assert mesma_data(exibida, esperada), (
        f"O painel mostra {exibida!r}; esperado {esperada!r}."
    )


def _conferir_dia_futuro(
    painel: PainelPontoPage, exibida: str, jornada: list[str]
) -> None:
    """
    Dia futuro: sem horas trabalhadas ("---"), status ESCALADO ou FOLGA
    e, nos dois casos, os horários da escala do usuário (comparados com
    APP_JORNADA, se configurada).
    """
    cards = painel.cards()
    status = cards["STATUS DO MOMENTO"]

    assert cards["JORNADA DIÁRIA"] == SEM_JORNADA, (
        f"{exibida}: dia futuro com jornada diária "
        f"{cards['JORNADA DIÁRIA']!r} (esperado {SEM_JORNADA!r})."
    )

    assert status in (ESCALADO, FOLGA), (
        f"{exibida}: status {status!r} num dia futuro (esperado "
        f"{ESCALADO} ou {FOLGA})."
    )

    if jornada:
        assert painel.marcacoes() == jornada, (
            f"{exibida}: os horários exibidos {painel.marcacoes()} não são "
            f"a jornada do usuário (APP_JORNADA: {jornada})."
        )


@pytest.mark.ct("CT011")
@pytest.mark.regression
def test_ponto_navegar_entre_os_dias(home_autenticada, jornada_do_usuario):
    """
    Valida a troca de dia pelas setas do painel da tela Ponto e que os
    detalhes acompanham o dia exibido.

    Fronteira: Home (hoje) -> < < (hoje-2) -> > > > (amanhã) -> < (hoje).
    Em cada toque, confere a data. Amanhã: sem horas trabalhadas,
    ESCALADO ou FOLGA, com os horários da jornada do usuário. De volta a
    hoje, as marcações são as do início e os cards estão preenchidos.
    Termina sempre em hoje, mesmo se falhar no meio.
    """
    painel = PainelPontoPage(home_autenticada.driver)
    hoje = date.today()

    _conferir_data(painel.data_exibida(), hoje)

    marcacoes_de_hoje = painel.marcacoes()

    try:
        for seta, deslocamento in SEQUENCIA:
            exibida = (
                painel.ir_para_dia_anterior()
                if seta == "anterior"
                else painel.ir_para_dia_posterior()
            )

            _conferir_data(exibida, hoje + timedelta(days=deslocamento))

            if deslocamento > 0:
                _conferir_dia_futuro(painel, exibida, jornada_do_usuario)

        assert painel.marcacoes() == marcacoes_de_hoje, (
            "De volta a hoje, as marcações não são as do início: "
            f"{painel.marcacoes()} (início: {marcacoes_de_hoje})."
        )

        sem_valor = [
            rotulo for rotulo, valor in painel.cards().items() if not valor
        ]
        assert not sem_valor, f"Cards de hoje sem valor: {sem_valor}."

    finally:
        # Os próximos testes (totais, registro com geo) partem de hoje.
        painel.ir_para(hoje)


@pytest.mark.ct("CT012")
@pytest.mark.regression
def test_ponto_totais_do_espelho(home_autenticada):
    """
    Valida os totais do espelho da tela Ponto: período de um mês e
    atual, e, abertos, os cinco totais em horas; fechados, somem.

    Fronteira: Home (hoje) -> período dos totais -> abrir ->
    INTERJORNADA, TOTAL DE HORAS, DESCONTOS, HORAS NOTURNAS e HORAS
    EXTRAS -> fechar.

    O período não precisa incluir hoje: o app mostra o do último
    espelho, que no começo do mês ainda é o anterior.
    """
    painel = PainelPontoPage(home_autenticada.driver)
    hoje = date.today()

    # Uma execução interrompida pode ter deixado o painel em outro dia.
    painel.ir_para(hoje)

    inicio, fim = periodo_dos_totais(painel.texto_dos_totais())
    problema = problema_no_periodo(inicio, fim, hoje)

    assert problema is None, problema

    if painel.totais_abertos():
        # Deixados abertos por uma execução interrompida: começa fechado.
        painel.fechar_totais()

    painel.abrir_totais()
    totais = painel.totais()

    faltando = [rotulo for rotulo, valor in totais.items() if valor is None]
    assert not faltando, f"Totais não exibidos: {faltando}."

    fora_do_formato = {
        rotulo: valor
        for rotulo, valor in totais.items()
        if not e_total_em_horas(valor)
    }
    assert not fora_do_formato, (
        f"Totais fora do formato de horas (HH:MM): {fora_do_formato}."
    )

    painel.fechar_totais()
