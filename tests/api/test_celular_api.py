import pytest

from utils.logger import get_logger

logger = get_logger(__name__)


def _garantir_reativacao(celular_api, codigo: int) -> None:
    """
    Deixa o celular ativo ao final, mesmo que o teste falhe no meio.

    Não propaga erro: o teardown não pode mascarar a falha original.
    """
    try:
        celular_api.ativar_celular(codigo)

    except Exception:
        logger.exception(
            "Falha ao garantir a reativação do celular no teardown",
            extra={
                "event": "device_reactivation_after_test_failed",
                "device_id": codigo,
            },
        )


@pytest.mark.ct("CT014")
@pytest.mark.api
def test_deve_alternar_status_celular(
    celular_api,
    monitor_nome_pessoa,
):
    """
    Valida a desativação e a reativação do celular mais recente da
    pessoa pela API.

    Busca, extração do código e validação da resposta ficam no
    MonitorCelularClient: resposta com success=false já levanta no
    client, com a mensagem da API, e o teste falha por ela.
    """
    codigo = celular_api.obter_codigo_celular_por_nome_pessoa(
        monitor_nome_pessoa
    )

    try:
        celular_api.desativar_celular(codigo)
        celular_api.ativar_celular(codigo)

    finally:
        _garantir_reativacao(celular_api, codigo)
