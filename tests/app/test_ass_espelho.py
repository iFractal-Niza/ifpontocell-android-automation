"""
Assinatura do Espelho (menu ASSINATURA DO ESPELHO). Não confundir com o
menu Espelho de Ponto, que é outra tela.

Massa de teste esperada: dois espelhos pendentes. Os testes assinam, ou
seja, consomem massa de forma irreversível (só volta excluindo e
refazendo o fechamento no ifPonto web), e só rodam com --consumir-massa
(make run e make ass-espelho). Cada um escolhe o seu espelho pela data — o
mais recente e o segundo mais recente.

O CT021 (DEPOIS no aviso de espelho pendente) roda primeiro: precisa
de um espelho pendente e não assina nada. CT021 e CT022 partem do aviso
que aparece ao abrir o app (relançar -> PIN); a lista só é aberta pelo
menu antes disso se o aviso não aparecer. O aviso só considera os
espelhos dos dois últimos meses: se nenhum deles estiver pendente, CT022
e CT023 (que assinam justamente esses dois) pulam na hora, sem relançar
o app; um pendente mais antigo não gera aviso e não conta.

Encadeados: o CT022 termina na lista da Assinatura do Espelho, o CT023
continua dali e também termina nela, e o CT024 (salvar) continua dali
— sem voltar à Home e entrar pelo menu entre eles. Rodando sozinhos (ex.:
--ct CT024), CT023 e CT024 entram pelo menu.

Salvar é um teste à parte (CT024) porque o botão SALVAR depende da
permissão do usuário no ifPonto: sem ela, o teste é pulado, e a
assinatura não reprova por causa disso.
"""

import pytest

from observability.evidencias import capturar_evidencia
from pages.ass_espelho.assinatura_espelho_page import AssinaturaEspelhoPage
from pages.autenticacao.unlock_page import UnlockPage
from pages.home_page import HomePage
from utils.ass_espelho import (
    EspelhoAssinatura,
    mais_recente,
    pendentes_com_aviso,
    segundo_mais_recente,
)

INSTRUCAO_REPOR = "Para repor, exclua e refaça o fechamento no ifPonto web."
MOTIVO_SEM_PENDENTES = (
    "Nenhum espelho pendente entre os dois mais recentes (os únicos que "
    "geram o aviso). "
)


@pytest.fixture(scope="module")
def massa_espelho() -> dict:
    """
    O que um teste do módulo já descobriu sobre a massa.

    'sem_pendentes': a lista foi conferida e nenhum dos dois espelhos
    mais recentes está pendente (CT021 ou CT022 pularam por isso). Nada
    assina entre um teste e outro, então o CT022 e o CT023 pulam na hora,
    sem relançar o app só para descobrir o mesmo. Rodando sozinhos,
    conferem como sempre.
    """
    return {"sem_pendentes": False}


def _pular_se_ja_sem_pendentes(massa_espelho: dict) -> None:
    if massa_espelho["sem_pendentes"]:
        pytest.skip(
            MOTIVO_SEM_PENDENTES
            + "(conferido na lista por um teste anterior) "
            + INSTRUCAO_REPOR
        )


def _abrir_ou_pular(home) -> AssinaturaEspelhoPage:
    """
    Abre a Assinatura do Espelho pelo menu; sem nenhum fechamento ("Sem
    assinatura"), volta à Home e pula — é massa de teste, não defeito.
    """
    pagina = AssinaturaEspelhoPage(home.driver)

    if not pagina.acessar():
        pagina.voltar_para_home()
        pytest.skip(
            "O usuário não tem nenhum espelho fechado ('Sem assinatura')."
        )

    return pagina


def _lista_aberta_ou_pelo_menu(request, sessao) -> AssinaturaEspelhoPage:
    """
    A lista da Assinatura do Espelho: a que já está na tela (deixada pelo
    CT022) ou aberta pelo menu a partir da Home.

    A home_autenticada só é pedida quando a lista não está na tela: ela
    relança o app se não estiver na Home, o que desfaria o encadeamento.
    """
    pagina = AssinaturaEspelhoPage(sessao.driver)

    if pagina.esta_na_tela(timeout=pagina.SHORT_TIMEOUT):
        return pagina

    return _abrir_ou_pular(request.getfixturevalue("home_autenticada"))


def _pendente_ou_pular(
    pagina: AssinaturaEspelhoPage,
    espelho: EspelhoAssinatura | None,
    descricao: str,
) -> EspelhoAssinatura:
    """
    Garante que o espelho escolhido ainda está pendente; senão volta à
    Home e pula (massa já consumida).
    """
    if espelho is None or espelho.assinado:
        capturar_evidencia(
            pagina.driver,
            f"Espelho {descricao} já assinado (massa consumida)",
        )
        pagina.voltar_para_home()
        pytest.skip(
            f"O espelho {descricao} já está assinado (ou não existe). "
            + INSTRUCAO_REPOR
        )

    return espelho


def _relancar_ate_aviso_pendente(
    sessao, app_pin, massa_espelho: dict
) -> HomePage:
    """
    Relança o app e desbloqueia sem passar pela limpeza de popups (que
    adiaria o aviso com DEPOIS), esperando o aviso de espelho pendente.

    O próprio aviso diz se há espelho pendente: a lista só é aberta pelo
    menu quando ele não aparece, para separar defeito (um dos dois mais
    recentes pendente e o aviso não veio: reprova) de falta de massa
    (nenhum deles pendente: pula). Pendente mais antigo não gera aviso.
    """
    sessao.relaunch()
    UnlockPage(sessao.driver).desbloquear_com_pin(app_pin)

    home = HomePage(sessao.driver)

    if home.popup_espelho_pendente_esta_visivel(timeout=home.LONG_TIMEOUT):
        return home

    home.tratar_popups_home_se_existirem()
    pagina = _abrir_ou_pular(home)

    pendentes = pendentes_com_aviso(pagina.espelhos())

    if pendentes:
        raise AssertionError(
            "Há espelho pendente entre os dois mais recentes "
            f"({', '.join(e.competencia for e in pendentes)}), mas o aviso "
            "de assinatura não foi exibido ao abrir o app."
        )

    capturar_evidencia(pagina.driver, "Assinatura do Espelho sem pendentes")
    pagina.voltar_para_home()
    massa_espelho["sem_pendentes"] = True
    pytest.skip(MOTIVO_SEM_PENDENTES + INSTRUCAO_REPOR)


def _assinar(
    pagina: AssinaturaEspelhoPage,
    espelho,
    impressao,
    tocar_sem_aceite: int = 0,
) -> None:
    """
    Da Impressão até o status ASSINADO na lista.

    tocar_sem_aceite: quantas vezes tocar em ASSINAR ESPELHO antes de
    marcar o aceite, conferindo que o botão está desabilitado e que nada
    acontece (não assina, não sai da tela, não marca o aceite).
    """
    assinar = impressao.abrir_assinatura()

    assert assinar.periodo_do_aceite() == espelho.periodo, (
        "O aceite não se refere ao período do espelho escolhido "
        f"({espelho.periodo})."
    )

    if tocar_sem_aceite:
        assert not assinar.botao_assinar_habilitado(), (
            "ASSINAR ESPELHO está habilitado sem o aceite marcado."
        )

    for toque in range(1, tocar_sem_aceite + 1):
        assinar.tocar_assinar()

        assert not assinar.assinatura_confirmada(
            timeout=assinar.SHORT_TIMEOUT
        ), (
            f"O espelho foi assinado sem o aceite (toque {toque} em "
            "ASSINAR ESPELHO)."
        )

        assert assinar.esta_aberta(timeout=assinar.SHORT_TIMEOUT), (
            f"O toque {toque} em ASSINAR ESPELHO sem o aceite saiu da tela "
            "de assinatura."
        )

        assert not assinar.aceite_marcado(), (
            f"O toque {toque} em ASSINAR ESPELHO marcou o aceite."
        )

    assinar.marcar_aceite()

    assert assinar.botao_assinar_habilitado(), (
        "ASSINAR ESPELHO não foi habilitado após marcar o aceite."
    )

    assinar.assinar()

    assert pagina.esta_na_tela(timeout=pagina.LONG_TIMEOUT), (
        "A lista da Assinatura do Espelho não foi exibida após confirmar "
        "a assinatura."
    )

    assert pagina.esta_assinado(espelho.competencia), (
        f"O espelho de {espelho.competencia} não aparece como ASSINADO "
        "após a assinatura."
    )


@pytest.mark.ct("CT021")
# === Aviso de espelho pendente (não consome massa) ===
@pytest.mark.regression
def test_ass_espelho_aviso_pendente_depois_nao_redireciona(
    home_autenticada,
    app_session_e2e_registro_ponto,
    app_pin,
    massa_espelho,
):
    """
    Valida que DEPOIS no aviso de espelho pendente fecha o aviso e mantém
    o app na Home, sem abrir a Assinatura do Espelho.

    Roda antes das assinaturas (CT022 e CT023): precisa de um espelho
    pendente e não assina nada.

    Fronteira: relançar -> PIN -> aviso "Seu espelho de ponto esta
    disponível para assinatura." -> DEPOIS -> Home.
    """
    home = _relancar_ate_aviso_pendente(
        app_session_e2e_registro_ponto, app_pin, massa_espelho
    )

    assert home.tratar_popup_espelho_pendente_se_existir(), (
        "Não foi possível tocar em DEPOIS no aviso de espelho pendente."
    )

    assert not home.popup_espelho_pendente_esta_visivel(
        timeout=home.SHORT_TIMEOUT,
    ), "O aviso de espelho pendente continuou na tela após DEPOIS."

    assert home.esta_na_home(timeout=home.LONG_TIMEOUT), (
        "O app não ficou na Home após DEPOIS no aviso de espelho pendente."
    )

    pagina = AssinaturaEspelhoPage(home.driver)

    assert not pagina.esta_na_tela(timeout=pagina.SHORT_TIMEOUT), (
        "DEPOIS no aviso de espelho pendente abriu a Assinatura do Espelho."
    )


@pytest.mark.ct("CT022")
# === Assinaturas (consomem massa) ===
@pytest.mark.smoke
@pytest.mark.consome_massa
def test_ass_espelho_redirecionamento_e_assinar_mais_recente(
    request,
    app_session_e2e_registro_ponto,
    app_pin,
    massa_espelho,
):
    """
    Valida o acesso pelo aviso de espelho pendente e a assinatura do
    espelho mais recente.

    Pelo aviso de espelho pendente ao abrir o app (ASSINAR), chega à
    Assinatura do Espelho; no espelho mais recente: totais do período,
    Impressão do mesmo mês e assinatura.

    Fronteira: relançar -> PIN -> aviso "Seu espelho de ponto esta
    disponível para assinatura." -> ASSINAR -> Assinatura do Espelho ->
    expandir -> visualizar -> Impressão -> ASSINAR ESPELHO -> aceite ->
    sucesso -> lista com ASSINADO (fica nela para o CT023).
    """
    _pular_se_ja_sem_pendentes(massa_espelho)

    # Só aqui: a home_autenticada relançaria o app à toa se o teste pula.
    request.getfixturevalue("home_autenticada")

    # O aviso aparece ao abrir o app.
    home = _relancar_ate_aviso_pendente(
        app_session_e2e_registro_ponto, app_pin, massa_espelho
    )

    home.aceitar_popup_espelho_pendente()

    pagina = AssinaturaEspelhoPage(home.driver)

    assert pagina.esta_na_tela(timeout=pagina.LONG_TIMEOUT), (
        "O ASSINAR do aviso de espelho pendente não levou à Assinatura "
        "do Espelho."
    )

    # O espelho é escolhido na lista aberta pelo aviso.
    espelho = _pendente_ou_pular(
        pagina,
        mais_recente(pagina.espelhos()),
        "mais recente",
    )

    pagina.expandir(espelho)
    impressao = pagina.visualizar(espelho)

    # Termina na lista com ASSINADO (conferido em _assinar): o CT023
    # continua daqui.
    _assinar(pagina, espelho, impressao)


@pytest.mark.ct("CT023")
@pytest.mark.smoke
@pytest.mark.consome_massa
def test_ass_espelho_assinar_segundo_mais_recente(
    request,
    app_session_e2e_registro_ponto,
    massa_espelho,
):
    """
    Valida a assinatura do segundo espelho mais recente pelo menu, que
    só é aceita com o termo de aceite marcado.

    Continua da lista deixada pelo CT022; rodando sozinho, entra pelo
    menu (o aviso de espelho pendente é adiado com DEPOIS pela fixture:
    o redirecionamento é coberto só pelo CT022).

    Antes do aceite, toca duas vezes em ASSINAR ESPELHO e confere que
    nada acontece: o botão só assina com o aceite marcado.

    Fronteira: lista da Assinatura do Espelho (ou Home -> menu) -> expandir ->
    visualizar -> Impressão -> ASSINAR ESPELHO -> 2 toques sem aceite
    (nada acontece) -> aceite -> sucesso -> lista com ASSINADO (fica
    nela para o CT024).
    """
    _pular_se_ja_sem_pendentes(massa_espelho)

    pagina = _lista_aberta_ou_pelo_menu(
        request,
        app_session_e2e_registro_ponto,
    )
    espelhos = pagina.espelhos()

    if len(espelhos) < 2:
        capturar_evidencia(
            pagina.driver,
            f"Assinatura do Espelho com {len(espelhos)} espelho(s)",
        )
        pagina.voltar_para_home()
        pytest.skip(
            f"O usuário tem {len(espelhos)} espelho(s); o cenário precisa "
            "de dois. " + INSTRUCAO_REPOR
        )

    espelho = _pendente_ou_pular(
        pagina,
        segundo_mais_recente(espelhos),
        "segundo mais recente",
    )

    pagina.expandir(espelho)
    impressao = pagina.visualizar(espelho)

    _assinar(pagina, espelho, impressao, tocar_sem_aceite=2)


@pytest.mark.ct("CT024")
@pytest.mark.regression
def test_ass_espelho_salvar_impressao(request, app_session_e2e_registro_ponto):
    """
    Valida o salvamento da Impressão do espelho mais recente.

    O botão SALVAR depende da permissão do usuário no ifPonto: sem ele,
    o teste é pulado (configuração, não defeito). Não assina nada; rodando
    depois das assinaturas, salva o espelho já assinado e confere que a
    Impressão mostra ASSINADO.

    Fronteira: lista da Assinatura do Espelho (ou Home -> menu) ->
    expandir -> visualizar -> Impressão -> SALVAR -> "Arquivo salvo com
    sucesso" -> lista -> Home.
    """
    pagina = _lista_aberta_ou_pelo_menu(
        request,
        app_session_e2e_registro_ponto,
    )
    espelho = mais_recente(pagina.espelhos())

    if espelho is None:
        capturar_evidencia(pagina.driver, "Assinatura do Espelho sem espelhos")
        pagina.voltar_para_home()
        pytest.skip(
            "O usuário não tem espelho para salvar. " + INSTRUCAO_REPOR
        )

    pagina.expandir(espelho)
    impressao = pagina.visualizar(espelho)

    if not impressao.salvar_disponivel():
        capturar_evidencia(pagina.driver, "Impressão sem o botão SALVAR")
        impressao.voltar()
        pagina.voltar_para_home()
        pytest.skip(
            "O botão SALVAR não é exibido: o usuário não tem permissão de "
            "salvar o espelho no ifPonto."
        )

    if espelho.assinado:
        assert impressao.assinado(), (
            f"O espelho de {espelho.competencia} está ASSINADO na lista, "
            "mas a Impressão não mostra ASSINADO."
        )

    impressao.salvar()
    impressao.voltar()

    assert pagina.esta_na_tela(timeout=pagina.LONG_TIMEOUT), (
        "A lista da Assinatura do Espelho não foi exibida ao voltar da "
        "Impressão."
    )

    pagina.voltar_para_home()
