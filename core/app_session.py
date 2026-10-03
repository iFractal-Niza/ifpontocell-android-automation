from selenium.common.exceptions import WebDriverException

from core.launch_profile import LaunchProfile
from utils.logger import get_logger, log_error, log_event

logger = get_logger("app_session")


class AppSession:
    """
    Dono do ciclo de vida do app dentro de uma sessão Appium.

    Todo relançamento do app passa por relaunch(), único ponto que
    encerra e reabre o app pelo appPackage.
    """

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

    @property
    def app_package(self) -> str:
        return self._app_package

    # === Preparação da sessão ===
    def preparar(self) -> None:
        """
        Prepara a sessão.

        No Android as permissões do manifest já foram concedidas pelo
        autoGrantPermissions na instalação: diferente do iOS (simctl +
        relaunch), não há o que aplicar. Só registra a intenção do
        perfil no log.
        """
        log_event(
            logger,
            "Sessão Android preparada",
            event="app_session_prepared",
            app_package=self._app_package,
            udid=self._device_udid,
            permissions=sorted(self.profile.permissions),
        )

    # === Ciclo de vida do app ===
    def relaunch(self) -> None:
        """
        Encerra e reabre o app pelo appPackage.
        """
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

        except WebDriverException as erro:
            log_error(
                logger,
                "Falha ao reiniciar o app Android",
                event="app_session_relaunch_error",
                app_package=self._app_package,
                error=str(erro),
                remediation=(
                    "Verifique ANDROID_APP_PACKAGE e se o app está "
                    "instalado no device ('adb shell pm list packages')."
                ),
            )

            raise RuntimeError(
                "Não foi possível reiniciar o app Android. Verifique o "
                "ANDROID_APP_PACKAGE e se o app está instalado."
            ) from erro

        log_event(
            logger,
            "App Android reiniciado",
            event="app_session_relaunched",
            app_package=self._app_package,
        )
