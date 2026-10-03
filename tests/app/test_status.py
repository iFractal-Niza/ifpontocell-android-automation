"""
Aba STATUS: a marcação feita pelo registro de ponto e o comprovante.

Roda logo depois do registro de ponto, na mesma sessão. A aba lista só
as marcações deste app desde o primeiro acesso, e a mais recente é a do
registro de ponto. Sempre "Sincronizado": o teste não registra
offline.
"""

import re
from datetime import date

import pytest

from pages.compartilhado.visualizador_documento_page import (
    VisualizadorDocumentoPage,
)
from pages.status.status_page import StatusPage
from utils.status import campos_do_comprovante
from utils.texto import normalizar_texto

TITULO_COMPROVANTE = "Comprovante de Registro de Ponto do Trabalhador"
_HORA = re.compile(r"^\d{2}:\d{2}$")


@pytest.mark.ct("CT010")
@pytest.mark.regression
def test_status_marcacao_e_comprovante(
    home_autenticada,
    marcacoes_registradas,
    monitor_nome_pessoa,
):
    """
    Valida, na aba STATUS, a marcação mais recente (a do registro de
    ponto: hoje, na hora registrada, sincronizada) e o comprovante dela,
    que é salvo no aparelho.

    Fronteira: Home -> STATUS -> marcação mais recente (data, hora,
    Sincronizado, 100%) -> COMPROVANTE -> título, colaborador, dia e hora
    -> SALVAR -> "Arquivo salvo com sucesso." -> voltar -> PONTO (Home).
    """
    pagina = StatusPage(home_autenticada.driver)
    pagina.acessar()

    marcacao = pagina.marcacao_mais_recente()

    if marcacao is None:
        pagina.voltar_para_ponto()
        pytest.skip(
            "Nenhuma marcação na aba STATUS: ela só lista as feitas por "
            "este app desde o primeiro acesso (rode junto com o registro "
            "de ponto: make registro-ponto ou make run)."
        )

    hoje = date.today()

    assert marcacao.dia == hoje, (
        f"A marcação mais recente é de {marcacao.dia:%d/%m/%Y}, não de hoje."
    )

    textos = pagina.textos(marcacao)
    hora = next((t for t in textos if _HORA.match(t)), None)

    assert f"{hoje:%d/%m/%Y}" in textos, (
        f"A marcação não mostra a data de hoje: {textos}."
    )

    if marcacoes_registradas:
        assert hora == marcacoes_registradas[-1], (
            f"A marcação mais recente é das {hora}; o registro de ponto "
            f"marcou às {marcacoes_registradas[-1]}."
        )
    else:
        assert hora, f"A marcação não mostra a hora: {textos}."

    status = pagina.aguardar_sincronizada(
        marcacao, timeout=pagina.LONG_TIMEOUT
    )

    assert status == pagina.SINCRONIZADO, (
        f"Status da marcação: {status!r}, esperado {pagina.SINCRONIZADO!r}."
    )

    assert pagina.progresso(marcacao) == "100%", (
        f"Progresso do envio: {pagina.progresso(marcacao)!r}, esperado '100%'."
    )

    pagina.abrir_comprovante(marcacao)
    comprovante = VisualizadorDocumentoPage(pagina.driver)

    assert comprovante.esta_aberto(timeout=comprovante.LONG_TIMEOUT), (
        "O comprovante não abriu ao tocar em COMPROVANTE."
    )

    texto = comprovante.texto()
    campos = campos_do_comprovante(texto)

    assert normalizar_texto(texto).startswith(TITULO_COMPROVANTE), (
        f"O documento não é o comprovante: {texto[:80]!r}."
    )

    esperados = {
        "DIA": f"{hoje:%d/%m/%Y}",
        "HORA": hora,
        "COLABORADOR": normalizar_texto(monitor_nome_pessoa),
    }
    divergentes = {
        campo: (campos.get(campo), esperado)
        for campo, esperado in esperados.items()
        if normalizar_texto(campos.get(campo, "")) != esperado
    }
    assert not divergentes, (
        "Comprovante diferente da marcação (exibido, esperado): "
        f"{divergentes}."
    )

    comprovante.salvar()
    comprovante.voltar()

    assert pagina.esta_aberta(timeout=pagina.LONG_TIMEOUT), (
        "A aba STATUS não foi exibida ao voltar do comprovante."
    )

    pagina.voltar_para_ponto()
