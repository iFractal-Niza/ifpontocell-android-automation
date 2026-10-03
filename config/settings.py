"""
Configuração tipada da suíte, lida do os.environ (carregado do
env.<device>.yaml por config.env_loader).

Único lugar que interpreta as variáveis: converte tipos, aplica
defaults e valida. Os erros de formato são acumulados e levantados
juntos em ConfiguracaoInvalida, para o env.<device>.yaml ser corrigido de uma
vez, e não um erro por execução.

Sem cache: from_env() relê o ambiente a cada chamada (é barato), o que
mantém os testes unitários independentes entre si.

Grupos sem regra de formato (API, credenciais do app) nunca levantam:
obrigatoriedade deles é checada por quem os usa, para que uma config
de Android incompleta não bloqueie, por exemplo, 'make api'.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from utils.ponto import ler_jornada

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ANDROID_TARGETS = ("emulator", "real")
APP_SOURCES = ("apk", "package")

APP_PACKAGE_PADRAO = "br.com.ifractal.Stou"
APP_ACTIVITY_PADRAO = "br.com.ifractal.stou.view.MainActivity"

VERDADEIROS = frozenset({"true", "1", "yes", "on"})
FALSOS = frozenset({"false", "0", "no", "off"})


class ConfiguracaoInvalida(ValueError):
    """Um ou mais valores do env.<device>.yaml inválidos, listados juntos."""

    def __init__(self, erros: list[str]) -> None:
        self.erros = erros
        itens = "\n".join(f"  - {erro}" for erro in erros)
        super().__init__(
            f"Configuração inválida no env do aparelho ({len(erros)}):\n"
            f"{itens}"
        )


# === Leitura com acúmulo de erros ===
class _Leitor:
    def __init__(self, env: Mapping[str, str]) -> None:
        self._env = env
        self.erros: list[str] = []

    def texto(self, nome: str, padrao: str = "") -> str:
        return str(self._env.get(nome, "")).strip() or padrao

    def obrigatorio(self, nome: str, contexto: str) -> str:
        valor = self.texto(nome)

        if not valor:
            self.erros.append(f"{nome} não configurado ({contexto}).")

        return valor

    def booleano(self, nome: str, padrao: bool) -> bool:
        valor = self.texto(nome).lower()

        if not valor:
            return padrao

        if valor in VERDADEIROS:
            return True

        if valor in FALSOS:
            return False

        self.erros.append(
            f"{nome} deve ser true ou false. Valor atual: {valor!r}."
        )
        return padrao

    def inteiro(self, nome: str, padrao: int, minimo: int) -> int:
        bruto = self.texto(nome)

        if not bruto:
            return padrao

        try:
            valor = int(bruto)
        except ValueError:
            self.erros.append(
                f"{nome} deve ser um número inteiro. Valor atual: {bruto!r}."
            )
            return padrao

        if valor < minimo:
            self.erros.append(
                f"{nome} deve ser maior ou igual a {minimo}. "
                f"Valor atual: {valor}."
            )
            return padrao

        return valor

    def inteiro_opcional(self, nome: str, minimo: int) -> int | None:
        if not self.texto(nome):
            return None

        return self.inteiro(nome, padrao=0, minimo=minimo) or None

    def escolha(self, nome: str, padrao: str, opcoes: tuple[str, ...]) -> str:
        valor = self.texto(nome, padrao).lower()

        if valor not in opcoes:
            self.erros.append(
                f"{nome} inválido: {valor!r}. Use {' ou '.join(opcoes)}."
            )
            return padrao

        return valor

    def coordenada(self, nome: str, limite: int) -> float | None:
        bruto = self.texto(nome)

        try:
            valor = float(bruto)
        except ValueError:
            self.erros.append(
                f"{nome} deve ser uma coordenada numérica. "
                f"Valor atual: {bruto!r}."
            )
            return None

        if not -limite <= valor <= limite:
            self.erros.append(
                f"{nome} deve estar entre -{limite} e {limite}. "
                f"Valor atual: {valor}."
            )
            return None

        return valor


# === Grupos ===
@dataclass(frozen=True)
class AppConfig:
    package: str
    activity: str
    # "*" aceita qualquer activity como tela inicial (splash, onboarding).
    wait_activity: str


@dataclass(frozen=True)
class DeviceConfig:
    """
    Emulador ou celular. No emulador, o udid é opcional (o Appium usa o
    único device conectado); no celular, obrigatório (adb -s <udid>).
    """

    udid: str
    device_name: str
    platform_version: str


@dataclass(frozen=True)
class ExecucaoConfig:
    appium_port: int
    new_command_timeout: int
    no_reset: bool
    full_reset: bool
    auto_grant_permissions: bool
    # Zera as escalas de animação do sistema (equivalente Android do
    # reduceMotion do iOS, e mais forte: desliga, não só reduz).
    disable_window_animation: bool
    ignore_hidden_api_policy_error: bool
    wait_for_idle_timeout: int
    # Porta do servidor UiAutomator2 no Mac. None: a padrão do driver
    # (8200). Emulador e celular ao mesmo tempo precisam de portas
    # diferentes (como o WebDriverAgent no iOS: 8100 e 8101).
    system_port: int | None


@dataclass(frozen=True)
class Localizacao:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class GeoDelimitacao:
    """
    Massa de teste da geo delimitação: um ponto dentro e um fora da
    área cadastrada para o usuário de teste (ANDROID_GEO_* no
    env.<device>.yaml).
    """

    dentro: Localizacao
    fora: Localizacao


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    user: str
    token: str
    monitor_nome_pessoa: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ApiConfig":
        leitor = _Leitor(os.environ if env is None else env)

        return cls(
            base_url=leitor.texto("API_BASE_URL"),
            user=leitor.texto("API_USER"),
            token=leitor.texto("API_TOKEN"),
            monitor_nome_pessoa=leitor.texto("MONITOR_NOME_PESSOA"),
        )


@dataclass(frozen=True)
class CredenciaisApp:
    sistema: str
    usuario: str
    senha: str
    pin: str
    # PIN usado pelo teste de Alterar Senha (troca e restaura). "" se
    # não configurado: o teste é pulado.
    pin_novo: str
    # Senha temporária do teste de troca da senha do sistema (troca e
    # restaura). "" se não configurada: o teste é pulado.
    senha_nova: str
    # Horários da jornada do usuário (APP_JORNADA), como a tela Ponto
    # mostra num dia escalado futuro. Vazia se não configurada: o teste
    # não compara a escala.
    jornada: tuple[str, ...] = ()

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None
    ) -> "CredenciaisApp":
        leitor = _Leitor(os.environ if env is None else env)

        return cls(
            sistema=leitor.texto("APP_SYSTEM"),
            usuario=leitor.texto("APP_USER"),
            senha=leitor.texto("APP_PASSWORD"),
            pin=leitor.texto("APP_PIN"),
            pin_novo=leitor.texto("APP_PIN_NOVO"),
            senha_nova=leitor.texto("APP_PASSWORD_NOVA"),
            jornada=tuple(_jornada_ou_vazia(leitor.texto("APP_JORNADA"))),
        )


def _jornada_ou_vazia(texto: str) -> list[str]:
    # Inválida vira vazia aqui; quem acusa o erro é o Settings.from_env.
    try:
        return ler_jornada(texto)
    except ValueError:
        return []


# === Resolver leve do alvo ===
def ler_android_target(env: Mapping[str, str] | None = None) -> str:
    """
    Só o ANDROID_TARGET, sem validar o resto.

    Usado por is_emulator(), que é consultado em vários pontos que não
    devem falhar por causa de outra variável inválida.
    """
    leitor = _Leitor(os.environ if env is None else env)
    alvo = leitor.escolha("ANDROID_TARGET", "emulator", ANDROID_TARGETS)

    if leitor.erros:
        raise ConfiguracaoInvalida(leitor.erros)

    return alvo


# === Configuração completa ===
@dataclass(frozen=True)
class Settings:
    android_target: str
    app_source: str
    app: AppConfig
    apk_path: Path
    device: DeviceConfig
    execucao: ExecucaoConfig
    # None quando desligada.
    localizacao: Localizacao | None
    # Flag desligada com coordenadas preenchidas: quase sempre
    # esquecimento; quem aplica a localização avisa.
    localizacao_desligada_com_coordenadas: bool
    # None quando as coordenadas da geo não foram preenchidas (os testes
    # de geo são pulados).
    geo: GeoDelimitacao | None
    api: ApiConfig
    credenciais: CredenciaisApp

    @property
    def is_emulator(self) -> bool:
        return self.android_target == "emulator"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        leitor = _Leitor(env)

        android_target = leitor.escolha(
            "ANDROID_TARGET", "emulator", ANDROID_TARGETS
        )
        app_source = leitor.escolha("APP_SOURCE", "apk", APP_SOURCES)

        app = AppConfig(
            package=leitor.texto("ANDROID_APP_PACKAGE", APP_PACKAGE_PADRAO),
            activity=leitor.texto("ANDROID_APP_ACTIVITY", APP_ACTIVITY_PADRAO),
            wait_activity=leitor.texto("ANDROID_APP_WAIT_ACTIVITY", "*"),
        )

        apk_path = (
            Path(
                leitor.texto("APP_PATH")
                or PROJECT_ROOT / "app" / "ifPontoCell.apk"
            )
            .expanduser()
            .resolve()
        )

        if app_source == "apk" and apk_path.suffix.lower() != ".apk":
            leitor.erros.append(
                f"APP_PATH deve apontar para um arquivo .apk: {apk_path}"
            )

        device = DeviceConfig(
            udid=(
                leitor.obrigatorio(
                    "ANDROID_UDID", "exigido com ANDROID_TARGET=real"
                )
                if android_target == "real"
                else leitor.texto("ANDROID_UDID")
            ),
            device_name=leitor.texto("ANDROID_DEVICE_NAME"),
            platform_version=leitor.texto("ANDROID_PLATFORM_VERSION"),
        )

        execucao = ExecucaoConfig(
            appium_port=leitor.inteiro("APPIUM_PORT", 4723, minimo=1),
            new_command_timeout=leitor.inteiro(
                "ANDROID_NEW_COMMAND_TIMEOUT", 120, minimo=1
            ),
            no_reset=leitor.booleano("ANDROID_NO_RESET", False),
            full_reset=leitor.booleano("ANDROID_FULL_RESET", False),
            auto_grant_permissions=leitor.booleano(
                "ANDROID_AUTO_GRANT_PERMISSIONS", True
            ),
            disable_window_animation=leitor.booleano(
                "ANDROID_DISABLE_WINDOW_ANIMATION", True
            ),
            ignore_hidden_api_policy_error=leitor.booleano(
                "ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR", True
            ),
            wait_for_idle_timeout=leitor.inteiro(
                "ANDROID_WAIT_FOR_IDLE_TIMEOUT", 500, minimo=0
            ),
            system_port=leitor.inteiro_opcional(
                "ANDROID_SYSTEM_PORT", minimo=1
            ),
        )

        localizacao, desligada_com_coordenadas = cls._ler_localizacao(leitor)
        geo = cls._ler_geo(leitor)

        try:
            ler_jornada(leitor.texto("APP_JORNADA"))
        except ValueError as erro:
            leitor.erros.append(str(erro))

        if leitor.erros:
            raise ConfiguracaoInvalida(leitor.erros)

        return cls(
            android_target=android_target,
            app_source=app_source,
            app=app,
            apk_path=apk_path,
            device=device,
            execucao=execucao,
            localizacao=localizacao,
            localizacao_desligada_com_coordenadas=desligada_com_coordenadas,
            geo=geo,
            api=ApiConfig.from_env(env),
            credenciais=CredenciaisApp.from_env(env),
        )

    @staticmethod
    def _ler_localizacao(
        leitor: _Leitor,
    ) -> tuple[Localizacao | None, bool]:
        """
        Localização simulada (driver.set_location): no emulador e no
        celular. No celular, o app precisa aceitar localização simulada
        (opções do desenvolvedor > app de localização fictícia = Appium
        Settings); sem ela vale o GPS de verdade.
        """
        preenchidas = bool(
            leitor.texto("ANDROID_LOCATION_LATITUDE")
            or leitor.texto("ANDROID_LOCATION_LONGITUDE")
        )

        if not leitor.booleano("ANDROID_LOCATION_ENABLED", False):
            return None, preenchidas

        if not (
            leitor.texto("ANDROID_LOCATION_LATITUDE")
            and leitor.texto("ANDROID_LOCATION_LONGITUDE")
        ):
            leitor.erros.append(
                "ANDROID_LOCATION_ENABLED=true, mas "
                "ANDROID_LOCATION_LATITUDE e ANDROID_LOCATION_LONGITUDE "
                "não foram configuradas."
            )
            return None, False

        latitude = leitor.coordenada("ANDROID_LOCATION_LATITUDE", 90)
        longitude = leitor.coordenada("ANDROID_LOCATION_LONGITUDE", 180)

        if latitude is None or longitude is None:
            return None, False

        return Localizacao(latitude=latitude, longitude=longitude), False

    @staticmethod
    def _ler_geo(leitor: _Leitor) -> GeoDelimitacao | None:
        """
        Coordenadas da massa de geo delimitação. Opcionais: sem nenhuma
        preenchida, None. Preenchidas pela metade é erro (quase sempre
        esquecimento), para o teste não ser pulado sem ninguém notar.
        """
        nomes = (
            "ANDROID_GEO_DENTRO_LATITUDE",
            "ANDROID_GEO_DENTRO_LONGITUDE",
            "ANDROID_GEO_FORA_LATITUDE",
            "ANDROID_GEO_FORA_LONGITUDE",
        )
        preenchidos = [nome for nome in nomes if leitor.texto(nome)]

        if not preenchidos:
            return None

        if len(preenchidos) < len(nomes):
            faltando = ", ".join(n for n in nomes if n not in preenchidos)
            leitor.erros.append(
                f"Geo delimitação configurada pela metade: falta {faltando}."
            )
            return None

        coordenadas = [
            leitor.coordenada(nome, 90 if "LATITUDE" in nome else 180)
            for nome in nomes
        ]

        if any(valor is None for valor in coordenadas):
            return None

        return GeoDelimitacao(
            dentro=Localizacao(coordenadas[0], coordenadas[1]),
            fora=Localizacao(coordenadas[2], coordenadas[3]),
        )
