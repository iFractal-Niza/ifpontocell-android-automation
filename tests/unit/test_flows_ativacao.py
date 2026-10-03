"""
sem_foto no primeiro acesso (flows._marcar_sem_foto_antes_unlock), com
um client da API falso. No Android o celular sobe ativo (emulador e
celular): nada é ativado pela API.
"""

from unittest.mock import Mock

import pytest

from tests.support import flows
from tests.support.flows import _marcar_sem_foto_antes_unlock


@pytest.fixture
def api():
    client = Mock()
    client.obter_codigo_celular_por_nome_pessoa.return_value = 42
    return client


def test_marca_sem_foto_no_celular_mais_recente(api):
    codigo = _marcar_sem_foto_antes_unlock(
        celular_api=api,
        monitor_nome_pessoa=" TesterN95 ",
    )

    assert codigo == 42
    api.obter_codigo_celular_por_nome_pessoa.assert_called_once_with(
        "TesterN95"
    )
    # Marcado antes do PIN: o registro de ponto não precisa relançar.
    api.definir_sem_foto.assert_called_once_with(42, sem_foto=True)


def test_nao_ativa_nem_espera_celular_novo(api):
    # O celular sobe ativo: esperar um código novo para ativar
    # travaria 60s.
    _marcar_sem_foto_antes_unlock(api, "TesterN95")

    api.aguardar_e_ativar_celular_mais_recente.assert_not_called()
    api.ativar_celular.assert_not_called()


def test_sem_client_falha_com_orientacao():
    with pytest.raises(AssertionError, match="celular_api"):
        _marcar_sem_foto_antes_unlock(None, "TesterN95")


def test_sem_pessoa_falha_com_orientacao(api):
    with pytest.raises(AssertionError, match="MONITOR_NOME_PESSOA"):
        _marcar_sem_foto_antes_unlock(api, "  ")

    api.definir_sem_foto.assert_not_called()


def test_primeiro_acesso_nao_busca_os_celulares_de_antes(monkeypatch, api):
    chamadas = {}
    monkeypatch.setattr(flows, "realizar_login", lambda **_: None)
    monkeypatch.setattr(
        flows, "realizar_unlock", lambda **kw: chamadas.update(kw) or "home"
    )

    flows.realizar_primeiro_acesso(
        driver=Mock(),
        nome_sistema="s",
        usuario="u",
        senha="p",
        pin="1111",
        celular_api=api,
        monitor_nome_pessoa="TesterN95",
    )

    assert chamadas["monitor_nome_pessoa"] == "TesterN95"
    assert "codigos_anteriores" not in chamadas
    api.obter_codigos_celular_por_nome_pessoa.assert_not_called()
