import os

from utils.helpers import build_file_name, ensure_dir


# =========================
# SCREENSHOT
# =========================
def build_screenshot_path(
    base_dir: str,
    test_name: str,
    context: str = "falha",
) -> str:
    """
    Monta o caminho completo para salvar um screenshot de evidência.
    O nome do arquivo inclui o nome do teste, contexto e timestamp.
    """
    ensure_dir(base_dir)

    file_name = build_file_name(
        test_name=test_name,
        context=context,
        extension=".png",
    )

    return os.path.join(base_dir, file_name)
