from typing import Any

import pytest

from utils.logger import get_logger


logger = get_logger(__name__)


# === Helpers ===
def validar_resposta_sucesso(
    resposta: Any,
    operacao: str,
) -> None:
    """
    Valida a resposta retornada pela API nas operações de status.
    """
    assert resposta is not None, (
        f"A API não retornou resposta ao {operacao} o celular."
    )

    if not isinstance(resposta, dict):
        return

    sucesso = resposta.get("success")

    if sucesso not in (False, 0, "false", "False"):
        return

    mensagem = (
        resposta.get("info")
        or resposta.get("message")
        or resposta.get("mensagem")
        or resposta
    )

    pytest.fail(
        f"Falha ao {operacao} o celular: {mensagem}"
    )


def extrair_codigo_registro(
    registro: dict[str, Any],
) -> int:
    """
    Extrai o código do celular utilizando as chaves conhecidas.
    """
    codigo = (
        registro.get("codigo")
        or registro.get("cod")
        or registro.get("id")
        or registro.get("device_id")
        or registro.get("celular_codigo")
    )

    if codigo is None:
        raise ValueError(
            "O registro retornado pela API não possui "
            "um identificador de celular."
        )

    try:
        return int(codigo)

    except (TypeError, ValueError) as error:
        raise ValueError(
            f"O código do celular é inválido: {codigo!r}"
        ) from error


def obter_dados_celular_atual(
    celular_api,
    monitor_nome_pessoa: str,
) -> dict[str, Any]:
    """
    Obtém o registro mais recente do celular associado à pessoa.
    """
    nome_pessoa = monitor_nome_pessoa.strip()

    if not nome_pessoa:
        raise ValueError(
            "MONITOR_NOME_PESSOA não foi configurado."
        )

    registro = (
        celular_api
        .obter_registro_celular_por_nome_pessoa(
            nome_pessoa
        )
    )

    codigo = extrair_codigo_registro(registro)

    ultima_comunicacao = str(
        registro.get("ultima_comunicacao")
        or registro.get("ultima comunicação")
        or ""
    ).strip()

    logger.info(
        "Dados do celular atual obtidos",
        extra={
            "event": "current_device_data_resolved",
            "person_name": nome_pessoa,
            "device_id": codigo,
            "ultima_comunicacao": ultima_comunicacao,
        },
    )

    return {
        "registro": registro,
        "codigo": codigo,
        "ultima_comunicacao": ultima_comunicacao,
    }


def alterar_status_celular(
    celular_api,
    dados_celular: dict[str, Any],
    ativo: bool,
) -> None:
    """
    Atualiza o status do celular informado.
    """
    operacao = "ativar" if ativo else "desativar"

    logger.info(
        "Iniciando alteração do status do celular",
        extra={
            "event": "device_status_change_started",
            "operation": operacao,
            "device_id": dados_celular["codigo"],
            "device_active": ativo,
            "ultima_comunicacao": (
                dados_celular["ultima_comunicacao"]
            ),
        },
    )

    resposta = celular_api.atualizar_status_celular(
        codigo=dados_celular["codigo"],
        ativo=ativo,
    )

    validar_resposta_sucesso(
        resposta=resposta,
        operacao=operacao,
    )

    logger.info(
        "Status do celular alterado com sucesso",
        extra={
            "event": "device_status_changed",
            "operation": operacao,
            "device_id": dados_celular["codigo"],
            "device_active": ativo,
        },
    )


def desativar_celular(
    celular_api,
    dados_celular: dict[str, Any],
) -> None:
    alterar_status_celular(
        celular_api=celular_api,
        dados_celular=dados_celular,
        ativo=False,
    )


def ativar_celular(
    celular_api,
    dados_celular: dict[str, Any],
) -> None:
    alterar_status_celular(
        celular_api=celular_api,
        dados_celular=dados_celular,
        ativo=True,
    )


def garantir_reativacao_celular(
    celular_api,
    dados_celular: dict[str, Any],
) -> None:
    """
    Garante que o mesmo celular permaneça ativo ao final do teste.
    """
    try:
        ativar_celular(
            celular_api=celular_api,
            dados_celular=dados_celular,
        )

        logger.info(
            "Reativação do celular garantida no teardown",
            extra={
                "event": "device_reactivation_after_test",
                "device_id": dados_celular["codigo"],
            },
        )

    except Exception:
        logger.exception(
            "Falha ao garantir a reativação do celular no teardown",
            extra={
                "event": "device_reactivation_after_test_failed",
                "device_id": dados_celular["codigo"],
            },
        )


# === Testes ===
@pytest.mark.api
def test_deve_alternar_status_celular(
    celular_api,
    monitor_nome_pessoa,
):
    dados_celular = obter_dados_celular_atual(
        celular_api=celular_api,
        monitor_nome_pessoa=monitor_nome_pessoa,
    )

    logger.info(
        "Iniciando teste de alternância do status do celular",
        extra={
            "event": "test_toggle_device_status_started",
            "person_name": monitor_nome_pessoa,
            "device_id": dados_celular["codigo"],
            "ultima_comunicacao": (
                dados_celular["ultima_comunicacao"]
            ),
        },
    )

    try:
        desativar_celular(
            celular_api=celular_api,
            dados_celular=dados_celular,
        )

        ativar_celular(
            celular_api=celular_api,
            dados_celular=dados_celular,
        )

        logger.info(
            "Teste de alternância do status do celular concluído",
            extra={
                "event": "test_toggle_device_status_finished",
                "person_name": monitor_nome_pessoa,
                "device_id": dados_celular["codigo"],
            },
        )

    finally:
        garantir_reativacao_celular(
            celular_api=celular_api,
            dados_celular=dados_celular,
        )