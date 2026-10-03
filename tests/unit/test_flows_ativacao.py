"""
Ativação do celular no primeiro acesso (flows._ativar_celular_antes_unlock),
com um client da API falso.
"""

from unittest.mock import Mock

import pytest

from tests.support import flows
from tests.support.flows import _ativar_celular_antes_unlock


@pytest.fixture(autouse=True)
def emulador(monkeypatch):
    """
    Emulador por padrão, sem depender do ANDROID_TARGET do
    env.<device>.yaml (com DEVICE=real, ele estaria em "real").
    """
    monkeypatch.setattr(flows, "is_emulator", lambda: True)


@pytest.fixture
def device_real(monkeypatch):
    monkeypatch.setattr(flows, "is_emulator", lambda: False)


@pytest.fixture
def api():
    client = Mock()
    client.aguardar_e_ativar_celular_mais_recente.return_value = 42
    return client


def test_ativa_e_marca_sem_foto_no_mesmo_celular(api):
    codigo = _ativar_celular_antes_unlock(
        celular_api=api,
        monitor_nome_pessoa=" TesterN95 ",
        codigos_anteriores={1, 2},
    )

    assert codigo == 42
    api.aguardar_e_ativar_celular_mais_recente.assert_called_once()
    assert (
        api.aguardar_e_ativar_celular_mais_recente.call_args.kwargs[
            "nome_pessoa"
        ]
        == "TesterN95"
    )
    # Marcado antes do PIN: o registro de ponto não precisa relançar.
    api.definir_sem_foto.assert_called_once_with(42, sem_foto=True)


def test_sem_client_falha_com_orientacao():
    with pytest.raises(AssertionError, match="celular_api"):
        _ativar_celular_antes_unlock(None, "TesterN95", None)


def test_sem_pessoa_falha_com_orientacao(api):
    with pytest.raises(AssertionError, match="MONITOR_NOME_PESSOA"):
        _ativar_celular_antes_unlock(api, "  ", None)

    api.definir_sem_foto.assert_not_called()


# === Primeiro acesso: celular novo x reaproveitado ===
def _primeiro_acesso(monkeypatch, api, **kwargs) -> dict:
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
        **kwargs,
    )

    return chamadas


def test_primeiro_acesso_ignora_os_celulares_que_ja_existiam(monkeypatch, api):
    api.obter_codigos_celular_por_nome_pessoa.return_value = {1, 2}

    chamadas = _primeiro_acesso(monkeypatch, api)

    assert chamadas["codigos_anteriores"] == {1, 2}


def test_depois_de_zerar_dados_reaproveita_o_celular(monkeypatch, api):
    # Caso real: depois de Zerar Dados o aparelho é o mesmo e o login
    # reaproveita o registro; ignorar os existentes travava a ativação.
    chamadas = _primeiro_acesso(monkeypatch, api, reaproveita_celular=True)

    assert chamadas["codigos_anteriores"] is None
    api.obter_codigos_celular_por_nome_pessoa.assert_not_called()


# === Device real: sem ativação ===
def test_device_real_nao_ativa_so_marca_sem_foto(api, device_real):
    # O celular do device real não sobe desativado: esperar um código
    # novo para ativar travaria 60s.
    api.obter_codigo_celular_por_nome_pessoa.return_value = 7

    codigo = _ativar_celular_antes_unlock(api, "TesterN95", None)

    assert codigo == 7
    api.aguardar_e_ativar_celular_mais_recente.assert_not_called()
    api.definir_sem_foto.assert_called_once_with(7, sem_foto=True)


def test_device_real_nao_busca_os_celulares_de_antes(
    monkeypatch, api, device_real
):
    chamadas = _primeiro_acesso(monkeypatch, api)

    assert chamadas["codigos_anteriores"] is None
    api.obter_codigos_celular_por_nome_pessoa.assert_not_called()
