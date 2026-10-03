"""
Registro de ponto com geo delimitação.

Massa de teste: uma geo delimitação cadastrada para o usuário, e as
coordenadas de um ponto dentro e de um fora dela no env.<device>.yaml
(ANDROID_GEO_*). Sem elas, os testes são pulados. Cada teste troca a
localização simulada do aparelho; a fixture geo_delimitacao restaura a
padrão.
"""

import pytest

from core.localizacao import definir_localizacao


@pytest.mark.ct("CT013")
@pytest.mark.regression
def test_registro_fora_da_geo_avisa_e_permite_cancelar(
    home_para_marcacao,
    geo_delimitacao,
):
    """
    Valida o aviso ao registrar fora da geo delimitação e o retorno à
    Home ao responder NÃO, sem registrar o ponto.

    Fronteira: localização fora da área -> Home -> Registrar ->
    confirmação -> SIM -> aviso "Você está fora da geo localização
    delimitada..." -> NÃO -> Home.
    """
    home_page = home_para_marcacao

    definir_localizacao(home_page.driver, geo_delimitacao.fora)

    home_page.abrir_confirmacao_registro_ponto()
    home_page.confirmar_registro_ponto()
    home_page.validar_aviso_fora_da_geo()

    home_page.cancelar_registro_fora_da_geo()

    assert home_page.esta_na_home(timeout=home_page.DEFAULT_TIMEOUT), (
        "A Home não foi exibida após responder NÃO ao aviso de fora da geo."
    )


@pytest.mark.ct("CT014")
@pytest.mark.regression
def test_registro_fora_da_geo_confirmado(home_para_marcacao, geo_delimitacao):
    """
    Valida que, fora da geo delimitação, responder SIM ao aviso registra
    o ponto normalmente.

    Fronteira: localização fora da área -> Home -> Registrar ->
    confirmação -> SIM -> aviso de fora da geo -> SIM -> sucesso -> Home.
    """
    home_page = home_para_marcacao

    definir_localizacao(home_page.driver, geo_delimitacao.fora)

    home_page.abrir_confirmacao_registro_ponto()
    home_page.confirmar_registro_ponto()
    home_page.validar_aviso_fora_da_geo()
    home_page.confirmar_registro_fora_da_geo()

    assert home_page.validar_ponto_registrado_com_sucesso(), (
        "A mensagem 'Ponto registrado com sucesso' não foi exibida após "
        "confirmar o registro fora da geo delimitação."
    )

    assert home_page.validar_hora_registro_recente(), (
        "A hora exibida no registro do ponto não está próxima do "
        "horário atual da execução."
    )

    home_page.aguardar_retorno_home()

    assert home_page.validar_home(), (
        "A Home não foi restabelecida após o registro fora da geo."
    )


@pytest.mark.ct("CT015")
@pytest.mark.smoke
def test_registro_dentro_da_geo(home_para_marcacao, geo_delimitacao):
    """
    Valida o registro de ponto com a localização dentro da geo
    delimitação, sem aviso.

    Fronteira: localização dentro da área -> Home -> Registrar ->
    confirmação -> SIM -> sucesso -> Home.
    """
    home_page = home_para_marcacao

    definir_localizacao(home_page.driver, geo_delimitacao.dentro)

    home_page.abrir_confirmacao_registro_ponto()
    home_page.confirmar_registro_ponto()

    assert home_page.validar_ponto_registrado_com_sucesso(), (
        "A mensagem 'Ponto registrado com sucesso' não foi exibida após "
        "confirmar a marcação dentro da geo delimitação."
    )

    assert home_page.validar_hora_registro_recente(), (
        "A hora exibida no registro do ponto não está próxima do "
        "horário atual da execução."
    )

    home_page.aguardar_retorno_home()

    assert home_page.validar_home(), (
        "A Home não foi restabelecida após o registro da marcação."
    )
