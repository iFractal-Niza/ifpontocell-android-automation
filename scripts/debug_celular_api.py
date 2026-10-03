import json
import sys
from pathlib import Path

import yaml

# === Raiz do projeto ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from api.monitor_celular_client import MonitorCelularClient  # noqa: E402
from config.env_loader import resolver_env_file  # noqa: E402

ENV_FILE = resolver_env_file()


def carregar_configuracao() -> dict[str, str]:
    if not ENV_FILE.is_file():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {ENV_FILE}"
        )

    with ENV_FILE.open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        configuracao = yaml.safe_load(arquivo) or {}

    campos_obrigatorios = (
        "API_BASE_URL",
        "API_USER",
        "API_TOKEN",
        "MONITOR_NOME_PESSOA",
    )

    campos_ausentes = [
        campo
        for campo in campos_obrigatorios
        if not str(configuracao.get(campo, "")).strip()
    ]

    if campos_ausentes:
        raise ValueError(
            "Configurações obrigatórias ausentes em "
            f"{ENV_FILE}: {', '.join(campos_ausentes)}"
        )

    return configuracao


def exibir_resposta(
    titulo: str,
    resposta: object,
) -> None:
    print(f"\n=== {titulo} ===")

    if isinstance(
        resposta,
        (dict, list),
    ):
        print(
            json.dumps(
                resposta,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    print(resposta)


def main() -> None:
    configuracao = carregar_configuracao()

    cliente = MonitorCelularClient(
        base_url=str(configuracao["API_BASE_URL"]),
        user=str(configuracao["API_USER"]),
        token_original=str(configuracao["API_TOKEN"]),
    )

    nome_pessoa = str(configuracao["MONITOR_NOME_PESSOA"]).strip()

    # Filtragem por nome é feita por listar_registros_celular_por_nome_pessoa.
    # listar_celulares(page, limit) não aceita 'filtro' — a chamada antiga
    # com filtro=... estourava TypeError.
    resposta_listagem = cliente.listar_registros_celular_por_nome_pessoa(
        nome_pessoa
    )

    exibir_resposta(
        "RESPOSTA DA LISTAGEM",
        resposta_listagem,
    )

    codigo = cliente.obter_codigo_celular_por_nome_pessoa(nome_pessoa)

    print(f"\nCódigo localizado: {codigo}")

    resposta_ativacao = cliente.ativar_celular(codigo)

    exibir_resposta(
        "RESPOSTA DA ATIVAÇÃO",
        resposta_ativacao,
    )


if __name__ == "__main__":
    main()
