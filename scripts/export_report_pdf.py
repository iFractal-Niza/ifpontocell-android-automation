from __future__ import annotations

import base64
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote_to_bytes

from weasyprint import CSS, HTML

# === Caminhos ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# A pasta do report pode ser por aparelho (DEVICE=... no make); o CSS de
# impressão fica sempre nos assets.
REPORTS_DIR = Path(
    os.getenv("IFPONTO_REPORTS_DIR") or PROJECT_ROOT / "reports"
).resolve()
PRINT_CSS = PROJECT_ROOT / "reports" / "assets" / "print.css"

_RESULT_ORDER = {
    "error": 0,
    "failed": 1,
    "xpassed": 2,
    "rerun": 3,
    "xfailed": 4,
    "skipped": 5,
    "passed": 6,
}

# O WeasyPrint não executa o reports/assets/report.js, que traduz as
# colunas no HTML: no PDF a tradução é feita aqui.
_COLUNAS = {
    "Result": "Resultado",
    "Test": "Teste",
    "Duration": "Duração",
    "Links": "Evidências",
}


# Categoria e Tipo do erro: preenchidas no navegador (salvas lá pelo
# report.js, não no HTML), então no PDF sairiam sempre vazias. Saem do PDF.
_CELULA_CLASSIFICACAO = re.compile(
    r'<t([hd]) class="col-classificacao[^"]*">.*?</t\1>',
    flags=re.DOTALL,
)


def _sem_classificacao(html_tabela: str) -> str:
    return _CELULA_CLASSIFICACAO.sub("", html_tabela)


def obter_ultimo_report_html() -> Path:
    """
    Retorna o relatório HTML mais recente.
    """
    reports = sorted(
        REPORTS_DIR.glob("*.html"),
        key=lambda arquivo: arquivo.stat().st_mtime,
        reverse=True,
    )

    if not reports:
        raise FileNotFoundError(
            "Nenhum relatório HTML encontrado em "
            f"'{REPORTS_DIR}'. Execute os testes antes de exportar."
        )

    return reports[0]


def _extrair_dados_pytest_html(
    html_text: str,
) -> dict:
    """
    Extrai o JSON usado pelo JavaScript do pytest-html.
    """
    match = re.search(
        r'<div id="data-container"\s+data-jsonblob="(.*?)"></div>',
        html_text,
        flags=re.DOTALL,
    )

    if not match:
        raise ValueError(
            "O data-jsonblob do pytest-html não foi encontrado no relatório."
        )

    return json.loads(html.unescape(match.group(1)))


def _iterar_testes(
    data: dict,
) -> list[dict]:
    testes = [
        teste
        for entradas in data.get("tests", {}).values()
        for teste in entradas
    ]

    return sorted(
        testes,
        key=lambda teste: (
            _RESULT_ORDER.get(
                str(teste.get("result", "")).lower(),
                99,
            ),
            str(teste.get("testId", "")),
        ),
    )


def _decodificar_data_uri_texto(
    uri: str,
) -> str:
    if not uri.startswith("data:text/plain"):
        return ""

    try:
        cabecalho, conteudo = uri.split(
            ",",
            1,
        )
    except ValueError:
        return ""

    try:
        if ";base64" in cabecalho:
            return base64.b64decode(conteudo).decode(
                "utf-8",
                errors="replace",
            )

        return unquote_to_bytes(conteudo).decode(
            "utf-8",
            errors="replace",
        )

    except (
        ValueError,
        UnicodeDecodeError,
    ):
        return ""


def _obter_erro_resumido(
    teste: dict,
) -> str:
    for extra in teste.get(
        "extras",
        [],
    ):
        if (
            extra.get("format_type") == "text"
            and extra.get("name") == "Erro resumido"
        ):
            resumo = _decodificar_data_uri_texto(
                str(
                    extra.get(
                        "content",
                        "",
                    )
                )
            )

            if resumo:
                return resumo.strip()

    log = str(
        teste.get(
            "log",
            "",
        )
    ).strip()

    if not log:
        return "Erro sem mensagem resumida disponível."

    return next(
        (linha.strip() for linha in log.splitlines() if linha.strip()),
        "Erro sem mensagem resumida disponível.",
    )


def _resolver_imagem(
    caminho_original: str,
    html_path: Path,
) -> str | None:
    """
    Resolve o screenshot salvo pelo pytest-html.

    O relatório pode conter um caminho absoluto da máquina que
    executou o teste. Caso ele não exista, tenta localizar o mesmo
    arquivo dentro de reports/screenshots/.
    """
    if not caminho_original:
        return None

    # Imagem embutida no HTML (base64): o WeasyPrint lê o data URI direto.
    if caminho_original.startswith("data:image/"):
        return caminho_original

    original = Path(caminho_original).expanduser()

    candidatos: list[Path] = []

    if original.is_absolute():
        candidatos.append(original)
    else:
        candidatos.append((html_path.parent / original).resolve())

    candidatos.append(REPORTS_DIR / "screenshots" / original.name)

    for candidato in candidatos:
        if candidato.is_file():
            return candidato.resolve().as_uri()

    print(f"[WARN] Screenshot não encontrado para o PDF: {caminho_original}")

    return None


def _obter_screenshot(
    teste: dict,
    html_path: Path,
) -> str | None:
    for extra in teste.get(
        "extras",
        [],
    ):
        if extra.get("format_type") == "image":
            caminho = _resolver_imagem(
                str(
                    extra.get(
                        "content",
                        "",
                    )
                ),
                html_path=html_path,
            )

            if caminho:
                return caminho

    return None


def _renderizar_detalhes_falha(
    teste: dict,
    html_path: Path,
) -> str:
    resultado = str(
        teste.get(
            "result",
            "",
        )
    ).lower()

    if resultado not in {
        "failed",
        "error",
        "xpassed",
    }:
        return ""

    erro = html.escape(_obter_erro_resumido(teste))

    screenshot = _obter_screenshot(
        teste,
        html_path=html_path,
    )

    screenshot_html = ""

    if screenshot:
        screenshot_html = f"""
            <figure class="pdf-media-panel">
                <img
                    src="{html.escape(screenshot, quote=True)}"
                    alt="Screenshot da falha"
                />
                <figcaption>
                    Screenshot da falha
                </figcaption>
            </figure>
        """

    classe_sem_imagem = (
        " pdf-failure-detail--without-media" if not screenshot else ""
    )

    return f"""
        <tr class="extras-row pdf-extras-row">
            <td class="extra" colspan="4">
                <div class="pdf-failure-detail{classe_sem_imagem}">
                    <section class="pdf-error-panel">
                        <span class="pdf-detail-title">
                            Erro resumido
                        </span>

                        <pre class="pdf-error-summary">{erro}</pre>

                        <span class="pdf-html-reference">
                            Detalhes completos e logs permanecem
                            disponíveis no relatório HTML.
                        </span>
                    </section>

                    {screenshot_html}
                </div>
            </td>
        </tr>
    """


def _renderizar_resultados_estaticos(
    data: dict,
    html_path: Path,
) -> str:
    partes: list[str] = []

    for teste in _iterar_testes(data):
        resultado = str(
            teste.get(
                "result",
                "",
            )
        ).lower()

        linhas = _sem_classificacao(
            "".join(
                str(item)
                for item in teste.get(
                    "resultsTableRow",
                    [],
                )
            )
        )

        partes.append(
            f"""
            <tbody class="results-table-row {html.escape(resultado)}">
                <tr class="collapsible pdf-result-row">
                    {linhas}
                </tr>

                {
                _renderizar_detalhes_falha(
                    teste,
                    html_path=html_path,
                )
            }
            </tbody>
            """
        )

    return "\n".join(partes)


def _traduzir_colunas(
    cabecalho_html: str,
) -> str:
    """
    Traduz os títulos das colunas no cabeçalho da tabela de resultados.
    """
    for original, traducao in _COLUNAS.items():
        cabecalho_html = cabecalho_html.replace(
            f">{original}</th>",
            f">{traducao}</th>",
        )

    return cabecalho_html


def _materializar_report_para_pdf(
    html_text: str,
    html_path: Path,
) -> str:
    """
    Materializa os resultados que o pytest-html monta via JavaScript.

    O WeasyPrint não executa JavaScript. Sem esta etapa, os detalhes
    de falha e os screenshots não são criados no DOM usado pelo PDF.
    """
    data = _extrair_dados_pytest_html(html_text)

    resultados = _renderizar_resultados_estaticos(
        data,
        html_path=html_path,
    )

    pattern = re.compile(
        r'(<table id="results-table">.*?'
        r'<thead id="results-table-head">.*?</thead>)'
        r'(.*?)'
        r'(</table>)',
        flags=re.DOTALL,
    )

    if not pattern.search(html_text):
        raise ValueError(
            "A tabela #results-table não foi encontrada no relatório."
        )

    html_text = pattern.sub(
        lambda match: (
            _traduzir_colunas(_sem_classificacao(match.group(1)))
            + resultados
            + match.group(3)
        ),
        html_text,
        count=1,
    )

    # Após materializar a tabela, o data-container e o JavaScript
    # do pytest-html não são mais necessários para o PDF.
    html_text = re.sub(
        r'<footer>\s*'
        r'<div id="data-container".*?</footer>',
        "",
        html_text,
        count=1,
        flags=re.DOTALL,
    )

    html_text = html_text.replace(
        "<body>",
        '<body class="pdf-export">',
        1,
    )

    return html_text


def exportar_report_pdf(
    html_path: Path,
) -> Path:
    """
    Converte o relatório HTML em uma versão PDF estática.

    O HTML original não é alterado.
    """
    pdf_path = html_path.with_suffix(".pdf")

    html_original = html_path.read_text(encoding="utf-8")

    html_para_pdf = _materializar_report_para_pdf(
        html_original,
        html_path=html_path,
    )

    stylesheets = []

    if PRINT_CSS.exists():
        stylesheets.append(
            CSS(
                filename=PRINT_CSS,
            )
        )

    HTML(
        string=html_para_pdf,
        base_url=str(PROJECT_ROOT),
        media_type="screen",
    ).write_pdf(
        target=pdf_path,
        stylesheets=stylesheets,
    )

    return pdf_path


def main() -> None:
    html_path = obter_ultimo_report_html()

    print(f"Exportando relatório: {html_path.name}")

    pdf_path = exportar_report_pdf(html_path)

    print(f"PDF gerado: {pdf_path}")


if __name__ == "__main__":
    main()
