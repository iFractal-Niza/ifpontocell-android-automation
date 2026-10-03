"""
Geo delimitação: coordenadas de dentro e de fora da área cadastrada para
o usuário de teste (massa de teste, ANDROID_GEO_* no env.<device>.yaml).

Roda no emulador e no celular (localização simulada nos dois). A
fixture entrega as coordenadas e, no fim do teste, devolve o aparelho
à localização padrão da sessão (ANDROID_LOCATION_*, ou a de dentro da geo),
mesmo se o teste falhar: os próximos testes de registro de ponto não
podem herdar a coordenada de fora da área.
"""

import pytest

from config.settings import GeoDelimitacao, Settings
from core.localizacao import definir_localizacao


@pytest.fixture
def geo_delimitacao(home_para_marcacao) -> GeoDelimitacao:
    settings = Settings.from_env()

    if settings.geo is None:
        pytest.skip(
            "Massa de geo delimitação não configurada: preencha "
            "ANDROID_GEO_DENTRO_* e ANDROID_GEO_FORA_* no "
            "env.<device>.yaml com pontos dentro e fora da área cadastrada "
            "para o usuário."
        )

    yield settings.geo

    definir_localizacao(
        home_para_marcacao.driver,
        settings.localizacao or settings.geo.dentro,
    )
