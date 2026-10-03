"""
Sonda o contrato de escrita em pag=configuracao_app.

Responde duas perguntas antes de escrever qualquer método de teste que
mexa na config GLOBAL (tela "Configuração > Botões"/"Configurações"):

1. O campo 'k' é obrigatório?
2. O 'originalValue' é trava otimista ou só telemetria?

Por que isso importa para os testes:
- Se 'originalValue' for trava otimista, então TODO cmd=up na config
  global exige ler o valor atual antes (get -> up). Isso torna o teardown
  de "salvar e restaurar" obrigatório, não opcional.
- Se for dispensável, o teardown pode repor um default conhecido sem ler.

Uso, a partir da raiz do projeto:

    python scripts/sondar_configuracao_app.py

O estado é restaurado ao final, mas confira a tela depois de rodar.

NOTA: usa ConfiguracaoAppClient (PAG='configuracao_app'), o dono desse
pag. O payload é montado pelos primitivos da base (_build_payload +
_post + _parse_response + _validar_resposta_negocio) porque a sondagem
precisa injetar campos extras (originalValue, k) que os métodos de
negócio não expõem. O 'pag' vem de client.PAG — não passar manualmente.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, RAIZ)


from config.env_loader import carregar_env, resolver_env_file  # noqa: E402

if not carregar_env():
    raise SystemExit(
        f"env.yaml não encontrado ou vazio em {resolver_env_file()}. "
        "Defina IFPONTO_ENV_FILE ou crie o arquivo."
    )

from api.configuracao_app_client import ConfiguracaoAppClient  # noqa: E402

# Slug confirmado no DevTools. 'alerts' também serve.
CODIGO = "mood"


def tentar(
    client: ConfiguracaoAppClient,
    descricao: str,
    value: str,
    **extra,
) -> bool:
    """
    Executa um cmd=up e informa se a API aceitou.

    O 'pag' vem de client.PAG (=configuracao_app) via _build_payload;
    não é passado aqui. 'extra' injeta campos de sondagem como
    originalValue e k.
    """
    print(f"\n--- {descricao} ---")

    payload = client._build_payload(
        cmd="up",
        codigo=CODIGO,
        campo="ativo",
        value=value,
        **extra,
    )

    print(f"payload: {payload}")

    try:
        resposta = client._parse_response(client._post(payload))

        client._validar_resposta_negocio(
            resposta,
            operacao=descricao,
        )

    except Exception as erro:
        print(f"RECUSADO -> {type(erro).__name__}: {erro}")
        return False

    print(f"ACEITO -> {resposta}")
    return True


def main() -> None:
    client = ConfiguracaoAppClient(
        base_url=os.getenv("API_BASE_URL", ""),
        user=os.getenv("API_USER", ""),
        token_original=os.getenv("API_TOKEN", ""),
    )

    try:
        sem_nada = tentar(
            client,
            "sem k, sem originalValue",
            value="false",
        )

        com_original = False

        if not sem_nada:
            com_original = tentar(
                client,
                "com originalValue, sem k",
                value="false",
                originalValue="true",
            )

        print("\n=== restaurando estado ===")

        tentar(
            client,
            "restaurar ativo=true",
            value="true",
            originalValue="false",
        )

        print("\n=== conclusão ===")

        if sem_nada:
            print(
                "k e originalValue são dispensáveis. "
                "Teardown pode repor default sem ler antes."
            )
        elif com_original:
            print(
                "originalValue é obrigatório: trava otimista. "
                "Todo up precisa de um get antes -> teardown DEVE "
                "salvar-e-restaurar (ler o valor original primeiro)."
            )
        else:
            print(
                "Ambas recusadas. Provavelmente o 'k' é exigido. "
                "Confirmar com o dev como ele é gerado."
            )

    finally:
        client.session.close()


if __name__ == "__main__":
    main()
