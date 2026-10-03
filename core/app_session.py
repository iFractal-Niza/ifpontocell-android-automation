from selenium.common.exceptions import WebDriverException

from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_error, log_event


logger = get_logger("app_session")


class AppSession:
    """Dono do ciclo de vida do app Android dentro da sessão Appium."""

    def __init__(
        self,
        driver,
        app_package: str,
        device_udid: str,
        profile: LaunchProfile,
    ):
        self.driver = driver
        self.profile = profile
        self._app_package = app_package
        self._device_udid = device_udid

    def preparar(self) -> None:
        """
        Prepara a sessão Android.

        As permissões comuns são concedidas pela capability
        autoGrantPermissions. O conjunto profile.permissions continua
        existindo para manter a intenção da fixture explícita.
        """
        log_event(
            logger,
            "Sessão Android preparada",
            event="app_session_prepared",
            app_package=self._app_package,
            udid=self._device_udid,
            permissions=sorted(self.profile.permissions),
        )

    def relaunch(self) -> None:
        """Força o encerramento e reabre o app Android."""
        try:
            self.driver.terminate_app(self._app_package)
        except WebDriverException:
            log_event(
                logger,
                "App já estava encerrado antes do relaunch",
                event="app_session_already_terminated",
                app_package=self._app_package,
            )

        try:
            self.driver.activate_app(self._app_package)
        except WebDriverException as error:
            log_error(
                logger,
                "Falha ao reiniciar o app Android",
                event="app_session_relaunch_error",
                app_package=self._app_package,
                error=str(error),
                remediation=(
                    "Verifique ANDROID_APP_PACKAGE e se o app está instalado."
                ),
            )
            raise RuntimeError(
                "Não foi possível reiniciar o app Android."
            ) from error

        log_event(
            logger,
            "App Android reiniciado",
            event="app_session_relaunched",
            app_package=self._app_package,
        )

    def trocar_captura_simulada(self, asset: str) -> None:
        """
        Compatibilidade com a API antiga.

        A injeção de asset via launch argument era específica do iOS e não
        existe neste projeto Android. Mantém o relaunch para não quebrar
        chamadas legadas, mas o asset é ignorado.
        """
        log_event(
            logger,
            "Captura simulada não suportada no Android; asset ignorado",
            event="fake_capture_ignored_android",
            asset=asset,
        )
        self.relaunch()
