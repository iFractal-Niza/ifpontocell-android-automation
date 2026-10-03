"""
Cliente do Monitor Celular (api.monitor_celular_client): extractors,
normalização da listagem, consultas por pessoa e ativação idempotente.
Nenhuma requisição HTTP é feita.
"""

import pytest

from api.monitor_celular_client import MonitorCelularClient


@pytest.fixture
def client():
    return MonitorCelularClient(
        base_url="https://api.exemplo",
        user="usuario",
        token_original="token",
    )


# === Extractors ===
@pytest.mark.parametrize(
    "registro, esperado",
    [
        ({"codigo": "123"}, 123),
        ({"cod": 7}, 7),
        ({"id": "9"}, 9),
        ({"codigo": "abc"}, None),
        ({}, None),
    ],
)
def test_extrair_codigo(registro, esperado):
    assert MonitorCelularClient._extrair_codigo_registro(registro) == esperado


def test_ativo_false_nao_cai_na_proxima_chave():
    # Um 'or' em cadeia descartaria o False legítimo de 'ativo'.
    registro = {"ativo": False, "active": True}

    assert MonitorCelularClient._extrair_ativo_registro(registro) is False


@pytest.mark.parametrize(
    "valor, esperado",
    [
        (True, True),
        (1, True),
        ("S", True),
        ("sim", True),
        ("ativo", True),
        (False, False),
        (0, False),
        ("N", False),
        ("não", False),
        ("", False),
        ("talvez", None),
    ],
)
def test_ativo_interpreta_formatos_do_backend(valor, esperado):
    registro = {"ativo": valor}

    assert MonitorCelularClient._extrair_ativo_registro(registro) is esperado


def test_ativo_ausente_e_desconhecido():
    assert MonitorCelularClient._extrair_ativo_registro({}) is None


# === Normalização da listagem ===
def test_normaliza_lista_descartando_nao_dicts(client):
    assert client._normalizar_registros([{"codigo": 1}, "lixo"]) == [
        {"codigo": 1}
    ]


def test_normaliza_chave_de_listagem(client):
    resposta = {"rows": [{"codigo": 1}, {"codigo": 2}]}

    assert client._normalizar_registros(resposta) == resposta["rows"]


def test_normaliza_listagem_aninhada(client):
    resposta = {"data": {"items": [{"codigo": 1}]}}

    assert client._normalizar_registros(resposta) == [{"codigo": 1}]


def test_normaliza_registro_unico(client):
    assert client._normalizar_registros({"codigo": 5}) == [{"codigo": 5}]


def test_normaliza_resposta_vazia(client):
    assert client._normalizar_registros(None) == []


def test_normaliza_resposta_de_falha_levanta(client):
    resposta = {"success": False, "info": "sem permissão"}

    with pytest.raises(ValueError, match="sem permissão"):
        client._normalizar_registros(resposta)


def test_normaliza_dict_sem_registros_levanta(client):
    with pytest.raises(ValueError, match="não contém registros"):
        client._normalizar_registros({"outra": "coisa"})


# === Consultas por pessoa ===
REGISTROS = [
    {"codigo": 30, "nmpessoa": "TesterN95", "ativo": "N"},
    {"codigo": 20, "nmpessoa": "Outra Pessoa", "ativo": "S"},
    {"codigo": 10, "nmpessoa": "testern95", "ativo": "S"},
]


@pytest.fixture
def client_com_listagem(client, monkeypatch):
    monkeypatch.setattr(
        client,
        "listar_celulares",
        lambda page=1, limit=25: {"rows": REGISTROS},
    )
    return client


def test_filtra_por_nome_sem_diferenciar_maiusculas(client_com_listagem):
    registros = client_com_listagem.listar_registros_celular_por_nome_pessoa(
        "  TESTERN95 "
    )

    assert [r["codigo"] for r in registros] == [30, 10]


def test_mais_recente_e_o_primeiro_da_listagem(client_com_listagem):
    registro = client_com_listagem.obter_registro_celular_por_nome_pessoa(
        "TesterN95"
    )

    assert registro["codigo"] == 30


def test_mais_recente_ignora_codigos_anteriores(client_com_listagem):
    registro = client_com_listagem.obter_registro_celular_por_nome_pessoa(
        "TesterN95",
        codigos_ignorados={30},
    )

    assert registro["codigo"] == 10


def test_busca_percorre_todas_as_paginas(client, monkeypatch):
    # Caso real: no device real, o registro do iPhone é antigo (o login
    # reaproveita, não cria) e ficava fora da primeira página.
    limite = client.LIMITE_POR_PAGINA_NA_BUSCA
    outros = [
        {"codigo": 1000 + n, "nmpessoa": "Outra Pessoa"} for n in range(limite)
    ]
    paginas = {1: outros, 2: [{"codigo": 7, "nmpessoa": "TesterN95"}]}
    pedidas = []

    def listar(page=1, limit=25):
        pedidas.append(page)
        return {"rows": paginas.get(page, [])}

    monkeypatch.setattr(client, "listar_celulares", listar)

    registro = client.obter_registro_celular_por_nome_pessoa("TesterN95")

    assert registro["codigo"] == 7
    assert pedidas == [1, 2]


def test_pessoa_sem_registro_levanta(client_com_listagem):
    with pytest.raises(ValueError, match="Nenhum registro"):
        client_com_listagem.obter_registro_celular_por_nome_pessoa("Ninguém")


# === Ativação idempotente ===
def test_ativa_quando_celular_esta_inativo(client_com_listagem, monkeypatch):
    ativados = []
    monkeypatch.setattr(client_com_listagem, "ativar_celular", ativados.append)

    codigo = client_com_listagem.aguardar_e_ativar_celular_mais_recente(
        "TesterN95",
        poll_interval=0.01,
    )

    assert codigo == 30
    assert ativados == [30]


def test_nao_reativa_celular_ja_ativo(client_com_listagem, monkeypatch):
    ativados = []
    monkeypatch.setattr(client_com_listagem, "ativar_celular", ativados.append)

    codigo = client_com_listagem.aguardar_e_ativar_celular_mais_recente(
        "TesterN95",
        codigos_anteriores={30},
        poll_interval=0.01,
    )

    assert codigo == 10
    assert ativados == []


def test_aguarda_celular_novo_aparecer(client, monkeypatch):
    # Primeira consulta: só o celular antigo; segunda: o novo apareceu.
    respostas = iter(
        [
            {"rows": [{"codigo": 1, "nmpessoa": "P", "ativo": "S"}]},
            {
                "rows": [
                    {"codigo": 2, "nmpessoa": "P", "ativo": "N"},
                    {"codigo": 1, "nmpessoa": "P", "ativo": "S"},
                ]
            },
        ]
    )
    monkeypatch.setattr(
        client, "listar_celulares", lambda page=1, limit=25: next(respostas)
    )
    ativados = []
    monkeypatch.setattr(client, "ativar_celular", ativados.append)

    codigo = client.aguardar_e_ativar_celular_mais_recente(
        "P",
        codigos_anteriores={1},
        poll_interval=0.01,
    )

    assert codigo == 2
    assert ativados == [2]


def test_timeout_quando_celular_novo_nao_aparece(client_com_listagem):
    with pytest.raises(TimeoutError, match="Nenhum registro"):
        client_com_listagem.aguardar_e_ativar_celular_mais_recente(
            "TesterN95",
            codigos_anteriores={10, 30},
            timeout=0.05,
            poll_interval=0.01,
        )
