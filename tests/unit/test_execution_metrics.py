"""
Métricas do dashboard (observability.execution_metrics): fluxo por
arquivo, título legível, motivo do pulo e lista de ressalvas.
"""

from types import SimpleNamespace

import pytest

from observability import execution_metrics
from observability.execution_metrics import (
    extract_fluxo,
    extract_skip_reason,
    extract_titulo,
)


@pytest.fixture(autouse=True)
def metricas_isoladas(monkeypatch):
    monkeypatch.setattr(
        execution_metrics,
        "logger",
        SimpleNamespace(
            debug=lambda *a, **k: None,
        ),
    )
    execution_metrics.reset_dashboard_stats()
    yield
    execution_metrics.reset_dashboard_stats()


@pytest.mark.parametrize(
    ("nodeid", "fluxo"),
    [
        ("tests/app/test_login.py::test_senha_invalida", "login"),
        ("tests/app/test_holerite.py::test_x", "holerite"),
        ("tests/app/test_ass_espelho.py::test_x", "assinatura do espelho"),
        ("tests/app/test_registro_sem_foto.py::test_x", "registro de ponto"),
        # O nome do teste não decide: "home" aqui é da jornada e2e.
        (
            "tests/app/test_e2e.py::test_primeiro_acesso_home_e_lembrete",
            "jornada e2e",
        ),
        ("tests/api/test_celular_api.py::test_x", "api"),
        ("tests/unit/test_periodo.py::test_x", "unitários"),
        # Tela nova, fora do mapa: ganha a própria linha.
        ("tests/app/test_espelho_ponto.py::test_x", "espelho ponto"),
        ("", "outros"),
    ],
)
def test_fluxo_vem_do_arquivo(nodeid, fluxo):
    assert extract_fluxo(nodeid) == fluxo


def test_titulo_e_o_primeiro_paragrafo_do_docstring():
    docstring = """
    Abre o holerite da segunda competência mais recente,
    sem salvar.

    Fronteira: Home -> menu -> Holerite.
    """

    assert extract_titulo("tests/app/test_h.py::test_x", docstring) == (
        "Abre o holerite da segunda competência mais recente, sem salvar"
    )


def test_titulo_sem_docstring_usa_o_nome_da_funcao():
    assert (
        extract_titulo("tests/app/test_login.py::test_senha_invalida")
        == "Senha invalida"
    )


def test_titulo_mantem_o_parametro():
    assert (
        extract_titulo("t.py::test_status[caso-1]", "Confere o status.")
        == "Confere o status [caso-1]"
    )


def test_motivo_do_skip_sem_o_prefixo_do_pytest():
    report = SimpleNamespace(longrepr=("arq.py", 10, "Skipped: sem massa"))

    assert extract_skip_reason(report) == "sem massa"


def test_motivo_de_falha_esperada():
    report = SimpleNamespace(wasxfail="bug 123", longrepr=None)

    assert extract_skip_reason(report) == "Falha esperada: bug 123"


def test_motivo_ausente():
    assert extract_skip_reason(SimpleNamespace(longrepr=None)) == (
        "Motivo não informado."
    )


def test_pulado_entra_nas_ressalvas_com_fluxo_titulo_e_motivo():
    nodeid = "tests/app/test_informe_rendimentos.py::test_segundo"

    execution_metrics.update_dashboard_stats(
        nodeid,
        "skipped",
        motivo="um documento só",
        titulo="Abre o segundo informe",
    )

    assert execution_metrics.DASHBOARD_STATS["pulados"] == [
        {
            "nodeid": nodeid,
            "titulo": "Abre o segundo informe",
            "fluxo": "informe de rendimentos",
            "motivo": "um documento só",
        }
    ]


def test_aprovado_nao_entra_nas_ressalvas():
    execution_metrics.update_dashboard_stats(
        "tests/app/test_login.py::t", "passed"
    )

    assert execution_metrics.DASHBOARD_STATS["pulados"] == []


def test_execucao_so_de_api_nao_usa_app():
    execution_metrics.update_dashboard_stats(
        "tests/api/test_a.py::t", "passed"
    )

    assert execution_metrics.execucao_usa_app() is False


def test_execucao_com_teste_de_tela_usa_app():
    execution_metrics.update_dashboard_stats(
        "tests/api/test_a.py::t", "passed"
    )
    execution_metrics.update_dashboard_stats(
        "tests/app/test_login.py::t", "passed"
    )

    assert execution_metrics.execucao_usa_app() is True


def test_status_por_teste_fica_com_o_mais_grave():
    # Passou na chamada e quebrou no teardown: fica "error".
    nodeid = "tests/app/test_login.py::test_x"

    execution_metrics.update_dashboard_stats(
        nodeid, "passed", titulo="Login X"
    )
    execution_metrics.update_dashboard_stats(nodeid, "error")

    assert execution_metrics.DASHBOARD_STATS["por_teste"][nodeid] == {
        "status": "error",
        "titulo": "Login X",
    }


def test_duracao_soma_as_fases_do_teste_e_do_fluxo():
    nodeid = "tests/app/test_holerite.py::test_holerite"

    execution_metrics.registrar_duracao(nodeid, 2.5, titulo="CT014 · A")
    execution_metrics.registrar_duracao(nodeid, 10.0)
    execution_metrics.registrar_duracao(nodeid, 0.5)

    stats = execution_metrics.DASHBOARD_STATS
    assert stats["duracoes"][nodeid] == {
        "titulo": "CT014 · A",
        "fluxo": "holerite",
        "segundos": 13.0,
    }
    assert stats["por_fluxo"]["holerite"]["duration"] == 13.0


def test_falha_do_smoke_conta_como_critica_uma_vez_por_teste():
    nodeid = "tests/app/test_login.py::test_credenciais_validas"

    execution_metrics.update_dashboard_stats(nodeid, "failed", smoke=True)
    execution_metrics.update_dashboard_stats(nodeid, "error", smoke=True)
    execution_metrics.update_dashboard_stats(
        "tests/app/test_privacidade.py::test_x", "failed"
    )

    stats = execution_metrics.DASHBOARD_STATS
    assert stats["criticas"] == 1
    assert stats["por_fluxo"]["login"]["critico"] == 1
    assert stats["por_fluxo"]["privacidade"]["critico"] == 0
