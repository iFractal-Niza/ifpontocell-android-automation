"""
Normalização de textos lidos da tela, para comparar com o esperado sem
falhar por detalhe de tipografia.
"""

import re
import unicodedata

# Traços que o app/fonte pode exibir no lugar do hífen comum.
_TRACOS = str.maketrans({"–": "-", "—": "-", "‐": "-", "‑": "-"})


def normalizar_texto(texto: str) -> str:
    """
    Troca traços tipográficos por hífen e junta espaços (inclusive os
    especiais, como o não separável) e quebras de linha em um espaço só.
    Unifica a forma dos acentos (NFC) sem removê-los; não mexe em
    maiúsculas.
    """
    texto = unicodedata.normalize("NFC", texto or "").translate(_TRACOS)

    return re.sub(r"\s+", " ", texto).strip()
