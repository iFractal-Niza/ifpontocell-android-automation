import pytest

from utils.ass_espelho import (
    EspelhoAssinatura,
    mais_recente,
    pendentes_com_aviso,
    segundo_mais_recente,
)
from utils.periodo import extrair_intervalo

AGOSTO = EspelhoAssinatura("Agosto 2026", "01/08/2026 a 31/08/2026", False)
JULHO = EspelhoAssinatura("Julho 2026", "01/07/2026 a 31/07/2026", False)
DEZEMBRO = EspelhoAssinatura("Dezembro 2025", "01/12/2025 a 31/12/2025", True)


# === Intervalo do período ===
@pytest.mark.parametrize(
    "texto",
    [
        "assinatura.cellCompetencia_Período de 01/08/2026 a 31/08/2026",
        "TOTAIS DO ESPELHO Período de 01/08/2026 a 31/08/2026",
        "Estou de acordo com o espelho referente ao período de: "
        "01/08/2026 a 31/08/2026",
    ],
)
def test_extrai_intervalo_dos_textos_do_app(texto):
    assert extrair_intervalo(texto) == "01/08/2026 a 31/08/2026"


@pytest.mark.parametrize("texto", ["", None, "Agosto 2026", "01/08/2026"])
def test_texto_sem_intervalo_falha_mostrando_o_texto(texto):
    with pytest.raises(ValueError, match="DD/MM/AAAA a DD/MM/AAAA"):
        extrair_intervalo(texto)


# === Escolha do espelho ===
def test_mais_recente_pela_data_e_nao_pela_posicao():
    assert mais_recente([JULHO, DEZEMBRO, AGOSTO]) == AGOSTO


def test_mais_recente_considera_assinados():
    # Visualizar não depende de estar assinado.
    assinado = EspelhoAssinatura(
        "Setembro 2026", "01/09/2026 a 30/09/2026", True
    )

    assert mais_recente([AGOSTO, assinado]) == assinado


def test_mais_recente_sem_espelhos_falha():
    with pytest.raises(ValueError, match="Nenhum espelho"):
        mais_recente([])


def test_segundo_mais_recente_pela_data():
    assert segundo_mais_recente([JULHO, DEZEMBRO, AGOSTO]) == JULHO


def test_segundo_mais_recente_exige_dois():
    with pytest.raises(ValueError, match="pelo menos dois"):
        segundo_mais_recente([AGOSTO])


# === Aviso de assinatura (dois últimos meses) ===
JUNHO = EspelhoAssinatura("Junho 2026", "01/06/2026 a 30/06/2026", False)


def _assinado(espelho: EspelhoAssinatura) -> EspelhoAssinatura:
    return EspelhoAssinatura(espelho.competencia, espelho.periodo, True)


def test_pendente_antigo_nao_gera_aviso():
    # Caso real: Agosto e Julho assinados, Junho pendente -> sem aviso.
    espelhos = [_assinado(AGOSTO), _assinado(JULHO), JUNHO]

    assert pendentes_com_aviso(espelhos) == []


def test_pendentes_entre_os_dois_mais_recentes_geram_aviso():
    espelhos = [JUNHO, _assinado(AGOSTO), JULHO]

    assert pendentes_com_aviso(espelhos) == [JULHO]


def test_aviso_sem_espelhos():
    assert pendentes_com_aviso([]) == []
