from collections.abc import Iterable

from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_event

logger = get_logger("profile_resolver")


# === Markers reconhecidos ===
EXIBIR_LEMBRETE_MARKER = "exibir_lembrete"


def resolver_profile(
    request,
    cold_start: bool,
    permissions: Iterable[str] = (),
    manter_estado: bool = False,
) -> LaunchProfile:
    """
    Monta o LaunchProfile do teste atual.

    Args:
        request:
            Objeto request da fixture que está criando a sessão.

        cold_start:
            True para fluxos que exigem instalação limpa.

        permissions:
            Permissões exigidas pela fixture (intenção; quem concede é
            o autoGrantPermissions).

        manter_estado:
            True para a sessão morna (app como a execução anterior o
            deixou). Não combina com cold_start.

    O marker @pytest.mark.exibir_lembrete é só registrado no log: no
    iOS ele decide se o popup de lembrete é suprimido por launch
    argument; no Android não há como suprimir, e o lembrete sempre
    aparece depois do login (tratado por polling na Home).
    """
    exibir_lembrete = (
        request.node.get_closest_marker(EXIBIR_LEMBRETE_MARKER) is not None
    )

    profile = LaunchProfile(
        cold_start=cold_start,
        permissions=frozenset(permissions),
        manter_estado=manter_estado,
    )

    log_event(
        logger,
        "LaunchProfile resolvido para a sessão",
        event="launch_profile_resolved",
        fixture=request.fixturename,
        scope=request.scope,
        cold_start=profile.cold_start,
        manter_estado=profile.manter_estado,
        permissions=sorted(profile.permissions),
        exibir_lembrete=exibir_lembrete,
    )

    return profile
