"""
Proteção dos testes que consomem massa de teste irreversivelmente
(ex.: assinar um espelho de ponto — só volta excluindo e refazendo o
fechamento).

Marcados com @pytest.mark.consome_massa, só executam com a opção
--consumir-massa (make run, make smoke — e, por ele, os merges —, make
ass-espelho, make ct e make falhas). Sem ela, são pulados com o motivo:
rodar por acidente num 'pytest tests' não gasta massa.
"""

import pytest

MARKER = "consome_massa"
OPCAO = "--consumir-massa"


def pytest_addoption(parser) -> None:
    parser.addoption(
        OPCAO,
        action="store_true",
        default=False,
        help=(
            "executa os testes marcados com consome_massa (alteram dados "
            "de forma irreversível no ambiente de teste)"
        ),
    )


def pular_sem_opcao(items, consumir_massa: bool) -> None:
    if consumir_massa:
        return

    pular = pytest.mark.skip(
        reason=(
            "consome massa de teste irreversivelmente; rode com "
            f"{OPCAO} (make run, make smoke ou make ass-espelho)"
        )
    )

    for item in items:
        if item.get_closest_marker(MARKER) is not None:
            item.add_marker(pular)


def pytest_collection_modifyitems(config, items) -> None:
    pular_sem_opcao(items, config.getoption(OPCAO))
