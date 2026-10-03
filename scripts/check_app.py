"""
Gate do make (check-app): com APP_SOURCE=apk, o APK do APP_PATH precisa
existir. Lê o env do aparelho pelo Settings, como a suíte.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.env_loader import carregar_env  # noqa: E402
from config.settings import ConfiguracaoInvalida, Settings  # noqa: E402


def main() -> int:
    try:
        carregar_env()
        settings = Settings.from_env()
    except ConfiguracaoInvalida as erro:
        print(erro)
        return 1

    if settings.app_source == "apk" and not settings.apk_path.is_file():
        print(f"APK não encontrado: {settings.apk_path}")
        print(
            "Adicione o ifPontoCell.apk em app/ (ou ajuste APP_PATH), "
            "ou use APP_SOURCE=package."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
