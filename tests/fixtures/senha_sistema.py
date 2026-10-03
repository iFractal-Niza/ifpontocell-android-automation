"""
Troca da senha do sistema (aba SENHA SISTEMA): a senha nova vem do
env.<device>.yaml (APP_PASSWORD_NOVA) e uma rede de segurança devolve a senha
original se o teste parar no meio.

A troca é real, no servidor: se a senha ficar trocada, o login de toda
a suíte (e de quem usar esse usuário) quebra. A volta direta (nova ->
original) é aceita pelo sistema.
"""

from dataclasses import dataclass

import pytest

from config.settings import CredenciaisApp
from pages.alterar_senha.alterar_senha_sistema_page import (
    AlterarSenhaSistemaPage,
)
from tests.support.flows import (
    garantir_home_desbloqueada,
    realizar_primeiro_acesso,
)
from utils.exceptions import LoginRejeitadoInesperado
from utils.logger import get_logger

logger = get_logger("fixture_senha_sistema")

CHAVE_SENHA_NOVA = "APP_PASSWORD_NOVA"


def ler_senha_nova(senha_nova: str, senha_atual: str) -> tuple[str, str]:
    """(senha nova, motivo para pular). Motivo vazio quando serve."""
    senha = senha_nova or ""

    if not senha.strip():
        return (
            "",
            f"{CHAVE_SENHA_NOVA} não configurada no config/env.<device>.yaml.",
        )

    if senha == senha_atual:
        return "", f"{CHAVE_SENHA_NOVA} é igual à APP_PASSWORD: nada a trocar."

    return senha, ""


def instrucao_manual(usuario: str) -> str:
    return (
        f"A senha do usuário {usuario!r} pode ter ficado como "
        f"{CHAVE_SENHA_NOVA}. Restaure manualmente: entre no app com ela, "
        "ALTERAR SENHA -> SENHA SISTEMA -> senha atual = APP_PASSWORD_NOVA, "
        "nova e confirmação = APP_PASSWORD."
    )


@pytest.fixture
def senha_nova(app_password) -> str:
    senha, motivo = ler_senha_nova(
        CredenciaisApp.from_env().senha_nova, app_password
    )

    if motivo:
        pytest.skip(motivo)

    return senha


@dataclass
class EstadoDaSenha:
    # True do SALVAR da troca até a senha original ser restaurada pelo
    # próprio teste. Enquanto True, a senha pode estar trocada.
    pode_estar_trocada: bool = False


def _entrar_no_app(sessao, credenciais: dict, senhas: tuple[str, ...]):
    """
    Deixa o app na Home: pelo PIN, se ainda estiver logado; senão (depois
    de Zerar Dados), pelo primeiro acesso, tentando cada senha. Devolve
    a senha que funcionou no login, ou None se entrou pelo PIN.
    """
    sessao.relaunch()

    try:
        garantir_home_desbloqueada(sessao.driver, credenciais["pin"])
        return None
    except AssertionError:
        pass

    for senha in senhas:
        try:
            realizar_primeiro_acesso(
                driver=sessao.driver,
                nome_sistema=credenciais["sistema"],
                usuario=credenciais["usuario"],
                senha=senha,
                pin=credenciais["pin"],
                celular_api=credenciais["celular_api"],
                monitor_nome_pessoa=credenciais["monitor_nome_pessoa"],
            )
            return senha
        except LoginRejeitadoInesperado:
            sessao.relaunch()

    raise AssertionError(
        "Rede de segurança: não foi possível entrar no app nem com a senha "
        "nova nem com a original. " + instrucao_manual(credenciais["usuario"])
    )


@pytest.fixture
def restauracao_da_senha(
    app_session_e2e_registro_ponto,
    app_system,
    app_user,
    app_password,
    app_pin,
    senha_nova,
    celular_api,
    monitor_nome_pessoa,
):
    """
    Rede de segurança: se o teste parar com a senha possivelmente
    trocada, entra no app e troca de volta (nova -> original).
    """
    estado = EstadoDaSenha()

    yield estado

    if not estado.pode_estar_trocada:
        return

    logger.warning(
        "Teste parou com a senha do sistema possivelmente trocada; restaurando"
    )

    sessao = app_session_e2e_registro_ponto
    credenciais = {
        "sistema": app_system,
        "usuario": app_user,
        "pin": app_pin,
        "celular_api": celular_api,
        "monitor_nome_pessoa": monitor_nome_pessoa,
    }

    senha_do_login = _entrar_no_app(
        sessao, credenciais, (senha_nova, app_password)
    )

    if senha_do_login == app_password:
        logger.warning("A senha original ainda vale: nada a restaurar")
        return

    pagina = AlterarSenhaSistemaPage(sessao.driver)
    pagina.acessar()
    mensagens = pagina.trocar_senha(senha_nova, app_password)

    if pagina.MENSAGEM_SUCESSO in mensagens:
        logger.warning("Senha original restaurada pela rede de segurança")
        return

    if senha_do_login == senha_nova:
        raise AssertionError(
            "Rede de segurança: o login entrou com a senha nova, mas a "
            f"volta para a original foi recusada ({mensagens}). "
            + instrucao_manual(app_user)
        )

    # Entrou pelo PIN e a troca de volta foi recusada: a senha atual não
    # era a nova, ou seja, a troca não chegou a acontecer.
    logger.warning(
        "Volta para a senha original recusada; a troca não tinha "
        f"acontecido ({mensagens})"
    )
