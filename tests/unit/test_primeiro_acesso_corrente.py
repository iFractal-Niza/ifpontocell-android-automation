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

    monkeypatch.setattr(
        flows, "realizar_login", lambda **_: passos.append("login") or Mock()
    )
    monkeypatch.setattr(
        flows, "realizar_unlock", lambda **_: passos.append("unlock")
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


def test_ja_no_onboarding_nao_faz_nada(monkeypatch, chamadas):
    _etapas(monkeypatch, flows.ETAPA_ONBOARDING)

    flows.levar_ao_onboarding(Mock(), CREDENCIAIS, Mock(), "T", {})

    assert chamadas == []


def test_logado_zera_pelo_app(monkeypatch, chamadas):
    # Ex.: APP_SOURCE=package, que não reinstala: o app já está logado.
    _etapas(monkeypatch, flows.ETAPA_LOGADO)

    flows.levar_ao_onboarding(Mock(), CREDENCIAIS, Mock(), "T", {})

    assert chamadas == ["zerar"]


def test_parado_no_login_conclui_o_acesso_antes_de_zerar(
    monkeypatch, chamadas
):
    _etapas(monkeypatch, flows.ETAPA_LOGIN)

    flows.levar_ao_onboarding(Mock(), CREDENCIAIS, Mock(), "T", {})

    assert chamadas == ["login", "unlock", "zerar"]


def test_tela_desconhecida_falha_com_mensagem(monkeypatch, chamadas):
    _etapas(monkeypatch, None)

    with pytest.raises(
        AssertionError, match="Nenhuma tela do primeiro acesso"
    ):
        flows.levar_ao_onboarding(Mock(), CREDENCIAIS, Mock(), "T", {})


def test_ja_na_criacao_do_pin_continua_dali(monkeypatch, chamadas):
    _etapas(monkeypatch, flows.ETAPA_CRIAR_PIN)

    flows.levar_a_criacao_do_pin(Mock(), CREDENCIAIS, Mock(), "T", {})

    assert chamadas == []


def test_login_nao_consulta_a_api(monkeypatch, chamadas):
    # No Android não há códigos de antes do login a guardar (sem ativação).
    api = Mock()

    flows.fazer_login_ate_criar_pin(Mock(), CREDENCIAIS, api, "T", {})

    assert chamadas == ["login"]
    api.obter_codigos_celular_por_nome_pessoa.assert_not_called()


def test_concluir_vai_do_pin_a_home(monkeypatch, chamadas):
    flows.concluir_primeiro_acesso(
        Mock(), CREDENCIAIS, Mock(), "T", {}, tratar_popups_home=False
    )

    assert chamadas == ["unlock"]
