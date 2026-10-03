"""
Marcações da aba STATUS e o comprovante (utils.status).
"""

from datetime import date

from utils.status import (
    MarcacaoStatus,
    campos_do_comprovante,
    ler_id_marcacao,
    mais_recente,
)


def test_le_dia_e_codigo_do_id():
    assert ler_id_marcacao("status.cellMarcacao_2026-10-01_1") == (
        MarcacaoStatus(
            "status.cellMarcacao_2026-10-01_1", date(2026, 10, 1), 1
        )
    )


def test_id_fora_do_formato():
    assert ler_id_marcacao("status.tblMarcacoes") is None
    assert ler_id_marcacao("") is None


def test_mais_recente_pelo_dia_e_pelo_codigo():
    ontem = ler_id_marcacao("status.cellMarcacao_2026-09-30_9")
    primeira = ler_id_marcacao("status.cellMarcacao_2026-10-01_2")
    segunda = ler_id_marcacao("status.cellMarcacao_2026-10-01_10")

    assert mais_recente([primeira, ontem, segunda]) == segunda
    assert mais_recente([]) is None


def test_campos_do_comprovante():
    # Texto real do comprovante (TextView), com o hash encurtado.
    texto = (
        "Comprovante de Registro de Ponto do Trabalhador\n"
        "CNPJ/CPF: 669.682.920-25\n"
        "COLABORADOR: TesterN95\n"
        "HORA: 16:50\n"
        "DIA: 01/10/2026\n"
        "NSR: 16834\n"
        "HASH: ebcab6cd\n"
        "Powered by TCPDF (www.tcpdf.org)"
    )

    campos = campos_do_comprovante(texto)

    assert campos["HORA"] == "16:50"
    assert campos["DIA"] == "01/10/2026"
    assert campos["COLABORADOR"] == "TesterN95"
    assert "Comprovante de Registro de Ponto do Trabalhador" not in campos
