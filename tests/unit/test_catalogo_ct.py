"""
Garantia de que todo teste de tela/API desta automação tem um CT único,
e a ordem da suíte da configuração (observability.automacao). O catálogo
em si é do pacote ifponto-observability (qa_observability.casos_teste,
testado lá).
"""

from qa_observability.casos_teste import (
    casos_na_ordem_da_suite,
    ler_casos,
    validar_casos,
)


def test_todo_teste_do_projeto_tem_ct_unico():
    erros = validar_casos(ler_casos())

    assert not erros, "\n".join(erros)


def test_ordem_da_suite_le_o_projeto_real():
    casos = casos_na_ordem_da_suite()

    assert casos[0].nodeid.startswith("tests/app/test_onboarding.py::")
    assert casos[-1].nodeid.startswith("tests/api/")
