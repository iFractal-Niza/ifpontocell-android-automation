"""
Histórico das execuções (observability.historico): falhas novas,
recorrentes e testes instáveis, comparando com as execuções anteriores.
"""

from datetime import datetime

from observability import historico


def _execucao(data: str, **status) -> dict:
    return {
        "data": data,
        "testes": {
            nodeid: {"status": s, "titulo": f"Título {nodeid}"}
            for nodeid, s in status.items()
        },
    }


def test_primeira_execucao_nao_tem_anteriores():
    resumo = historico.resumir([], _execucao("hoje", a="failed"))

    assert resumo.tem_anteriores is False
    assert resumo.falhas_novas == ["Título a"]


def test_falha_nova_passava_na_anterior():
    anteriores = [_execucao("01/10", a="passed")]

    resumo = historico.resumir(anteriores, _execucao("02/10", a="failed"))

    assert resumo.falhas_novas == ["Título a"]
    assert resumo.falhas_recorrentes == []


def test_falha_recorrente_informa_desde_quando():
    anteriores = [
        _execucao("01/10", a="passed"),
        _execucao("02/10", a="failed"),
        _execucao("03/10", a="error"),
    ]

    resumo = historico.resumir(anteriores, _execucao("04/10", a="failed"))

    assert resumo.falhas_novas == []
    assert resumo.falhas_recorrentes == [
        historico.FalhaRecorrente("Título a", "02/10")
    ]


def test_compara_com_a_ultima_execucao_em_que_o_teste_rodou():
    # Execução parcial (make holerite) no meio não apaga o passado de 'a'.
    anteriores = [
        _execucao("01/10", a="failed"),
        _execucao("02/10", b="passed"),
    ]

    resumo = historico.resumir(anteriores, _execucao("03/10", a="failed"))

    assert resumo.falhas_recorrentes[0].desde == "01/10"


def test_instavel_alterna_entre_passar_e_falhar():
    anteriores = [
        _execucao("1", a="passed"),
        _execucao("2", a="failed"),
        _execucao("3", a="passed"),
    ]

    resumo = historico.resumir(anteriores, _execucao("4", a="passed"))

    assert resumo.instaveis == ["Título a"]


def test_falha_corrigida_nao_e_instavel():
    # Falhou duas vezes e passou: uma troca só, foi corrigido.
    anteriores = [_execucao("1", a="failed"), _execucao("2", a="failed")]

    resumo = historico.resumir(anteriores, _execucao("3", a="passed"))

    assert resumo.instaveis == []


def test_falha_que_quebrou_agora_nao_e_instavel():
    anteriores = [_execucao("1", a="passed"), _execucao("2", a="passed")]

    resumo = historico.resumir(anteriores, _execucao("3", a="failed"))

    assert resumo.instaveis == []
    assert resumo.falhas_novas == ["Título a"]


def test_failed_e_error_nao_contam_como_troca():
    anteriores = [_execucao("1", a="passed"), _execucao("2", a="failed")]

    resumo = historico.resumir(anteriores, _execucao("3", a="error"))

    assert resumo.instaveis == []


def test_pulado_no_meio_nao_esconde_a_alternancia():
    anteriores = [
        _execucao("1", a="passed"),
        _execucao("2", a="skipped"),
        _execucao("3", a="failed"),
    ]

    resumo = historico.resumir(anteriores, _execucao("4", a="passed"))

    assert resumo.instaveis == ["Título a"]


def test_pulado_nao_conta_como_instavel():
    anteriores = [_execucao("1", a="skipped"), _execucao("2", a="passed")]

    resumo = historico.resumir(anteriores, _execucao("3", a="passed"))

    assert resumo.instaveis == []


def test_instabilidade_antiga_sai_da_janela():
    anteriores = [_execucao("0", a="failed")] + [
        _execucao(str(n), a="passed")
        for n in range(1, historico.JANELA_INSTAVEL)
    ]

    resumo = historico.resumir(anteriores, _execucao("x", a="passed"))

    assert resumo.instaveis == []


def test_salvar_mantem_as_ultimas_execucoes(tmp_path):
    arquivo = tmp_path / "history.json"
    execucoes = [_execucao(str(n), a="passed") for n in range(40)]

    historico.salvar(execucoes, arquivo)

    salvas = historico.carregar(arquivo)
    assert len(salvas) == historico.MAX_EXECUCOES
    assert salvas[-1]["data"] == "39"


def test_arquivo_corrompido_vale_como_vazio(tmp_path):
    arquivo = tmp_path / "history.json"
    arquivo.write_text("{ quebrado", encoding="utf-8")

    assert historico.carregar(arquivo) == []


def test_montar_execucao_guarda_status_e_titulo():
    execucao = historico.montar_execucao(
        datetime(2026, 10, 1, 9, 5),
        {"t.py::a": {"status": "passed", "titulo": "A"}},
    )

    assert execucao == {
        "data": "01/10/2026 09:05",
        "testes": {"t.py::a": {"status": "passed", "titulo": "A"}},
    }
