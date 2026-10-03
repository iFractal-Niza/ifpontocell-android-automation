"""
Corrente do primeiro acesso (flows: levar_ao_onboarding,
levar_a_criacao_do_pin, fazer_login_ate_criar_pin): cada teste leva o
app à sua etapa a partir de onde ele estiver.
"""

from unittest.mock import Mock

import pytest

from tests.support import flows

CREDENCIAIS = {"sistema": "s", "usuario": "u", "senha": "p", "pin": "1111"}


@pytest.fixture
def chamadas(monkeypatch):
    """Registra os passos executados, sem app."""
    passos = []

    monkeypatch.setattr(flows, "is_emulator", lambda: True)
    monkeypatch.setattr(
        flows, "realizar_login", lambda **_: passos.append("login") or Mock()
    )
    monkeypatch.setattr(
        flows,
        "realizar_unlock",
        lambda **kw: passos.append(("unlock", kw["codigos_anteriores"])),
    )
    monkeypatch.setattr(
        flows, "zerar_dados_pelo_app", lambda *_: passos.append("zerar")
    )
    monkeypatch.setattr(
        flows, "garantir_tela_login", lambda **_: passos.append("tela_login")
    )
    return passos


def _etapas(monkeypatch, *etapas):
    sequencia = iter(etapas)
    monkeypatch.setattr(
        flows, "etapa_do_primeiro_acesso", lambda *_a, **_k: next(sequencia)
    )


def _api(codigos=frozenset({1, 2})):
    api = Mock()
    api.obter_codigos_celular_por_nome_pessoa.return_value = set(codigos)
    return api


def test_ja_no_onboarding_nao_faz_nada(monkeypatch, chamadas):
    _etapas(monkeypatch, flows.ETAPA_ONBOARDING)

    flows.levar_ao_onboarding(Mock(), CREDENCIAIS, _api(), "T", {})

    assert chamadas == []


def test_logado_zera_pelo_app_e_marca_reaproveitamento(monkeypatch, chamadas):
    # Caso do device real: o app não é reinstalado e já está logado.
    _etapas(monkeypatch, flows.ETAPA_LOGADO)
    estado = {"codigos_anteriores": {9}, "reaproveita_celular": False}

    flows.levar_ao_onboarding(Mock(), CREDENCIAIS, _api(), "T", estado)

    assert chamadas == ["zerar"]
    assert estado == {"codigos_anteriores": None, "reaproveita_celular": True}


def test_parado_no_login_conclui_o_acesso_antes_de_zerar(
    monkeypatch, chamadas
):
    _etapas(monkeypatch, flows.ETAPA_LOGIN)

    flows.levar_ao_onboarding(
        Mock(), CREDENCIAIS, _api(), "T", {"reaproveita_celular": False}
    )

    assert chamadas == ["login", ("unlock", {1, 2}), "zerar"]


def test_tela_desconhecida_falha_com_mensagem(monkeypatch, chamadas):
    _etapas(monkeypatch, None)

    with pytest.raises(
        AssertionError, match="Nenhuma tela do primeiro acesso"
    ):
        flows.levar_ao_onboarding(Mock(), CREDENCIAIS, _api(), "T", {})


def test_ja_na_criacao_do_pin_continua_dali(monkeypatch, chamadas):
    _etapas(monkeypatch, flows.ETAPA_CRIAR_PIN)

    flows.levar_a_criacao_do_pin(Mock(), CREDENCIAIS, _api(), "T", {})

    assert chamadas == []


def test_login_guarda_os_codigos_de_antes(monkeypatch, chamadas):
    estado = {"reaproveita_celular": False}

    flows.fazer_login_ate_criar_pin(Mock(), CREDENCIAIS, _api(), "T", estado)

    assert estado["codigos_anteriores"] == {1, 2}


def test_login_depois_de_zerar_nao_busca_codigos(monkeypatch, chamadas):
    api = _api()
    estado = {"reaproveita_celular": True}

    flows.fazer_login_ate_criar_pin(Mock(), CREDENCIAIS, api, "T", estado)

    assert estado["codigos_anteriores"] is None
    api.obter_codigos_celular_por_nome_pessoa.assert_not_called()


def test_concluir_usa_os_codigos_e_limpa_o_estado(monkeypatch, chamadas):
    estado = {"codigos_anteriores": {1}, "reaproveita_celular": True}

    flows.concluir_primeiro_acesso(
        Mock(), CREDENCIAIS, _api(), "T", estado, tratar_popups_home=False
    )

    assert chamadas == [("unlock", {1})]
    assert estado == {"codigos_anteriores": None, "reaproveita_celular": False}
