"""
Espelhos da tela Assinatura do Espelho (ass_espelho; o menu Espelho de
Ponto é outra tela): escolha de qual visualizar e qual assinar, sem
depender da ordem da tela.
"""

from dataclasses import dataclass

from utils.periodo import interpretar_competencia


@dataclass(frozen=True)
class EspelhoAssinatura:
    competencia: str  # "Agosto 2026"
    periodo: str  # "01/08/2026 a 31/08/2026"
    assinado: bool


def mais_recente(espelhos: list[EspelhoAssinatura]) -> EspelhoAssinatura:
    if not espelhos:
        raise ValueError("Nenhum espelho informado.")

    return max(espelhos, key=lambda e: interpretar_competencia(e.competencia))


def segundo_mais_recente(
    espelhos: list[EspelhoAssinatura],
) -> EspelhoAssinatura:
    if len(espelhos) < 2:
        raise ValueError(
            f"São necessários pelo menos dois espelhos; há {len(espelhos)}."
        )

    return sorted(
        espelhos,
        key=lambda e: interpretar_competencia(e.competencia),
        reverse=True,
    )[1]


# O aviso de assinatura ao abrir o app só considera os espelhos dos dois
# últimos meses (confirmado no device em 01/10/2026): um pendente mais
# antigo (ex.: Junho, com Agosto e Julho assinados) não gera aviso.
ESPELHOS_COM_AVISO = 2


def pendentes_com_aviso(
    espelhos: list[EspelhoAssinatura],
) -> list[EspelhoAssinatura]:
    """
    Os espelhos pendentes que geram o aviso de assinatura: os não
    assinados entre os ESPELHOS_COM_AVISO mais recentes (pela data, não
    pela posição na tela).
    """
    recentes = sorted(
        espelhos,
        key=lambda e: interpretar_competencia(e.competencia),
        reverse=True,
    )[:ESPELHOS_COM_AVISO]

    return [espelho for espelho in recentes if not espelho.assinado]
