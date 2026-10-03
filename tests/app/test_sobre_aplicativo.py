"""
Sobre o aplicativo (menu do perfil -> SOBRE O APLICATIVO).

A versão não é fixa: é comparada com a do app instalado (no Android, do
device ou do APK), que muda a cada build. O STATUS ("Atualizar") não é
validado: depende de haver versão mais nova publicada.
"""

import re

import pytest

from config.settings import Settings
from observability.contexto_execucao import (
    ler_versao_curta_app,
    ler_versao_instalada,
)
from pages.sobre_aplicativo.sobre_aplicativo_page import SobreAplicativoPage
from utils.texto import normalizar_texto

DESCRICAO = (
    "O ifPonto Cell é um aplicativo para registro online e offline da "
    "jornada dos colaboradores vinculado ao sistema ifPonto. Neste "
    "aplicativo é possível também acompanhar o status das suas "
    "marcações, o espelho de ponto, receber alertas e comunicados do "
    "gestor."
)

CAMPOS = {
    "NOME": "ifPonto Cell",
    "DESENVOLVEDOR": "iFractal®",
    # PENDENTE: confirmar o texto no Android (no iOS, "iOS").
    "PLATAFORMA": "Android",
}

DADOS_DA_EMPRESA = (
    "RUA FIACÃO DA SAÚDE, 145 - SAÚDE - 04144-020, SÃO PAULO, SP",
    "TEL.: (11)5070.1799",
    "IFRACTAL DESENVOLVIMENTO DE SOFTWARE LTDA.",
    "CNPJ 04.147.622/0001-06",
    "WWW.IFRACTAL.COM.BR",
)


@pytest.mark.ct("CT025")
@pytest.mark.regression
def test_sobre_aplicativo_versao_e_textos(home_autenticada):
    """
    Valida a versão exibida (igual à do app instalado) e os textos da
    tela Sobre o aplicativo.

    Fronteira: Home -> menu do perfil -> SOBRE O APLICATIVO -> leitura
    da tela (rolando até o fim) -> Home.
    """
    pagina = SobreAplicativoPage(home_autenticada.driver)
    pagina.acessar()

    conteudo = pagina.ler_conteudo()

    assert normalizar_texto(DESCRICAO) in conteudo.textos, (
        "A descrição do app não confere com a esperada."
    )

    for rotulo, esperado in CAMPOS.items():
        assert conteudo.campos.get(rotulo) == esperado, (
            f"{rotulo}: esperado {esperado!r}, exibido "
            f"{conteudo.campos.get(rotulo)!r}."
        )

    faltando = [
        texto
        for texto in DADOS_DA_EMPRESA
        if normalizar_texto(texto) not in conteudo.textos
    ]
    assert not faltando, f"Dados da empresa não exibidos: {faltando}."

    versao_exibida = conteudo.campos.get("VERSÃO", "")
    settings = Settings.from_env()
    # No iOS, do .app local. No Android: do APK (APP_SOURCE=apk) ou do
    # app instalado no device (package, o padrão), sem o build.
    versao_instalada = (
        ler_versao_curta_app(settings.apk_path)
        if settings.app_source == "apk"
        else ler_versao_instalada(
            settings.app.package, settings.device.udid
        ).split(" ")[0]
    )

    if versao_instalada:
        assert versao_exibida == versao_instalada, (
            f"A tela mostra a versão {versao_exibida!r}, mas o app "
            f"instalado é a {versao_instalada!r}."
        )
    else:
        # Sem a versão instalada (sem aapt/adb): confere só o formato.
        assert re.fullmatch(r"\d+(\.\d+)+", versao_exibida), (
            f"Versão exibida fora do formato esperado: {versao_exibida!r}."
        )

    pagina.voltar_para_home()
