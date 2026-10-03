import pytest


@pytest.mark.ct("CT008")
# === Registro de ponto: confirmação ===
@pytest.mark.smoke
def test_registro_ponto_confirmar(home_para_marcacao, marcacoes_registradas):
    """
    Valida o registro de ponto com confirmação.

    Fronteira:
    Home -> abrir confirmação -> confirmar -> validar sucesso
    -> validar hora do registro -> retorno à Home.

    Pré-condições externas:
    - Localização concedida no emulador/device Android.
    - Câmera concedida no emulador/device Android.
    - Celular ativado via API (persistido do primeiro acesso).
    """
    home_page = home_para_marcacao

    home_page.abrir_confirmacao_registro_ponto()
    home_page.confirmar_registro_ponto()

    assert home_page.validar_ponto_registrado_com_sucesso(), (
        "A mensagem 'Ponto registrado com sucesso' "
        "não foi exibida após confirmar a marcação."
    )

    # Lida antes de a tela de sucesso voltar sozinha para a Home: a aba
    # STATUS (CT010) confere esta marcação.
    marcacoes_registradas.append(
        f"{home_page.obter_data_hora_registro():%H:%M}"
    )

    assert home_page.validar_hora_registro_recente(), (
        "A hora exibida no registro do ponto não está "
        "próxima do horário atual da execução."
    )

    home_page.aguardar_retorno_home()

    assert home_page.validar_home(), (
        "A Home não foi restabelecida após o registro da marcação."
    )

    # Conferir a marcação nova na faixa do dia (PainelPontoPage.
    # aguardar_marcacao) fica para quando o app atualizar a árvore de
    # acessibilidade da faixa: hoje ela não inclui marcações novas (ver
    # ONDE_PAREI.md, "Para levar ao time de dev").


@pytest.mark.ct("CT009")
# === Registro de ponto: cancelamento ===
@pytest.mark.regression
def test_registro_ponto_cancelar(home_para_marcacao):
    """
    Valida o cancelamento de uma tentativa de registro.

    Fronteira:
    Home -> abrir confirmação -> cancelar -> retorno à Home.

    Pré-condições externas:
    - Localização concedida no emulador/device Android.
    - Câmera concedida no emulador/device Android.
    - Celular ativado via API (persistido do primeiro acesso).
    """
    home_page = home_para_marcacao

    home_page.abrir_confirmacao_registro_ponto()
    home_page.cancelar_registro_ponto()
    home_page.aguardar_retorno_home()

    assert home_page.validar_home(), (
        "A Home não foi restabelecida após cancelar a tentativa de marcação."
    )
