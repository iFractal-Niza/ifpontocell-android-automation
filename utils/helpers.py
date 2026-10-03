import os
import re
from datetime import datetime


# =========================
# DATA / TEMPO
# =========================
def current_timestamp(fmt: str = "%Y-%m-%d_%H-%M-%S") -> str:
    """
    Retorna o timestamp atual formatado para uso em logs e nomes de arquivo.
    """
    return datetime.now().strftime(fmt)


# =========================
# DIRETÓRIOS
# =========================
def ensure_dir(path: str) -> None:
    """
    Garante que o diretório informado exista, criando-o se necessário.
    Ignorado silenciosamente quando o caminho é vazio.
    """
    if path:
        os.makedirs(path, exist_ok=True)


# =========================
# STRINGS / FILE NAMES
# =========================
def safe_file_name(name: str) -> str:
    """
    Normaliza um nome de arquivo removendo caracteres inválidos e espaços.
    Substitui os caracteres problemáticos por underscore.
    """
    return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_")


def build_file_name(
    test_name: str,
    context: str = "",
    extension: str = "",
) -> str:
    """
    Monta um nome de arquivo padronizado para evidências e artefatos.

    O nome é composto por: nome do teste + contexto (opcional) + timestamp,
    separados por '__'. A extensão é normalizada para incluir o ponto inicial.
    """
    parts = [safe_file_name(test_name)]

    if context:
        parts.append(safe_file_name(context))

    parts.append(current_timestamp())

    file_name = "__".join(parts)

    if extension:
        ext = extension if extension.startswith(".") else f".{extension}"
        file_name += ext

    return file_name
