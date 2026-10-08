"""
Testes que continuam manuais: o observability/testes_manuais.yaml desta
automação é válido e não repete CT dos automatizados. A leitura, a opção
--testes-manuais e o dashboard são do pacote ifponto-observability
(testados lá).
"""

from qa_observability import testes_manuais
from qa_observability.casos_teste import ler_casos

from observability.automacao import RAIZ


def test_arquivo_do_projeto_e_valido_e_sem_ct_dos_automatizados():
    arquivo = testes_manuais.arquivo_da_automacao(RAIZ)
    manuais = {teste["ct"] for teste in testes_manuais.carregar(arquivo)}
    automatizados = {caso.id for caso in ler_casos() if caso.id}

    assert manuais & automatizados == set()
