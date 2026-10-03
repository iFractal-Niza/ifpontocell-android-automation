"""
Textos do painel da tela Ponto (aba PONTO da Home): a data do dia, as
marcações e o período dos totais do espelho.
"""

import re
from datetime import date, timedelta

from utils.periodo import MESES, _sem_acento

DIAS_DA_SEMANA = (
    "Segunda",
    "Terça",
    "Quarta",
    "Quinta",
    "Sexta",
    "Sábado",
    "Domingo",
)

MESES_EXIBIDOS = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def data_do_painel(dia: date) -> str:
    """Ex.: date(2026, 10, 1) -> "Quinta, 01 de Outubro de 2026"."""
    return (
        f"{DIAS_DA_SEMANA[dia.weekday()]}, {dia.day:02d} de "
        f"{MESES_EXIBIDOS[dia.month - 1]} de {dia.year}"
    )


_DATA_DO_PAINEL = re.compile(
    r"^[^,]+,\s*(\d{1,2})\s+de\s+(\S+)\s+de\s+(\d{4})$"
)


def dia_do_painel(texto: str) -> date:
    """
    "Sexta, 02 de Outubro de 2026" -> date(2026, 10, 2).

    Levanta ValueError com o texto lido quando o formato não é
    reconhecido.
    """
    correspondencia = _DATA_DO_PAINEL.match(" ".join((texto or "").split()))
    mes = (
        _sem_acento(correspondencia.group(2)).lower()
        if correspondencia
        else ""
    )

    if not correspondencia or mes not in MESES:
        raise ValueError(f"Data do painel não reconhecida: {texto!r}.")

    return date(
        int(correspondencia.group(3)),
        MESES[mes],
        int(correspondencia.group(1)),
    )


def mesma_chave(texto: str) -> str:
    """
    Forma comparável de um texto da tela, sem acento, caixa e espaços
    repetidos: "JORNADA   DIÁRIA" e "Jornada Diaria" -> "jornada diaria".
    """
    return " ".join(_sem_acento(texto or "").lower().split())


def mesma_data(exibida: str, esperada: str) -> bool:
    """
    Compara sem depender de acento e caixa ("Sábado"/"Sabado",
    "Março"/"MARÇO"): o que importa é o dia, não a tipografia.
    """
    return mesma_chave(exibida) == mesma_chave(esperada)


# "10:47 horas", ou com a letra do tipo da marcação depois do horário:
# "10:47e horas". A letra não entra no horário.
_MARCACAO = re.compile(r"^(\d{2}:\d{2})([^\s\d]*)\s+horas$")

# Tipo da marcação, pela letra depois do horário (ainda não validado
# pelos testes; a alteração de marcação é um cenário futuro).
MARCACAO_ELETRONICA = "e"
MARCACAO_ALTERADA = "i"


def tipo_da_marcacao(texto: str) -> str | None:
    """
    "10:47e horas" -> "e" (eletrônica); "10:47i horas" -> "i" (alterada);
    "10:47 horas" -> "" (sem letra); None se não for uma marcação.
    """
    correspondencia = _MARCACAO.match((texto or "").strip())

    return correspondencia.group(2).lower() if correspondencia else None


def horario_da_marcacao(texto: str) -> str | None:
    """ "10:47e horas" -> "10:47"; None se não for uma marcação."""
    correspondencia = _MARCACAO.match((texto or "").strip())

    return correspondencia.group(1) if correspondencia else None


# "01setembro2026" (como a árvore mostra) ou "01/09/2026" (como a tela).
_DATA_POR_EXTENSO = re.compile(r"(\d{1,2})\s*([^\W\d_]+)\s*(\d{4})")
_DATA_NUMERICA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


def _datas_do_texto(texto: str) -> list[date]:
    numericas = _DATA_NUMERICA.findall(texto)

    if numericas:
        return [date(int(a), int(m), int(d)) for d, m, a in numericas]

    datas = []

    for dia, mes, ano in _DATA_POR_EXTENSO.findall(texto):
        nome = _sem_acento(mes).lower()

        if nome in MESES:
            datas.append(date(int(ano), MESES[nome], int(dia)))

    return datas


def periodo_dos_totais(texto: str) -> tuple[date, date]:
    """
    "TOTAIS DO ESPELHO \\n Período de 01setembro2026 a 30setembro2026"
    -> (date(2026, 9, 1), date(2026, 9, 30)).

    Levanta ValueError com o texto lido quando não encontra as duas datas.
    """
    datas = _datas_do_texto(texto or "")

    if len(datas) != 2:
        raise ValueError(
            f"Período dos totais do espelho não reconhecido: {texto!r}."
        )

    return datas[0], datas[1]


# Duração de um período de espelho: um mês, que vai de 28 a 31 dias
# (01/09 a 30/09 são 29 dias de diferença; 22/09 a 21/10, também).
DIAS_DO_PERIODO = range(26, 31)


def problema_no_periodo(inicio: date, fim: date, hoje: date) -> str | None:
    """
    Por que o período dos totais não é coerente, ou None se for.

    Não exige que o período inclua hoje: o app mostra o espelho do
    último período, que no começo do mês ainda pode ser o anterior
    (01/09 a 30/09 visto em 01/10). Exige um mês de duração, que não
    comece no futuro e que não esteja desatualizado (fim há mais de um
    mês).
    """
    periodo = f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}"

    if (fim - inicio).days not in DIAS_DO_PERIODO:
        return f"O período {periodo} não tem a duração de um mês."

    if inicio > hoje:
        return f"O período {periodo} começa depois de hoje ({hoje:%d/%m/%Y})."

    if fim < hoje - timedelta(days=31):
        return (
            f"O período {periodo} está desatualizado: terminou há mais de "
            f"um mês (hoje: {hoje:%d/%m/%Y})."
        )

    return None


def ler_jornada(texto: str) -> list[str]:
    """
    APP_JORNADA do env.<device>.yaml -> horários na ordem.

    "08:00 12:00 13:00 18:00" (ou separados por vírgula) ->
    ["08:00", "12:00", "13:00", "18:00"]; vazio -> []. Levanta
    ValueError dizendo o que está fora do formato HH:MM.
    """
    horarios = (texto or "").replace(",", " ").split()
    invalidos = [h for h in horarios if not re.fullmatch(r"\d{2}:\d{2}", h)]

    if invalidos:
        raise ValueError(
            f"APP_JORNADA com horário fora do formato HH:MM: {invalidos}."
        )

    return horarios


_HORAS = re.compile(r"^\d+:\d{2}$")


def e_total_em_horas(texto: str) -> bool:
    """ "01:10", "174:30" -> True."""
    return bool(_HORAS.match((texto or "").strip()))
