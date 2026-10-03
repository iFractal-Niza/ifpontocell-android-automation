import os

from utils.report_dashboard import build_dashboard_html


# === Dashboard e relatório HTML ===
def _load_inline_asset(
    project_root: str,
    nome: str,
) -> str:
    """
    Lê um arquivo de reports/assets para embutir no relatório.

    Retorna uma string vazia quando o arquivo não está disponível.
    """
    caminho = os.path.join(
        project_root,
        "reports",
        "assets",
        nome,
    )

    if not os.path.exists(caminho):
        return ""

    with open(
        caminho,
        encoding="utf-8",
    ) as arquivo:
        return arquivo.read()


def load_inline_css(
    project_root: str,
) -> str:
    """
    Carrega o CSS utilizado no dashboard do relatório HTML.
    """
    return _load_inline_asset(project_root, "style.css")


def load_inline_js(
    project_root: str,
) -> str:
    """
    Carrega o script embutido no report: traduz e enxuga os filtros
    nativos do pytest-html e amplia as imagens na própria página.
    """
    return _load_inline_asset(project_root, "report.js")


def build_results_summary_html(
    project_root: str,
    stats: dict,
) -> tuple[str, str]:
    """
    Monta o conteúdo do dashboard do relatório HTML.

    Inclui:
    - CSS customizado.
    - Resumo das métricas da execução.
    - Rodapé do relatório.
    """
    stats = stats or {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "success_rate": 0.0,
    }

    inline_css = load_inline_css(project_root)
    dashboard_html = build_dashboard_html(
        stats,
    )

    return inline_css, dashboard_html
