"""
Histórico das execuções (reports/history.json), para o dashboard dizer
o que mudou: falhas novas, falhas que já vinham de antes e testes
instáveis. Enxuto de propósito: sem gráfico de tendência (já foi testado
e poluía o report).

Cada execução guarda a data e o status final de cada teste que rodou.
Execuções parciais (ex.: make holerite) também entram: cada teste é
comparado com a última execução em que ele rodou.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from observability import pastas

ARQUIVO = Path(pastas.REPORTS_DIR) / "history.json"

MAX_EXECUCOES = 30
# Quantas aparições recentes de um teste olhar para dizer se é instável.
JANELA_INSTAVEL = 5
# Quantas trocas entre passar e falhar na janela tornam o teste instável.
# Com uma troca só, ele quebrou ou foi corrigido; instável é o que vai e
# volta (passou -> falhou -> passou).
MIN_TROCAS_INSTAVEL = 2

FALHAS = ("failed", "error")
FORMATO_DATA = "%d/%m/%Y %H:%M"


@dataclass
class FalhaRecorrente:
    titulo: str
    desde: str


@dataclass
class ResumoHistorico:
    tem_anteriores: bool = False
    falhas_novas: list[str] = field(default_factory=list)
    falhas_recorrentes: list[FalhaRecorrente] = field(default_factory=list)
    instaveis: list[str] = field(default_factory=list)

    def para_dashboard(self) -> dict:
        return {
            "tem_anteriores": self.tem_anteriores,
            "falhas_novas": list(self.falhas_novas),
            "falhas_recorrentes": [
                {"titulo": f.titulo, "desde": f.desde}
                for f in self.falhas_recorrentes
            ],
            "instaveis": list(self.instaveis),
        }


# === Arquivo ===
def carregar(arquivo: Path | None = None) -> list[dict]:
    """Execuções anteriores, da mais antiga à mais recente."""
    try:
        dados = json.loads((arquivo or ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    return dados if isinstance(dados, list) else []


def salvar(execucoes: list[dict], arquivo: Path | None = None) -> None:
    destino = arquivo or ARQUIVO
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(execucoes[-MAX_EXECUCOES:], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def montar_execucao(agora: datetime, por_teste: dict) -> dict:
    return {
        "data": agora.strftime(FORMATO_DATA),
        "testes": {
            nodeid: {"status": dados["status"], "titulo": dados["titulo"]}
            for nodeid, dados in por_teste.items()
        },
    }


# === Análise ===
def _aparicoes(execucoes: list[dict], nodeid: str) -> list[tuple[str, str]]:
    """(data, status) das execuções em que o teste rodou, em ordem."""
    return [
        (execucao.get("data", ""), execucao["testes"][nodeid]["status"])
        for execucao in execucoes
        if nodeid in execucao.get("testes", {})
    ]


def resumir(anteriores: list[dict], atual: dict) -> ResumoHistorico:
    resumo = ResumoHistorico(tem_anteriores=bool(anteriores))

    for nodeid, dados in atual.get("testes", {}).items():
        titulo = dados.get("titulo") or nodeid
        passado = _aparicoes(anteriores, nodeid)

        if dados["status"] in FALHAS:
            if not passado or passado[-1][1] not in FALHAS:
                resumo.falhas_novas.append(titulo)
            else:
                desde = passado[-1][0]

                for data, status in reversed(passado):
                    if status not in FALHAS:
                        break

                    desde = data

                resumo.falhas_recorrentes.append(
                    FalhaRecorrente(titulo, desde)
                )

        # Pulado não é resultado: não conta como passar nem falhar.
        recentes = [
            status in FALHAS
            for _, status in (passado + [("", dados["status"])])[
                -JANELA_INSTAVEL:
            ]
            if status != "skipped"
        ]
        trocas = sum(
            a != b for a, b in zip(recentes, recentes[1:], strict=False)
        )

        if trocas >= MIN_TROCAS_INSTAVEL:
            resumo.instaveis.append(titulo)

    return resumo
