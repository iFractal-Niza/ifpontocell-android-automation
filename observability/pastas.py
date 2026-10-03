"""
Pasta onde a execução grava o report, prints, vídeos, histórico e o
aviso de pulados.

Padrão: reports/. Com IFPONTO_REPORTS_DIR (o Makefile define com
DEVICE=..., ex.: reports/real), cada aparelho tem a sua: emulador e
celular rodando ao mesmo tempo não se atropelam. Os assets do report
(CSS, JS) ficam sempre em reports/assets.
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REPORTS_DIR = os.path.abspath(
    os.getenv("IFPONTO_REPORTS_DIR") or os.path.join(PROJECT_ROOT, "reports")
)
