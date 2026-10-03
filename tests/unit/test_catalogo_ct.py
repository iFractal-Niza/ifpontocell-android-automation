"""
Catálogo dos casos de teste (observability.casos_teste) e a garantia
de que todo teste de tela/API do projeto tem um CT único.
"""

from observability.casos_teste import (
    CasoTeste,
    aplicar_renumeracao,
    casos_na_ordem_da_suite,
    ler_casos,
    mapa_de_renumeracao,
    proximo_id,
    validar_casos,
)

TESTE = '''
import pytest


@pytest.mark.ct("CT001")
@pytest.mark.smoke
@pytest.mark.consome_massa
def test_visualizar_holerite_mais_recente():
    """
    Valida a abertura do holerite
    mais recente.

    Fronteira: Home -> Holerite.
    """


@pytest.mark.regression
def test_sem_ct():
    pass


def _auxiliar():
    pass
'''


def _projeto(tmp_path, conteudo: str = TESTE):
    pasta = tmp_path / "tests" / "app"
    pasta.mkdir(parents=True)
    (tmp_path / "tests" / "api").mkdir()
    (pasta / "test_holerite.py").write_text(conteudo, encoding="utf-8")

    return tmp_path


def _caso(identificador: str, nome: str = "t") -> CasoTeste:
    return CasoTeste(
        id=identificador,
        nodeid=f"tests/app/test_login.py::{nome}",
    )


# === Garantia sobre o projeto real ===
def test_todo_teste_do_projeto_tem_ct_unico():
    erros = validar_casos(ler_casos())

    assert not erros, "\n".join(erros)


# === Leitura ===
def test_le_o_id_e_o_nodeid_do_caso(tmp_path):
    caso = ler_casos(_projeto(tmp_path))[0]

    assert caso == CasoTeste(
        id="CT001",
        nodeid="tests/app/test_holerite.py::test_visualizar_holerite_mais_recente",
    )


def test_funcao_auxiliar_nao_e_caso_de_teste(tmp_path):
    nomes = [caso.nodeid for caso in ler_casos(_projeto(tmp_path))]

    assert not any("_auxiliar" in nome for nome in nomes)


def test_teste_sem_ct_vai_para_o_fim_com_id_vazio(tmp_path):
    casos = ler_casos(_projeto(tmp_path))

    assert [caso.id for caso in casos] == ["CT001", ""]


# === Validação ===
def test_teste_sem_ct_e_erro_e_sugere_o_proximo_id(tmp_path):
    erros = validar_casos(ler_casos(_projeto(tmp_path)))

    assert len(erros) == 1
    assert "test_sem_ct" in erros[0]
    assert "CT002" in erros[0]


def test_id_repetido_e_erro():
    erros = validar_casos([_caso("CT001", "a"), _caso("CT001", "b")])

    assert len(erros) == 1
    assert "CT001 repetido" in erros[0]
    assert "::a" in erros[0] and "::b" in erros[0]


def test_id_fora_do_formato_e_erro():
    erros = validar_casos([_caso("CT-1")])

    assert len(erros) == 1
    assert "fora do formato" in erros[0]


def test_catalogo_correto_nao_tem_erros():
    assert validar_casos([_caso("CT001"), _caso("CT002")]) == []


def test_proximo_id_segue_o_maior_usado():
    assert proximo_id([_caso("CT001"), _caso("CT018"), _caso("")]) == "CT019"
    assert proximo_id([]) == "CT001"


# === Renumeração na ordem da suíte ===
def test_mapa_numera_na_ordem_recebida():
    casos = [_caso("CT019", "a"), _caso("CT011", "b"), _caso("CT012", "c")]

    assert mapa_de_renumeracao(casos) == {
        "CT019": "CT001",
        "CT011": "CT002",
        "CT012": "CT003",
    }


def test_mapa_ignora_teste_sem_ct():
    assert mapa_de_renumeracao([_caso(""), _caso("CT005")]) == {
        "CT005": "CT001"
    }


def test_troca_de_ids_nao_se_atropela(tmp_path):
    arquivo = tmp_path / "test_x.py"
    arquivo.write_text(
        '@pytest.mark.ct("CT023")\n# continua do CT024\n'
        '@pytest.mark.ct("CT024")\n',
        encoding="utf-8",
    )

    alterados = aplicar_renumeracao(
        {"CT023": "CT024", "CT024": "CT023"}, [arquivo]
    )

    assert alterados == [arquivo]
    assert arquivo.read_text(encoding="utf-8") == (
        '@pytest.mark.ct("CT024")\n# continua do CT023\n'
        '@pytest.mark.ct("CT023")\n'
    )


def test_arquivo_sem_mudanca_nao_e_reescrito(tmp_path):
    arquivo = tmp_path / "test_x.py"
    arquivo.write_text('@pytest.mark.ct("CT001")\n', encoding="utf-8")

    assert aplicar_renumeracao({"CT009": "CT010"}, [arquivo]) == []


def test_ordem_da_suite_le_o_projeto_real():
    casos = casos_na_ordem_da_suite()

    assert casos[0].nodeid.startswith("tests/app/test_onboarding.py::")
    assert casos[-1].nodeid.startswith("tests/api/")
