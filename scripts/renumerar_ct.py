"""
Renumera os casos de teste (CT) na ordem da suíte (a mesma do make run).

    make renumerar-ct            # só mostra o mapa (não altera nada)
    make renumerar-ct aplicar=1  # aplica nos markers e nos textos dos testes

Renumerar muda o que um CT significa: um report já compartilhado passa a
apontar para outro cenário. Faça antes de compartilhar reports.
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qa_observability.automacao import atual  # noqa: E402
from qa_observability.casos_teste import (  # noqa: E402
    aplicar_renumeracao,
    casos_na_ordem_da_suite,
    ler_casos,
    mapa_de_renumeracao,
    validar_casos,
)


def main(argumentos: list[str]) -> int:
    aplicar = "--aplicar" in argumentos

    erros = validar_casos(ler_casos())

    if erros:
        print("Corrija os CTs antes de renumerar:")

        for erro in erros:
            print(f"  - {erro}")

        return 1

    casos = casos_na_ordem_da_suite()
    mapa = mapa_de_renumeracao(casos)
    mudancas = {atual: novo for atual, novo in mapa.items() if atual != novo}

    for caso in casos:
        novo = mapa.get(caso.id, "")
        marca = "  <- muda" if caso.id != novo else ""
        print(f"  {caso.id} -> {novo}  {caso.nodeid}{marca}")

    if not mudancas:
        print("\nOs CTs já seguem a ordem da suíte. Nada a fazer.")
        return 0

    if not aplicar:
        print(
            f"\n{len(mudancas)} CT(s) mudariam. Nada foi alterado; para "
            "aplicar: make renumerar-ct aplicar=1"
        )
        return 0

    arquivos = [
        arquivo
        for pasta in atual().pastas_com_ct
        for arquivo in sorted((PROJECT_ROOT / pasta).glob("test_*.py"))
    ]
    alterados = aplicar_renumeracao(mudancas, arquivos)

    print(
        f"\n{len(mudancas)} CT(s) renumerados em {len(alterados)} arquivo(s)."
    )

    citacoes = [
        documento.name
        for documento in sorted(PROJECT_ROOT.glob("*.md"))
        if any(
            ct in documento.read_text(encoding="utf-8")
            for ct in re.findall(r"CT\d{3}", " ".join(mudancas))
        )
    ]

    if citacoes:
        print(
            "Revise as citações de CT nestes documentos (não são "
            f"alteradas automaticamente): {', '.join(citacoes)}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
