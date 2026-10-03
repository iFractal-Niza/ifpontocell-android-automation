"""
Leitura das telas de rótulo/valor (TabelaRotuloValorMixin, usado por
Dados Pessoais): agrupamento dos textos da tela em rótulo + valor e
rolagem até não aparecer texto novo. As células lidas da tela são
injetadas no lugar de _textos_das_celulas.
"""

from unittest.mock import Mock

from pages.compartilhado.tabela_rotulo_valor import agrupar_rotulo_valor
from pages.dados_pessoais.dados_pessoais_page import DadosPessoaisPage


def _pagina(monkeypatch, leituras, max_rolagens=4) -> DadosPessoaisPage:
    pagina = DadosPessoaisPage(Mock())
    pagina.MAX_ROLAGENS = max_rolagens
    telas = iter(leituras)
    ultima = []

    def proxima():
        nonlocal ultima
        ultima = next(telas, ultima)
        return ultima

    monkeypatch.setattr(pagina, "_textos_das_celulas", proxima)
    monkeypatch.setattr(pagina, "_rolar_para_baixo", lambda: None)
    monkeypatch.setattr(pagina, "_log_info", lambda *a, **k: None)
    return pagina


# === Agrupamento dos textos (Android: sem células) ===
def test_agrupa_rotulo_em_caixa_alta_com_o_valor_seguinte():
    textos = [
        "DADOS PESSOAIS",
        "EMPRESA",
        "Teste_homolog 9",
        "COLABORADOR",
        "TesterN95",
        "DEPTO.:",
        "2 - Depto_NR1",
        "MATRICULA",
        "14095",
    ]

    assert agrupar_rotulo_valor(textos) == [
        ["DADOS PESSOAIS"],
        ["EMPRESA", "Teste_homolog 9"],
        ["COLABORADOR", "TesterN95"],
        ["DEPTO.:", "2 - Depto_NR1"],
        ["MATRICULA", "14095"],
    ]


def test_rotulo_seguido_de_rotulo_fica_sozinho():
    assert agrupar_rotulo_valor(["TITULO", "EMPRESA", "iFractal"]) == [
        ["TITULO"],
        ["EMPRESA", "iFractal"],
    ]


# === Leitura com rolagem ===
def test_monta_campos_e_junta_o_que_aparece_ao_rolar(monkeypatch):
    primeira_tela = [["EMPRESA", "Teste_homolog 9"], ["COLABORADOR", "X"]]
    depois_de_rolar = [["COLABORADOR", "X"], ["MATRICULA", "14095"]]

    conteudo = _pagina(
        monkeypatch, [primeira_tela, depois_de_rolar]
    ).ler_conteudo()

    assert conteudo.campos == {
        "EMPRESA": "Teste_homolog 9",
        "COLABORADOR": "X",
        "MATRICULA": "14095",
    }
    # Célula repetida entre as rolagens não duplica.
    assert conteudo.textos.count("COLABORADOR") == 1


def test_dados_pessoais_le_os_campos(monkeypatch):
    pagina = _pagina(
        monkeypatch,
        [[["COLABORADOR", "Tester QA"], ["DEPARTAMENTO", "Depto_Tester_QA"]]],
        max_rolagens=0,
    )

    assert pagina.ler_conteudo().campos["DEPARTAMENTO"] == "Depto_Tester_QA"


def test_tela_sem_rolagem_le_uma_vez_e_nao_rola(monkeypatch):
    pagina = DadosPessoaisPage(Mock())
    rolagens = []
    leituras = []

    def ler():
        leituras.append(1)
        return [["COLABORADOR", "Tester QA"]]

    monkeypatch.setattr(pagina, "_textos_das_celulas", ler)
    monkeypatch.setattr(
        pagina, "_rolar_para_baixo", lambda: rolagens.append(1)
    )
    monkeypatch.setattr(pagina, "_log_info", lambda *a, **k: None)

    pagina.ler_conteudo()

    assert (len(leituras), len(rolagens)) == (1, 0)


def test_dados_pessoais_le_o_colaborador(monkeypatch):
    # Mesma leitura do iOS: o nome vem do par COLABORADOR.
    pagina = _pagina(
        monkeypatch,
        [
            [
                ["DADOS PESSOAIS"],
                ["EMPRESA", "iFractal"],
                ["COLABORADOR", "Tester QA"],
                ["DEPARTAMENTO", "Depto_Tester_QA"],
                ["MATRÍCULA", "72"],
            ]
        ],
        max_rolagens=0,
    )

    assert pagina.colaborador() == "Tester QA"
