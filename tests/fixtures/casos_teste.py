"""
Execução por ID de caso de teste: --ct CT011 (ou --ct CT011,CT012).

Os IDs vêm do @pytest.mark.ct("CT011") de cada teste; o catálogo e a
checagem de IDs únicos ficam em qa_observability.casos_teste.
"""

import pytest

MARKER = "ct"
OPCAO = "--ct"


def pytest_addoption(parser) -> None:
    parser.addoption(
        OPCAO,
        default="",
        help=(
            "executa só os casos de teste informados, separados por "
            "vírgula (ex.: --ct CT011,CT012)"
        ),
    )


def id_do_item(item) -> str:
    """ID do CT do teste; "" se ele não tiver o marker."""
    marker = item.get_closest_marker(MARKER)

    if marker is None or not marker.args:
        return ""

    return str(marker.args[0])


def separar_por_ct(items, opcao: str) -> tuple[list, list]:
    """
    (selecionados, descartados) para os IDs pedidos. Sem a opção, todos
    ficam selecionados. ID que não existe em nenhum teste é erro: evita
    a execução vazia que parece aprovada.
    """
    pedidos = {parte.strip().upper() for parte in opcao.split(",")}
    pedidos.discard("")

    if not pedidos:
        return list(items), []

    selecionados = [item for item in items if id_do_item(item) in pedidos]
    descartados = [item for item in items if id_do_item(item) not in pedidos]

    ausentes = pedidos - {id_do_item(item) for item in selecionados}

    if ausentes:
        raise pytest.UsageError(
            f"{OPCAO}: nenhum teste com o ID {', '.join(sorted(ausentes))}."
        )

    return selecionados, descartados


def pytest_collection_modifyitems(config, items) -> None:
    selecionados, descartados = separar_por_ct(items, config.getoption(OPCAO))

    if descartados:
        config.hook.pytest_deselected(items=descartados)
        items[:] = selecionados
