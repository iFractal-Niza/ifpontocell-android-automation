"""
Carga do env.<device>.yaml para o os.environ.

Único ponto que sabe onde fica o arquivo e como os valores viram
variáveis de ambiente. Usado pelo conftest (antes da coleta) e pelos
scripts avulsos de scripts/.
"""

import os
from pathlib import Path

import yaml

from config.settings import ConfiguracaoInvalida
from utils.logger import get_logger

logger = get_logger("env_loader")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolver_env_file() -> Path:
    """
    Caminho do env do aparelho: IFPONTO_ENV_FILE, se definida (o Makefile
    define com DEVICE=...); senão config/env.emulator.yaml (fora do
    controle de versão).
    """
    return (
        Path(
            os.getenv(
                "IFPONTO_ENV_FILE",
                PROJECT_ROOT / "config" / "env.emulator.yaml",
            )
        )
        .expanduser()
        .resolve()
    )


class _LoaderSemChaveRepetida(yaml.SafeLoader):
    """
    SafeLoader que recusa chave repetida. O YAML padrão fica com a última
    em silêncio: um ANDROID_LOCATION_ENABLED: "true" seguido, mais abaixo, de
    um "false" esquecido vale "false" sem ninguém perceber.
    """

    def construct_mapping(self, node, deep=False):
        linhas: dict = {}
        repetidas = []

        for chave_node, _ in node.value:
            chave = self.construct_object(chave_node, deep=deep)
            linha = chave_node.start_mark.line + 1

            if chave in linhas:
                repetidas.append(
                    f"{chave} aparece mais de uma vez "
                    f"(linhas {linhas[chave]} e {linha}); apague uma: "
                    "senão vale a última, em silêncio."
                )
            else:
                linhas[chave] = linha

        if repetidas:
            raise ConfiguracaoInvalida(repetidas)

        return super().construct_mapping(node, deep=deep)


def ler_yaml(caminho: Path):
    """
    Conteúdo do arquivo YAML, recusando chave repetida.

    Levanta ConfiguracaoInvalida listando cada chave repetida e as linhas.
    """
    with caminho.open(encoding="utf-8") as file:
        return yaml.load(file, Loader=_LoaderSemChaveRepetida)  # noqa: S506


def carregar_env() -> bool:
    """
    Carrega as variáveis do env.<device>.yaml para o ambiente.

    Retorna False quando o arquivo não existe ou está vazio (com aviso
    no log); quem chama decide se isso é fatal.

    - Chave sem valor ("ANDROID_UDID:") vira "", não a string "None".
    - Variável já exportada no shell tem precedência, permitindo
      override pontual (ex.: ANDROID_LOCATION_ENABLED=true make jornada).
    - Chave repetida levanta ConfiguracaoInvalida (ver ler_yaml).
    """
    env_path = resolver_env_file()

    if not env_path.is_file():
        logger.warning(
            "Arquivo env.<device>.yaml não encontrado em "
            f"{env_path}. Defina IFPONTO_ENV_FILE ou crie "
            "o arquivo antes de executar a suíte."
        )
        return False

    data = ler_yaml(env_path)

    if not data:
        logger.warning(
            "Arquivo env.<device>.yaml está vazio. "
            "Preencha as configurações antes da execução."
        )
        return False

    sobrescritas_pelo_shell = []

    for key, value in data.items():
        if key in os.environ:
            sobrescritas_pelo_shell.append(key)
            continue

        os.environ[key] = "" if value is None else str(value)

    if sobrescritas_pelo_shell:
        logger.info(
            "Variáveis do env.<device>.yaml sobrescritas pelo shell: "
            f"{', '.join(sorted(sobrescritas_pelo_shell))}"
        )

    logger.info("Variáveis de ambiente carregadas com sucesso")

    return True
