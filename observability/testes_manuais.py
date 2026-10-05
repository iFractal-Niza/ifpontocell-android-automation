"""
Testes que continuam manuais (observability/testes_manuais.yaml).

No `make evidencias` (opção --testes-manuais), o report já abre com eles
no bloco "Testes manuais", com o CT, a descrição e o fluxo, para o
tester preencher Status e o resto. Entram sem Status: só contam nos
totais e em "Qualidade por fluxo" (por isso o fluxo é obrigatório)
depois de preenchidos. Nos outros comandos, não entram.
"""

import re
from pathlib import Path

import yaml

ARQUIVO = Path(__file__).resolve().parent / "testes_manuais.yaml"

OPCAO = "--testes-manuais"

FORMATO_CT = re.compile(r"^CT\d{3}$")


class ListaInvalida(ValueError):
    """O testes_manuais.yaml tem um item fora do formato."""


def carregar(arquivo: Path = ARQUIVO) -> list[dict[str, str]]:
    """
    Os testes manuais do arquivo: [{"ct", "descricao", "fluxo"}]. Sem
    arquivo ou com a lista vazia, nenhum.
    """
    if not arquivo.exists():
        return []

    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or []

    if not isinstance(dados, list):
        raise ListaInvalida(f"{arquivo.name}: esperava uma lista de testes.")

    testes = []
    vistos = set()

    for posicao, item in enumerate(dados, start=1):
        if not isinstance(item, dict):
            raise ListaInvalida(
                f"{arquivo.name}, item {posicao}: não é um teste."
            )

        ct = str(item.get("ct") or "").strip()
        descricao = str(item.get("descricao") or "").strip()
        fluxo = str(item.get("fluxo") or "").strip()

        if not FORMATO_CT.match(ct):
            raise ListaInvalida(
                f"{arquivo.name}, item {posicao}: CT '{ct}' fora do formato "
                "CT000."
            )

        if not descricao:
            raise ListaInvalida(f"{arquivo.name}, {ct}: falta a descricao.")

        if not fluxo:
            raise ListaInvalida(
                f"{arquivo.name}, {ct}: falta o fluxo (Qualidade por fluxo)."
            )

        if ct in vistos:
            raise ListaInvalida(f"{arquivo.name}: {ct} repetido.")

        vistos.add(ct)
        testes.append(
            {
                "ct": ct,
                "descricao": descricao,
                "fluxo": fluxo,
            }
        )

    return testes


def pytest_addoption(parser) -> None:
    parser.addoption(
        OPCAO,
        action="store_true",
        default=False,
        help=(
            "inclui no report os testes manuais de "
            "observability/testes_manuais.yaml (make evidencias)"
        ),
    )
