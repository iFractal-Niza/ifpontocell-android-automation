"""
Marcações da tela STATUS e o comprovante de registro de ponto.
"""

import re
from dataclasses import dataclass
from datetime import date

# Id de cada marcação: "status.cellMarcacao_2026-10-01_1" (dia e código).
_ID_MARCACAO = re.compile(
    r"^status\.cellMarcacao_(\d{4})-(\d{2})-(\d{2})_(\d+)$"
)


@dataclass(frozen=True)
class MarcacaoStatus:
    id: str
    dia: date
    codigo: int


def ler_id_marcacao(id_celula: str) -> MarcacaoStatus | None:
    """ "status.cellMarcacao_2026-10-01_1" -> dia 01/10/2026, código 1."""
    correspondencia = _ID_MARCACAO.match((id_celula or "").strip())

    if not correspondencia:
        return None

    ano, mes, dia, codigo = correspondencia.groups()

    return MarcacaoStatus(
        id=id_celula.strip(),
        dia=date(int(ano), int(mes), int(dia)),
        codigo=int(codigo),
    )


def mais_recente(marcacoes: list[MarcacaoStatus]) -> MarcacaoStatus | None:
    """A do dia mais recente e, no dia, a de maior código."""
    if not marcacoes:
        return None

    return max(marcacoes, key=lambda m: (m.dia, m.codigo))


def campos_do_comprovante(texto: str) -> dict[str, str]:
    """
    Texto do comprovante -> {"HORA": "16:50", "DIA": "01/10/2026", ...}.

    Uma linha por campo, "CHAVE: valor"; a chave vai em caixa alta. O
    título e o rodapé (sem ": ") não entram.
    """
    campos = {}

    for linha in (texto or "").splitlines():
        chave, separador, valor = linha.partition(": ")

        if separador and chave.strip():
            campos[chave.strip().upper()] = valor.strip()

    return campos
