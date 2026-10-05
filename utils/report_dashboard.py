import html
import json
from collections.abc import Mapping
from typing import Any

# === Status da execução ===
HEALTHY_THRESHOLD = 90

# Aplica o tema escolhido (report.js grava em localStorage) antes do
# dashboard ser desenhado, para não piscar o tema claro. Só ASCII: o
# bloco passa por _codificar_ascii_seguro, que não vale dentro de script.
_SCRIPT_TEMA_INICIAL = (
    "<script>try{if(localStorage.getItem('qa-report-tema')==='dark')"
    "{document.documentElement.setAttribute('data-theme','dark');}}"
    "catch(e){}</script>"
)
UNSTABLE_THRESHOLD = 70


# === Conversão e formatação ===
def _safe_text(value: Any) -> str:
    """
    Escapa valores para uso seguro no HTML.
    """
    return html.escape(
        str(value),
        quote=True,
    )


def _to_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    Converte um valor para inteiro de forma segura.
    """
    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Converte um valor para decimal de forma segura.
    """
    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _format_rate(
    value: Any,
) -> str:
    """
    Formata uma porcentagem usando padrão pt-BR.
    """
    rate = round(
        _to_float(value),
        2,
    )

    if rate.is_integer():
        return f"{int(rate)}%"

    return f"{rate:.2f}%".replace(
        ".",
        ",",
    )


def _format_duration(
    value: Any,
) -> str:
    """
    Formata duração em segundos para HH:MM:SS ou MM:SS.

    Mantém valores textuais que já estejam formatados.
    """
    if value in (
        None,
        "",
    ):
        return ""

    if isinstance(
        value,
        str,
    ):
        stripped_value = value.strip()

        if ":" in stripped_value:
            return stripped_value

        try:
            seconds = float(stripped_value)

        except ValueError:
            return stripped_value

    else:
        seconds = _to_float(value)

    total_seconds = max(
        0,
        round(seconds),
    )

    hours, remainder = divmod(
        total_seconds,
        3600,
    )
    minutes, seconds = divmod(
        remainder,
        60,
    )

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def _pluralize(
    quantity: int,
    singular: str,
    plural: str,
) -> str:
    """
    Retorna a palavra adequada para a quantidade informada.
    """
    return singular if quantity == 1 else plural


# === Status e resumo ===
def calcular_taxa_sucesso(
    passed: int,
    failed: int,
    error: int,
) -> float:
    """
    Taxa de sucesso sobre os testes que rodaram.

    Pulado não entra na conta: é teste que não rodou (em geral por falta
    de massa), não reprovação. Sem nenhum teste rodado, a taxa é 0.
    """
    executados = passed + failed + error

    if not executados:
        return 0.0

    return round(passed / executados * 100, 2)


def _get_status_meta(
    success_rate: float,
    *,
    total: int,
    failed: int = 0,
    error: int = 0,
    skipped: int = 0,
    criticas: int = 0,
    critico_pela_taxa: bool = True,
) -> tuple[str, str, str]:
    """
    Retorna classe CSS, rótulo e descrição do status.

    'criticas' são as falhas e erros de testes do smoke (o essencial do
    app). A falha de um teste fora do smoke (ex.: Privacidade) chama
    atenção, mas não é crítica.

    Prioridade:
    - Sem testes, ou todos pulados: sem execução.
    - Falha ou erro em teste do smoke: crítico.
    - Taxa abaixo de 70%: crítico (só na execução inteira, com
      critico_pela_taxa; num fluxo de um teste, uma falha já é 0%).
    - Demais falhas e erros, ou taxa abaixo de 90%: instável.
    - Sem falhas, mas com pulados: aprovado com ressalvas.
    - Demais casos: aprovado.

    A taxa é a de calcular_taxa_sucesso (só os testes que rodaram).
    """
    if total == 0:
        return (
            "neutral",
            "SEM EXECUÇÃO",
            "Nenhum teste foi executado.",
        )

    if skipped >= total:
        return (
            "neutral",
            "SEM EXECUÇÃO",
            "Todos os testes foram pulados.",
        )

    if criticas > 0 or (
        critico_pela_taxa and success_rate < UNSTABLE_THRESHOLD
    ):
        return (
            "failed",
            "CRÍTICO",
            "A execução exige análise imediata.",
        )

    if failed > 0 or error > 0 or success_rate < HEALTHY_THRESHOLD:
        return (
            "unstable",
            "INSTÁVEL",
            "A execução possui resultados que exigem atenção.",
        )

    if skipped > 0:
        # Âmbar: o pulado segue chamando atenção, sem a cor de falha
        # (laranja do instável, vermelho do crítico).
        return (
            "caveat",
            "APROVADO COM RESSALVAS",
            "Nenhuma falha; há testes que não foram executados.",
        )

    return (
        "healthy",
        "APROVADO",
        "A execução foi concluída sem falhas.",
    )


def _build_summary_text(
    *,
    failed: int,
    error: int,
    skipped: int,
    total: int,
    criticas: int = 0,
) -> str:
    """
    Gera o resumo executivo da execução.
    """
    if total == 0:
        return "Nenhum teste foi executado."

    if failed == 0 and error == 0:
        if skipped:
            skipped_label = _pluralize(
                skipped,
                "teste pulado",
                "testes pulados",
            )

            return (
                "Execução concluída sem falhas, "
                f"com {skipped} {skipped_label}."
            )

        return "Execução concluída sem falhas ou erros técnicos."

    problems = []

    if failed:
        failed_label = _pluralize(
            failed,
            "falha funcional",
            "falhas funcionais",
        )
        problems.append(f"{failed} {failed_label}")

    if error:
        error_label = _pluralize(
            error,
            "erro técnico",
            "erros técnicos",
        )
        problems.append(f"{error} {error_label}")

    # Concordância: "falha" é feminina, "erro" é masculino; os dois
    # juntos ficam no masculino plural.
    if failed and error:
        detectado = "detectados"
    elif failed:
        detectado = _pluralize(failed, "detectada", "detectadas")
    else:
        detectado = _pluralize(error, "detectado", "detectados")

    resumo = f"{' e '.join(problems)} {detectado}."

    if not criticas:
        return f"{resumo} Nenhum teste do smoke falhou."

    if criticas == 1:
        return f"{resumo} 1 teste do smoke falhou."

    return f"{resumo} {criticas} testes do smoke falharam."


# === Componentes do dashboard ===
def _build_kpi_card(
    *,
    css_class: str,
    label: str,
    value: Any,
    detail: str = "",
    chave: str = "",
) -> str:
    """
    Monta um card compacto de indicador.
    """
    detail_html = ""

    if detail:
        detail_html = (
            f"<span class='qa-kpi-detail'>{_safe_text(detail)}</span>"
        )

    # data-qa-kpi: o report.js atualiza o card com os testes manuais.
    return f"""
        <div class="qa-kpi-card {css_class}" data-qa-kpi="{chave}">
            <span class="qa-kpi-label">
                {_safe_text(label)}
            </span>

            <strong class="qa-kpi-value">
                {_safe_text(value)}
            </strong>

            {detail_html}
        </div>
    """


def _calculate_flow_metrics(
    data: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Normaliza as métricas de um fluxo.
    """
    passed = _to_int(data.get("ok"))
    failed = _to_int(data.get("fail"))
    error = _to_int(data.get("error"))
    skipped = _to_int(data.get("skip"))

    total = passed + failed + error + skipped

    return {
        "passed": passed,
        "failed": failed,
        "error": error,
        "skipped": skipped,
        "total": total,
        "executed": passed + failed + error,
        "success_rate": calcular_taxa_sucesso(passed, failed, error),
        "duration": _format_duration(data.get("duration")),
    }


# === Qualidade por fluxo ===
def build_fluxo_html_card(
    fluxo: str,
    dados: Mapping[str, Any],
) -> str:
    """
    Monta uma linha compacta com as métricas de um fluxo.
    """
    metrics = _calculate_flow_metrics(dados)

    total = metrics["total"]
    passed = metrics["passed"]
    failed = metrics["failed"]
    error = metrics["error"]
    skipped = metrics["skipped"]
    success_rate = metrics["success_rate"]
    duration = metrics["duration"]

    # Só a cor da barra do fluxo: a etiqueta de status (CRÍTICO,
    # APROVADO...) saiu do dashboard.
    status_class, _, _ = _get_status_meta(
        success_rate,
        total=total,
        failed=failed,
        error=error,
        skipped=skipped,
        criticas=_to_int(dados.get("critico")),
        critico_pela_taxa=False,
    )

    duration_html = ""

    if duration:
        duration_html = f"""
            <span class="qa-flow-meta-item">
                <span>Duração</span>
                <strong>{_safe_text(duration)}</strong>
            </span>
        """

    # Números do fluxo para o report.js somar os testes manuais.
    dados_do_fluxo = html.escape(
        json.dumps(
            {
                "nome": fluxo,
                "ok": passed,
                "fail": failed,
                "error": error,
                "skip": skipped,
                "critico": _to_int(dados.get("critico")),
            }
        )
    )

    return f"""
        <article class="qa-flow-row" data-qa-fluxo="{dados_do_fluxo}">
            <div class="qa-flow-main">
                <div class="qa-flow-heading">
                    <span class="qa-flow-title">
                        {_safe_text(fluxo.upper())}
                    </span>

                </div>

                <div class="qa-flow-summary">
                    <strong>{passed}/{total}</strong>
                    <span>testes aprovados</span>
                </div>
            </div>

            <div class="qa-flow-meta">
                <span class="qa-flow-meta-item">
                    <span>Sucesso</span>
                    <strong>{_format_rate(success_rate)}</strong>
                </span>

                <span class="qa-flow-meta-item passed">
                    <span>Passou</span>
                    <strong>{passed}</strong>
                </span>

                <span class="qa-flow-meta-item failed">
                    <span>Falhou</span>
                    <strong>{failed}</strong>
                </span>

                <span class="qa-flow-meta-item error">
                    <span>Execução</span>
                    <strong>{error}</strong>
                </span>

                <span class="qa-flow-meta-item skipped">
                    <span>Pulados</span>
                    <strong>{skipped}</strong>
                </span>

                {duration_html}
            </div>

            <div
                class="qa-flow-progress-bar"
                role="progressbar"
                aria-label="Taxa de sucesso do fluxo {_safe_text(fluxo)}"
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow="{success_rate}"
            >
                <div
                    class="qa-flow-progress {status_class}"
                    style="width: {success_rate}%;"
                ></div>
            </div>
        </article>
    """


def _build_flows_html(
    fluxos: Mapping[str, Mapping[str, Any]],
) -> str:
    """
    Monta a seção de qualidade por fluxo.

    Preserva a ordem de inserção para refletir a ordem real
    de execução da suíte.
    """
    # qa-fluxos: o report.js acrescenta os fluxos dos testes manuais.
    if not fluxos:
        return """
            <section class="qa-section qa-fluxos">
                <div class="qa-section-header">
                    <div>
                        <span class="qa-section-eyebrow">
                            Cobertura
                        </span>
                        <h3>Qualidade por fluxo</h3>
                    </div>
                </div>

                <div class="qa-empty-state">
                    Nenhum fluxo foi identificado nesta execução.
                </div>

                <div class="qa-flow-list"></div>
            </section>
        """

    flow_rows = "".join(
        build_fluxo_html_card(
            fluxo,
            dados,
        )
        for fluxo, dados in fluxos.items()
    )

    return f"""
        <section class="qa-section qa-fluxos">
            <div class="qa-section-header">
                <div>
                    <span class="qa-section-eyebrow">
                        Cobertura
                    </span>
                    <h3>Qualidade por fluxo</h3>
                </div>
            </div>

            <div class="qa-flow-list">
                {flow_rows}
            </div>
        </section>
    """


# === Identificação da execução ===
def _build_contexto_html(
    contexto: Any,
) -> str:
    """
    Faixa com a identificação da execução (data, duração, ambiente,
    dispositivo, versão do app). 'contexto' é uma lista de pares
    (rótulo, valor); vazia, não gera nada.
    """
    if not isinstance(contexto, (list, tuple)) or not contexto:
        return ""

    itens = "".join(
        f"""
            <div class="qa-context-item">
                <div class="qa-context-label">{_safe_text(rotulo)}</div>
                <strong>{_safe_text(valor)}</strong>
            </div>
        """
        for rotulo, valor in contexto
        if valor
    )

    return f"""
        <div class="qa-context">
            {itens}
        </div>
    """


# === Testes mais demorados ===
MAIS_DEMORADOS = 5


def _formatar_tempo_do_teste(segundos: Any) -> str:
    """Ex.: "<1s", "42s", "02:15"."""
    valor = _to_float(segundos)

    if valor < 1:
        return "<1s"

    if valor < 60:
        return f"{round(valor)}s"

    return _format_duration(valor)


def _build_demorados_html(duracoes: Any) -> str:
    """
    Os testes mais demorados da execução, para saber onde vale otimizar.
    O tempo inclui a preparação do teste (ex.: relançar o app). Com menos
    de dois testes, não há o que comparar e não gera nada.
    """
    if not isinstance(duracoes, Mapping) or len(duracoes) < 2:
        return ""

    demorados = sorted(
        (item for item in duracoes.values() if isinstance(item, Mapping)),
        key=lambda item: _to_float(item.get("segundos")),
        reverse=True,
    )[:MAIS_DEMORADOS]

    itens = "".join(
        f"""
            <li class="qa-caveat-item qa-demorado-item">
                <div class="qa-caveat-test">
                    <div class="qa-caveat-flow">
                        {_safe_text(str(item.get("fluxo", "")).upper())}
                    </div>

                    <strong>{_safe_text(item.get("titulo", ""))}</strong>
                </div>

                <p class="qa-demorado-tempo">
                    {_formatar_tempo_do_teste(item.get("segundos"))}
                </p>
            </li>
        """
        for item in demorados
    )

    return f"""
        <section class="qa-section">
            <div class="qa-section-header">
                <div>
                    <span class="qa-section-eyebrow">
                        Desempenho
                    </span>
                    <h3>Testes mais demorados</h3>
                </div>
            </div>

            <ul class="qa-caveat-list">
                {itens}
            </ul>

            <p class="qa-demorado-nota">
                O tempo inclui a preparação de cada teste (ex.: abrir o app
                ou refazer o primeiro acesso).
            </p>
        </section>
    """


# === Ressalvas ===
def _build_ressalvas_html(
    pulados: Any,
) -> str:
    """
    Lista os testes pulados com o motivo de cada um.

    Responde, no próprio dashboard, quais são as ressalvas do status
    APROVADO COM RESSALVAS. Sem pulados, não gera nada.
    """
    if not isinstance(pulados, list) or not pulados:
        return ""

    itens = "".join(
        f"""
            <li class="qa-caveat-item">
                <div class="qa-caveat-test">
                    <div class="qa-caveat-flow">
                        {_safe_text(str(pulado.get("fluxo", "")).upper())}
                    </div>

                    <strong>
                        {
            _safe_text(
                pulado.get("titulo")
                or str(pulado.get("nodeid", "")).split("::")[-1]
            )
        }
                    </strong>
                </div>

                <p>{_safe_text(pulado.get("motivo", ""))}</p>
            </li>
        """
        for pulado in pulados
        if isinstance(pulado, Mapping)
    )

    return f"""
        <section class="qa-section">
            <div class="qa-section-header">
                <div>
                    <span class="qa-section-eyebrow">
                        Ressalvas
                    </span>
                    <h3>Motivo dos testes pulados</h3>
                </div>
            </div>

            <ul class="qa-caveat-list">
                {itens}
            </ul>
        </section>
    """


# === Dashboard principal ===
def build_dashboard_html(
    dashboard_stats: Mapping[str, Any],
) -> str:
    """
    Monta o dashboard principal do relatório HTML.
    """
    total = _to_int(dashboard_stats.get("total"))
    passed = _to_int(dashboard_stats.get("passed"))
    failed = _to_int(dashboard_stats.get("failed"))
    error = _to_int(dashboard_stats.get("error"))
    skipped = _to_int(dashboard_stats.get("skipped"))
    success_rate = _to_float(dashboard_stats.get("success_rate"))
    criticas = _to_int(dashboard_stats.get("criticas"))

    fluxos = dashboard_stats.get(
        "por_fluxo",
        {},
    )

    if not isinstance(
        fluxos,
        Mapping,
    ):
        fluxos = {}

    (
        status_class,
        status_label,
        status_description,
    ) = _get_status_meta(
        success_rate,
        total=total,
        failed=failed,
        error=error,
        skipped=skipped,
        criticas=criticas,
    )

    summary = _build_summary_text(
        failed=failed,
        error=error,
        skipped=skipped,
        total=total,
        criticas=criticas,
    )

    executed = passed + failed + error

    success_detail = (
        f"{passed} de {executed} executados" if executed else "Sem resultados"
    )

    kpi_cards = "".join(
        (
            _build_kpi_card(
                css_class=(f"success {status_class}"),
                label="Taxa de sucesso",
                chave="taxa",
                value=_format_rate(success_rate),
                detail=success_detail,
            ),
            _build_kpi_card(
                css_class="total",
                label="Total",
                chave="total",
                value=total,
                detail="Testes na execução",
            ),
            _build_kpi_card(
                css_class="passed",
                label="Passou",
                chave="passou",
                value=passed,
                detail="Cenários aprovados",
            ),
            _build_kpi_card(
                css_class=("failed active" if failed else "failed muted"),
                label="Falhou",
                chave="falhou",
                value=failed,
                detail="Falhas funcionais",
            ),
            _build_kpi_card(
                css_class=("error active" if error else "error muted"),
                label="Execução",
                chave="erro",
                value=error,
                detail="Erros técnicos",
            ),
            _build_kpi_card(
                css_class=("skipped active" if skipped else "skipped muted"),
                label="Pulados",
                chave="pulados",
                value=skipped,
                detail="Testes não executados",
            ),
        )
    )

    # Totais da automação para o report.js somar os testes manuais e as
    # melhorias (com as mesmas regras de _get_status_meta e
    # _build_summary_text) sem perder a base.
    totais_automacao = html.escape(
        json.dumps(
            {
                "total": total,
                "passed": passed,
                "failed": failed,
                "error": error,
                "skipped": skipped,
                "criticas": criticas,
                "saudavel": HEALTHY_THRESHOLD,
                "instavel": UNSTABLE_THRESHOLD,
            }
        )
    )

    # Testes manuais previstos (make evidencias): o report.js os inclui no
    # bloco "Testes manuais", sem Status, para o tester preencher.
    previstos = dashboard_stats.get("testes_manuais_previstos") or []
    atributo_previstos = (
        f' data-qa-previstos="{html.escape(json.dumps(previstos))}"'
        if previstos
        else ""
    )

    flows_html = _build_flows_html(fluxos)
    ressalvas_html = _build_ressalvas_html(dashboard_stats.get("pulados"))
    demorados_html = _build_demorados_html(dashboard_stats.get("duracoes"))
    contexto_html = _build_contexto_html(dashboard_stats.get("contexto"))

    return f"""
        {_SCRIPT_TEMA_INICIAL}
        <div
            class="qa-dashboard"
            data-qa-totais="{totais_automacao}"{atributo_previstos}
        >
            <header class="qa-dashboard-header">
                <div class="qa-dashboard-title">
                    <span class="qa-dashboard-eyebrow">
                        Android Automation
                    </span>

                    <h2>Dashboard de execução</h2>

                    <p>
                        Visão consolidada da qualidade da suíte
                        automatizada.
                    </p>
                </div>

                <div class="qa-dashboard-lateral">
                    <div
                        class="qa-theme-toggle"
                        role="group"
                        aria-label="Tema do report"
                    >
                        <button
                            type="button"
                            data-qa-theme="light"
                            aria-pressed="true"
                        >
                            Light
                        </button>
                        <button
                            type="button"
                            data-qa-theme="dark"
                            aria-pressed="false"
                        >
                            Dark
                        </button>
                    </div>

                    <button
                        type="button"
                        class="qa-baixar-html"
                        data-qa-baixar
                        title="Cópia do report com a classificação, só leitura"
                    >
                        Baixar HTML
                    </button>
                </div>
            </header>

            {contexto_html}

            <section
                class="qa-execution-alert {status_class}"
                role="status"
            >
                <div class="qa-execution-alert-icon">
                    <span></span>
                </div>

                <div class="qa-execution-alert-content">
                    <span class="qa-execution-alert-label">
                        Resumo executivo
                    </span>

                    <strong>
                        {_safe_text(summary)}
                    </strong>
                </div>
            </section>

            <section class="qa-kpi-grid">
                {kpi_cards}
            </section>

            {ressalvas_html}


            {flows_html}

            {demorados_html}

            <footer class="qa-footer">
                <div class="qa-footer-brand">
                    <strong>iFRACTAL</strong>
                    <span>TECNOLOGIA PARA SER HUMANO</span>
                </div>

                <span class="qa-footer-description">
                    Relatório gerado automaticamente
                </span>
            </footer>
        </div>
    """
