import html
from typing import Any, Mapping


# === Status da execução ===
HEALTHY_THRESHOLD = 90
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

    return (
        f"{rate:.2f}%"
        .replace(
            ".",
            ",",
        )
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
            seconds = float(
                stripped_value
            )

        except ValueError:
            return stripped_value

    else:
        seconds = _to_float(
            value
        )

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
        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


def _pluralize(
    quantity: int,
    singular: str,
    plural: str,
) -> str:
    """
    Retorna a palavra adequada para a quantidade informada.
    """
    return (
        singular
        if quantity == 1
        else plural
    )


# === Status e resumo ===
def _get_status_meta(
    success_rate: float,
    *,
    total: int,
    failed: int = 0,
    error: int = 0,
) -> tuple[str, str, str]:
    """
    Retorna classe CSS, rótulo e descrição do status.

    Prioridade:
    - Sem testes: sem execução.
    - Erro técnico: crítico.
    - Taxa abaixo de 70%: crítico.
    - Taxa abaixo de 90% ou falhas funcionais: instável.
    - Demais casos: estável.
    """
    if total == 0:
        return (
            "neutral",
            "SEM EXECUÇÃO",
            "Nenhum teste foi executado.",
        )

    if (
        error > 0
        or success_rate < UNSTABLE_THRESHOLD
    ):
        return (
            "failed",
            "CRÍTICO",
            "A execução exige análise imediata.",
        )

    if (
        failed > 0
        or success_rate < HEALTHY_THRESHOLD
    ):
        return (
            "unstable",
            "INSTÁVEL",
            "A execução possui resultados que exigem atenção.",
        )

    return (
        "healthy",
        "ESTÁVEL",
        "A execução foi concluída com estabilidade.",
    )


def _build_summary_text(
    *,
    failed: int,
    error: int,
    skipped: int,
    total: int,
) -> str:
    """
    Gera o resumo executivo da execução.
    """
    if total == 0:
        return "Nenhum teste foi executado."

    if (
        failed == 0
        and error == 0
    ):
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

        return (
            "Execução concluída sem falhas "
            "ou erros técnicos."
        )

    problems = []

    if failed:
        failed_label = _pluralize(
            failed,
            "falha funcional",
            "falhas funcionais",
        )
        problems.append(
            f"{failed} {failed_label}"
        )

    if error:
        error_label = _pluralize(
            error,
            "erro técnico",
            "erros técnicos",
        )
        problems.append(
            f"{error} {error_label}"
        )

    return (
        f"{' e '.join(problems)} "
        f"{'detectado' if len(problems) == 1 else 'detectados'}."
    )


# === Componentes do dashboard ===
def _build_kpi_card(
    *,
    css_class: str,
    label: str,
    value: Any,
    detail: str = "",
) -> str:
    """
    Monta um card compacto de indicador.
    """
    detail_html = ""

    if detail:
        detail_html = (
            "<span class='qa-kpi-detail'>"
            f"{_safe_text(detail)}"
            "</span>"
        )

    return f"""
        <div class="qa-kpi-card {css_class}">
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
    passed = _to_int(
        data.get("ok")
    )
    failed = _to_int(
        data.get("fail")
    )
    error = _to_int(
        data.get("error")
    )
    skipped = _to_int(
        data.get("skip")
    )

    total = (
        passed
        + failed
        + error
        + skipped
    )

    success_rate = (
        round(
            passed / total * 100,
            2,
        )
        if total
        else 0.0
    )

    return {
        "passed": passed,
        "failed": failed,
        "error": error,
        "skipped": skipped,
        "total": total,
        "success_rate": success_rate,
        "duration": _format_duration(
            data.get("duration")
        ),
    }


# === Qualidade por fluxo ===
def build_fluxo_html_card(
    fluxo: str,
    dados: Mapping[str, Any],
) -> str:
    """
    Monta uma linha compacta com as métricas de um fluxo.
    """
    metrics = _calculate_flow_metrics(
        dados
    )

    total = metrics["total"]
    passed = metrics["passed"]
    failed = metrics["failed"]
    error = metrics["error"]
    skipped = metrics["skipped"]
    success_rate = metrics[
        "success_rate"
    ]
    duration = metrics["duration"]

    status_class, status_label, _ = (
        _get_status_meta(
            success_rate,
            total=total,
            failed=failed,
            error=error,
        )
    )

    duration_html = ""

    if duration:
        duration_html = f"""
            <span class="qa-flow-meta-item">
                <span>Duração</span>
                <strong>{_safe_text(duration)}</strong>
            </span>
        """

    return f"""
        <article class="qa-flow-row">
            <div class="qa-flow-main">
                <div class="qa-flow-heading">
                    <span class="qa-flow-title">
                        {_safe_text(fluxo.upper())}
                    </span>

                    <span class="qa-flow-badge {status_class}">
                        {status_label}
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
    if not fluxos:
        return """
            <section class="qa-section">
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
        <section class="qa-section">
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


# === Dashboard principal ===
def build_dashboard_html(
    dashboard_stats: Mapping[str, Any],
) -> str:
    """
    Monta o dashboard principal do relatório HTML.
    """
    total = _to_int(
        dashboard_stats.get("total")
    )
    passed = _to_int(
        dashboard_stats.get("passed")
    )
    failed = _to_int(
        dashboard_stats.get("failed")
    )
    error = _to_int(
        dashboard_stats.get("error")
    )
    skipped = _to_int(
        dashboard_stats.get("skipped")
    )
    success_rate = _to_float(
        dashboard_stats.get(
            "success_rate"
        )
    )

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
    )

    summary = _build_summary_text(
        failed=failed,
        error=error,
        skipped=skipped,
        total=total,
    )

    success_detail = (
        f"{passed} de {total} aprovados"
        if total
        else "Sem resultados"
    )

    kpi_cards = "".join(
        (
            _build_kpi_card(
                css_class=(
                    f"success {status_class}"
                ),
                label="Taxa de sucesso",
                value=_format_rate(
                    success_rate
                ),
                detail=success_detail,
            ),
            _build_kpi_card(
                css_class="total",
                label="Total",
                value=total,
                detail="Testes executados",
            ),
            _build_kpi_card(
                css_class="passed",
                label="Passou",
                value=passed,
                detail="Cenários aprovados",
            ),
            _build_kpi_card(
                css_class=(
                    "failed active"
                    if failed
                    else "failed muted"
                ),
                label="Falhou",
                value=failed,
                detail="Falhas funcionais",
            ),
            _build_kpi_card(
                css_class=(
                    "error active"
                    if error
                    else "error muted"
                ),
                label="Execução",
                value=error,
                detail="Erros técnicos",
            ),
            _build_kpi_card(
                css_class=(
                    "skipped active"
                    if skipped
                    else "skipped muted"
                ),
                label="Pulados",
                value=skipped,
                detail="Testes não executados",
            ),
        )
    )

    flows_html = _build_flows_html(
        fluxos
    )

    return f"""
        <div class="qa-dashboard">
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

                <div class="qa-dashboard-status">
                    <span class="qa-status-dot {status_class}"></span>

                    <div>
                        <span class="qa-status {status_class}">
                            {status_label}
                        </span>

                        <small>
                            {_safe_text(status_description)}
                        </small>
                    </div>
                </div>
            </header>

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

                <div class="qa-execution-alert-rate">
                    <span>Resultado</span>
                    <strong>
                        {_format_rate(success_rate)}
                    </strong>
                </div>
            </section>

            <section class="qa-kpi-grid">
                {kpi_cards}
            </section>

            {flows_html}

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