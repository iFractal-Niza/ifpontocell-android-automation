import os

from utils.report_dashboard import build_dashboard_html


# === Dashboard e relatório HTML ===
def load_inline_css(
    project_root: str,
) -> str:
    """
    Carrega o CSS utilizado no dashboard do relatório HTML.

    Retorna uma string vazia quando o arquivo de estilos
    não está disponível.
    """
    css_path = os.path.join(
        project_root,
        "reports",
        "assets",
        "style.css",
    )

    if not os.path.exists(css_path):
        return ""

    with open(
        css_path,
        "r",
        encoding="utf-8",
    ) as css_file:
        return css_file.read()


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

    inline_css = load_inline_css(
        project_root
    )
    dashboard_html = build_dashboard_html(
        stats,
    )

    return inline_css, dashboard_html