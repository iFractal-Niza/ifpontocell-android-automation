"""
Períodos exibidos nas listas de documentos do app.

- Competência (mês de referência): "Setembro 2026" — Holerite.
- Exercício (ano): "IR-2026" — Informe de Rendimentos.

As funções convertem o texto em algo ordenável, para escolher o mais
recente sem depender da ordem da tela.
"""

import re
import unicodedata
from datetime import date

MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def _sem_acento(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def interpretar_competencia(texto: str) -> date:
    """
    Converte "Setembro 2026" em date(2026, 9, 1).

    Aceita caixa e acento variáveis ("MARÇO 2026", "marco 2026") e
    espaços extras. Levanta ValueError com o texto lido quando o formato
    não é reconhecido.
    """
    partes = _sem_acento(texto or "").lower().split()

    if len(partes) != 2 or partes[0] not in MESES or not partes[1].isdigit():
        raise ValueError(f"Competência fora do formato 'Mês AAAA': {texto!r}.")

    return date(int(partes[1]), MESES[partes[0]], 1)


_EXERCICIO = re.compile(r"^IR-(\d{4})$")


def interpretar_exercicio(texto: str) -> int:
    """
    Converte "IR-2026" em 2026.

    Aceita caixa e espaços extras nas pontas ("ir-2026 "). Levanta
    ValueError com o texto lido quando o formato não é reconhecido.
    """
    correspondencia = _EXERCICIO.match((texto or "").strip().upper())

    if not correspondencia:
        raise ValueError(f"Exercício fora do formato 'IR-AAAA': {texto!r}.")

    return int(correspondencia.group(1))


_INTERVALO = re.compile(r"(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})")


def extrair_intervalo(texto: str) -> str:
    """
    Extrai "DD/MM/AAAA a DD/MM/AAAA" de um texto do app, ex.:
    "assinatura.cellCompetencia_Período de 01/08/2026 a 31/08/2026" ou
    "Estou de acordo com o espelho referente ao período de: 01/08/2026
    a 31/08/2026" -> "01/08/2026 a 31/08/2026".

    Levanta ValueError com o texto lido quando não encontra o intervalo.
    """
    correspondencia = _INTERVALO.search(texto or "")

    if not correspondencia:
        raise ValueError(
            f"Intervalo 'DD/MM/AAAA a DD/MM/AAAA' não encontrado: {texto!r}."
        )

    return f"{correspondencia.group(1)} a {correspondencia.group(2)}"
