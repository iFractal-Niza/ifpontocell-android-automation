"""
Decisão da fixture de Home autenticada (tests.fixtures.jornada.
_garantir_home_autenticada): desbloquear, relançar ou fazer o primeiro
acesso. Páginas e flows são substituídos por falsos.
"""

from unittest.mock import Mock

import pytest

from tests.fixtures import jornada

CREDENCIAIS = {
    "sistema": "exemplo",
    "usuario": "u",
    "senha": "s",
    "pin": "1111",
}


@pytest.fixture
def cenario(monkeypatch):
    """
    Monta o cenário: 'estados' diz, a cada checagem, se o app parece
    logado (Home ou PIN visíveis). Devolve os mocks para conferência.
    """

    def montar(*estados: bool):
        leituras = iter(estados)

        home = Mock()
        home.SHORT_TIMEOUT = 2
        home.LONG_TIMEOUT = 8
        home.esta_na_home.side_effect = lambda timeout: next(leituras)

        unlock = Mock()
        unlock.esta_na_tela_unlock.return_value = False

        monkeypatch.setattr(jornada, "HomePage", lambda driver: home)
        monkeypatch.setattr(jornada, "UnlockPage", lambda driver: unlock)

        desbloquear = Mock(return_value="home_desbloqueada")
        primeiro_acesso = Mock(return_value="home_primeiro_acesso")
        monkeypatch.setattr(jornada, "garantir_home_desbloqueada", desbloquear)
        monkeypatch.setattr(
            jornada, "realizar_primeiro_acesso", primeiro_acesso
        )
        monkeypatch.setattr(jornada, "logger", Mock())

        session = Mock()

        resultado = jornada._garantir_home_autenticada(
            session=session,
            credenciais=CREDENCIAIS,
            celular_api=Mock(),
            monitor_nome_pessoa="P",
            motivo="teste",
        )

        return resultado, session, desbloquear, primeiro_acesso

    return montar


def test_logado_so_desbloqueia(cenario):
    resultado, session, desbloquear, primeiro_acesso = cenario(True)

    assert resultado == "home_desbloqueada"
    session.relaunch.assert_not_called()
    primeiro_acesso.assert_not_called()


def test_tela_desconhecida_relanca_e_desbloqueia(cenario):
    # Caso real: pedido de senha da Conta Apple tirou o app da frente.
    resultado, session, desbloquear, primeiro_acesso = cenario(False, True)

    assert resultado == "home_desbloqueada"
    session.relaunch.assert_called_once()
    primeiro_acesso.assert_not_called()


def test_nao_logado_mesmo_apos_relancar_faz_primeiro_acesso(cenario):
    resultado, session, desbloquear, primeiro_acesso = cenario(False, False)

    assert resultado == "home_primeiro_acesso"
    session.relaunch.assert_called_once()
    desbloquear.assert_not_called()
