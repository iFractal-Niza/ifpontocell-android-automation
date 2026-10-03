import pytest

from core.launch_profile import LaunchProfile
from core.privacy_services import CAMERA, LOCATION


def test_com_permissoes_retorna_novo_perfil():
    original = LaunchProfile()
    novo = original.com_permissoes(LOCATION)

    assert original.permissions == frozenset()
    assert novo.permissions == frozenset({LOCATION})


def test_com_permissoes_acumula():
    perfil = LaunchProfile().com_permissoes(LOCATION).com_permissoes(CAMERA)

    assert perfil.permissions == frozenset({LOCATION, CAMERA})


# === Sessão morna ===
def test_cold_start_e_manter_estado_sao_exclusivos():
    with pytest.raises(ValueError, match="ao mesmo tempo"):
        LaunchProfile(cold_start=True, manter_estado=True)


def test_metodos_preservam_todos_os_campos():
    # Um campo novo (manter_estado) não pode se perder em silêncio ao
    # derivar o perfil.
    perfil = LaunchProfile(manter_estado=True).com_permissoes(LOCATION)

    assert perfil.manter_estado is True
    assert LOCATION in perfil.permissions
