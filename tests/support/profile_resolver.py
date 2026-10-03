from collections.abc import Iterable

from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_event


logger = get_logger("profile_resolver")


def resolver_profile(
    request,
    cold_start: bool,
    permissions: Iterable[str] = (),
) -> LaunchProfile:
    """Monta o LaunchProfile Android do teste atual."""
    marker = request.node.get_closest_marker("fake_capture")
    if marker is not None:
        log_event(
            logger,
            "Marker fake_capture ignorado no Android",
            event="fake_capture_ignored_android",
            fixture=request.fixturename,
        )

    profile = LaunchProfile(
        cold_start=cold_start,
        permissions=frozenset(permissions),
    )

    log_event(
        logger,
        "LaunchProfile Android resolvido",
        event="launch_profile_resolved",
        fixture=request.fixturename,
        scope=request.scope,
        cold_start=profile.cold_start,
        permissions=sorted(profile.permissions),
    )
    return profile
