from types import SimpleNamespace

from core.privacy_services import CAMERA, LOCATION
from tests.support.profile_resolver import resolver_profile


def _request(exibir_lembrete: bool = False):
    """
    Imita o request da fixture. exibir_lembrete: teste com
    @exibir_lembrete.
    """
    markers = {}

    if exibir_lembrete:
        markers["exibir_lembrete"] = SimpleNamespace(args=())

    return SimpleNamespace(
        node=SimpleNamespace(get_closest_marker=markers.get),
        fixturename="app_session_teste",
        scope="function",
    )


def test_perfil_repassa_cold_start_e_permissoes():
    perfil = resolver_profile(
        _request(),
        cold_start=True,
        permissions=(LOCATION, CAMERA),
    )

    assert perfil.cold_start is True
    assert perfil.permissions == frozenset({LOCATION, CAMERA})


def test_sessao_morna():
    perfil = resolver_profile(_request(), cold_start=False, manter_estado=True)

    assert perfil.manter_estado is True


def test_exibir_lembrete_nao_muda_o_perfil():
    # No Android não há launch argument para suprimir o lembrete.
    com = resolver_profile(_request(exibir_lembrete=True), cold_start=True)
    sem = resolver_profile(_request(), cold_start=True)

    assert com == sem
