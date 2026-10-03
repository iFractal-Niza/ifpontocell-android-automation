"""
Base dos clientes da API (api.ifponto_api_client): configuração,
payload e erro de negócio. Exercitada por uma subclasse concreta, já que
a base não instancia sem PAG. Nenhuma requisição HTTP é feita.
"""

import pytest

from api.ifponto_api_client import IfPontoApiClient
from api.monitor_celular_client import MonitorCelularClient


@pytest.fixture
def client():
    return MonitorCelularClient(
        base_url="https://api.exemplo",
        user="usuario",
        token_original="token",
    )


# === Configuração ===
@pytest.mark.parametrize(
    "campo, mensagem",
    [
        ("base_url", "API_BASE_URL"),
        ("user", "API_USER"),
        ("token_original", "API_TOKEN"),
    ],
)
def test_configuracao_obrigatoria(campo, mensagem):
    argumentos = {
        "base_url": "https://api.exemplo",
        "user": "usuario",
        "token_original": "token",
    }
    argumentos[campo] = "   "

    with pytest.raises(ValueError, match=mensagem):
        MonitorCelularClient(**argumentos)


def test_base_sem_pag_nao_instancia():
    with pytest.raises(ValueError, match="não definiu PAG"):
        IfPontoApiClient("https://api.exemplo", "usuario", "token")


# === Payload ===
def test_multipart_normaliza_booleanos_para_minusculo():
    payload = MonitorCelularClient._build_multipart_payload(
        {"value": True, "outro": False, "codigo": 42}
    )

    assert payload == {
        "value": (None, "true"),
        "outro": (None, "false"),
        "codigo": (None, "42"),
    }


def test_atualizar_campo_rejeita_codigo_invalido(client):
    with pytest.raises(ValueError, match="Código do registro inválido"):
        client.atualizar_campo(codigo="abc", campo="ativo", value=True)


def test_atualizar_campo_rejeita_campo_vazio(client):
    with pytest.raises(ValueError, match="campo não pode ser vazio"):
        client.atualizar_campo(codigo=1, campo="  ", value=True)


# === Erro de negócio ===
@pytest.mark.parametrize("sucesso", [False, 0, "0", "false", "False"])
def test_resposta_de_falha_levanta_com_mensagem(client, sucesso):
    with pytest.raises(ValueError, match="Celular não encontrado"):
        client._validar_resposta_negocio(
            {"success": sucesso, "info": "Celular não encontrado"},
            operacao="teste",
        )


@pytest.mark.parametrize("resposta", [{"success": True}, {}, [], "texto"])
def test_resposta_sem_falha_passa(client, resposta):
    client._validar_resposta_negocio(resposta, operacao="teste")
