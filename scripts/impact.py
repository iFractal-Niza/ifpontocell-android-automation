"""
Análise de impacto reverso (make impact file=x.py): quais arquivos e
testes dependem do arquivo informado, e o que rodar para validar.

Segue duas formas de dependência, até o fim da cadeia:
- import: quem importa o módulo (direta ou indiretamente);
- fixture: quem pede, pelo nome do parâmetro, uma fixture definida no
  arquivo. As fixtures chegam aos testes pelo pytest_plugins do
  conftest, sem import: sem esta regra, mexer em tests/fixtures/ parecia
  não afetar nenhum teste de tela.

A leitura é estática (ast): não importa os módulos nem precisa do venv.
"""

import ast
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PASTAS = (
    "api",
    "config",
    "core",
    "observability",
    "pages",
    "scripts",
    "tests",
    "utils",
)
ARQUIVOS_NA_RAIZ = ("conftest.py",)

# Alvo do Makefile que roda cada arquivo de teste de tela/API.
ALVO_POR_TESTE = {
    "tests/app/test_onboarding.py": "make onboarding",
    "tests/app/test_login.py": "make login",
    "tests/app/test_unlock.py": "make unlock",
    "tests/app/test_e2e.py": "make e2e",
    "tests/app/test_registro_sem_foto.py": "make registro-ponto",
    "tests/app/test_status.py": "make status",
    "tests/app/test_ponto.py": "make ponto",
    "tests/app/test_registro_geo.py": "make registro-geo",
    "tests/app/test_holerite.py": "make holerite",
    "tests/app/test_informe_rendimentos.py": "make informe",
    "tests/app/test_estado_humor.py": "make humor",
    "tests/app/test_ass_espelho.py": "make ass-espelho",
    "tests/app/test_sobre_aplicativo.py": "make sobre",
    "tests/app/test_dados_pessoais.py": "make dados-pessoais",
    "tests/app/test_privacidade.py": "make privacidade",
    "tests/app/test_alterar_pin.py": "make alterar-pin",
    "tests/app/test_alterar_senha_sistema.py": "make alterar-senha-sistema",
    "tests/app/test_zerar_dados.py": "make zerar-dados",
}
ALVO_API = "make api"

# A partir de quantos alvos de tela compensa rodar a suíte inteira.
LIMITE_SUITE_COMPLETA = 4


@dataclass
class Arquivo:
    caminho: str
    # Caminhos dos arquivos do projeto que este importa.
    importa: set[str] = field(default_factory=set)
    fixtures_definidas: set[str] = field(default_factory=set)
    fixtures_autouse: set[str] = field(default_factory=set)
    # Nomes pedidos por testes e fixtures deste arquivo (parâmetros,
    # usefixtures e getfixturevalue); só contam os que são fixtures.
    nomes_pedidos: set[str] = field(default_factory=set)
    hooks: set[str] = field(default_factory=set)


# === Leitura dos arquivos ===
def listar_arquivos(raiz: Path) -> list[str]:
    caminhos = [nome for nome in ARQUIVOS_NA_RAIZ if (raiz / nome).is_file()]

    for pasta in PASTAS:
        caminhos.extend(
            arquivo.relative_to(raiz).as_posix()
            for arquivo in sorted((raiz / pasta).rglob("*.py"))
            if "__pycache__" not in arquivo.parts
        )

    return caminhos


def _caminho_do_modulo(modulo: str, existentes: set[str]) -> str | None:
    """ "pages.home_page" -> "pages/home_page.py", se existir."""
    base = modulo.replace(".", "/")

    for candidato in (f"{base}.py", f"{base}/__init__.py"):
        if candidato in existentes:
            return candidato

    return None


def _imports(arvore: ast.AST, existentes: set[str]) -> set[str]:
    modulos = set()

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            modulos.update(nome.name for nome in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
            modulos.add(no.module)
            # "from observability import execution_metrics": o nome
            # importado pode ser um módulo do pacote.
            modulos.update(f"{no.module}.{nome.name}" for nome in no.names)

    caminhos = (_caminho_do_modulo(modulo, existentes) for modulo in modulos)

    return {caminho for caminho in caminhos if caminho}


def _plugins(arvore: ast.AST, existentes: set[str]) -> set[str]:
    """Módulos listados em pytest_plugins = [...]."""
    caminhos = set()

    for no in ast.walk(arvore):
        if not (
            isinstance(no, ast.Assign)
            and any(
                isinstance(alvo, ast.Name) and alvo.id == "pytest_plugins"
                for alvo in no.targets
            )
        ):
            continue

        for item in ast.walk(no.value):
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                caminho = _caminho_do_modulo(item.value, existentes)

                if caminho:
                    caminhos.add(caminho)

    return caminhos


def _decorador_fixture(funcao: ast.FunctionDef) -> ast.expr | None:
    for decorador in funcao.decorator_list:
        alvo = decorador.func if isinstance(decorador, ast.Call) else decorador
        nome = getattr(alvo, "attr", None) or getattr(alvo, "id", None)

        if nome == "fixture":
            return decorador

    return None


def _argumento(decorador: ast.expr, nome: str):
    if not isinstance(decorador, ast.Call):
        return None

    for argumento in decorador.keywords:
        if argumento.arg == nome and isinstance(argumento.value, ast.Constant):
            return argumento.value.value

    return None


def _nomes_em_strings(arvore: ast.AST) -> set[str]:
    """Fixtures pedidas por nome: usefixtures("x"), getfixturevalue("x")."""
    nomes = set()

    for no in ast.walk(arvore):
        if not (
            isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        ):
            continue

        if no.func.attr in ("usefixtures", "getfixturevalue"):
            nomes.update(
                argumento.value
                for argumento in no.args
                if isinstance(argumento, ast.Constant)
                and isinstance(argumento.value, str)
            )

    return nomes


def analisar(caminho: str, codigo: str, existentes: set[str]) -> Arquivo:
    arvore = ast.parse(codigo)
    arquivo = Arquivo(
        caminho=caminho,
        importa=_imports(arvore, existentes) | _plugins(arvore, existentes),
        nomes_pedidos=_nomes_em_strings(arvore),
    )
    arquivo.importa.discard(caminho)

    for no in ast.walk(arvore):
        if not isinstance(no, ast.FunctionDef):
            continue

        parametros = {
            argumento.arg for argumento in (*no.args.args, *no.args.kwonlyargs)
        }
        decorador = _decorador_fixture(no)

        if decorador is not None:
            nome = _argumento(decorador, "name") or no.name
            arquivo.fixtures_definidas.add(nome)
            arquivo.nomes_pedidos |= parametros

            if _argumento(decorador, "autouse") is True:
                arquivo.fixtures_autouse.add(nome)

        elif no.name.startswith("test_"):
            arquivo.nomes_pedidos |= parametros

        elif no.name.startswith("pytest_"):
            arquivo.hooks.add(no.name)

    return arquivo


def ler_projeto(raiz: Path = PROJECT_ROOT) -> dict[str, Arquivo]:
    caminhos = listar_arquivos(raiz)
    existentes = set(caminhos)

    return {
        caminho: analisar(
            caminho,
            (raiz / caminho).read_text(encoding="utf-8"),
            existentes,
        )
        for caminho in caminhos
    }


# === Dependentes ===
def dependentes_diretos(
    alvo: str,
    projeto: dict[str, Arquivo],
) -> dict[str, str]:
    """{caminho: motivo} de quem depende diretamente do alvo."""
    fixtures = projeto[alvo].fixtures_definidas
    diretos = {}

    for caminho, arquivo in projeto.items():
        if caminho == alvo:
            continue

        usadas = sorted(fixtures & arquivo.nomes_pedidos)

        if alvo in arquivo.importa:
            diretos[caminho] = "importa"
        elif usadas:
            diretos[caminho] = f"usa a fixture {', '.join(usadas)}"

    return diretos


def calcular_impacto(
    alvo: str,
    projeto: dict[str, Arquivo],
) -> dict[str, tuple[int, str, str]]:
    """
    Todos os dependentes do alvo, até o fim da cadeia:
    {caminho: (nível, via qual arquivo, motivo)}.
    """
    impacto: dict[str, tuple[int, str, str]] = {}
    fila = deque([(alvo, 0)])

    while fila:
        atual, nivel = fila.popleft()

        for caminho, motivo in sorted(
            dependentes_diretos(atual, projeto).items()
        ):
            if caminho == alvo or caminho in impacto:
                continue

            impacto[caminho] = (nivel + 1, atual, motivo)
            fila.append((caminho, nivel + 1))

    return impacto


# === Classificação e recomendação ===
def _eh_teste(caminho: str) -> bool:
    return caminho.startswith("tests/") and Path(caminho).name.startswith(
        "test_"
    )


def classificar(caminhos) -> dict[str, list[str]]:
    grupos: dict[str, list[str]] = {
        "tela": [],
        "api": [],
        "unit": [],
        "outros": [],
    }

    for caminho in sorted(caminhos):
        if not _eh_teste(caminho):
            grupos["outros"].append(caminho)
        elif caminho.startswith("tests/unit/"):
            grupos["unit"].append(caminho)
        elif caminho.startswith("tests/api/"):
            grupos["api"].append(caminho)
        else:
            grupos["tela"].append(caminho)

    return grupos


def recomendar(grupos: dict[str, list[str]]) -> list[str]:
    """Comandos para validar a mudança, do mais barato ao mais caro."""
    comandos = []

    if grupos["unit"]:
        comandos.append("make unit")

    if grupos["api"]:
        comandos.append(ALVO_API)

    alvos_de_tela = [
        ALVO_POR_TESTE.get(teste, f"venv/bin/python -m pytest {teste}")
        for teste in grupos["tela"]
    ]

    if len(alvos_de_tela) >= LIMITE_SUITE_COMPLETA:
        comandos.append(
            f"make run  ({len(alvos_de_tela)} arquivos de teste de tela)"
        )
    else:
        comandos.extend(alvos_de_tela)

    return comandos


# === Alvo informado ===
def resolver_alvo(argumento: str, projeto: dict[str, Arquivo]) -> list[str]:
    """
    Caminhos que casam com o argumento: caminho completo, final de
    caminho ("fixtures/jornada.py") ou só o nome ("jornada", "jornada.py").
    """
    nome = argumento.strip().removeprefix("./")

    if not nome.endswith(".py"):
        nome += ".py"

    if nome in projeto:
        return [nome]

    return sorted(
        caminho for caminho in projeto if caminho.endswith(f"/{nome}")
    )


# === Saída ===
def _listar(titulo: str, caminhos: list[str], impacto) -> None:
    if not caminhos:
        return

    print(f"  {titulo} ({len(caminhos)}):")

    for caminho in caminhos:
        nivel, via, motivo = impacto[caminho]
        origem = (
            f"importa {via}" if motivo == "importa" else f"{motivo} de {via}"
        )
        print(f"    - {caminho}  [nível {nivel}: {origem}]")

    print("")


def main(argumentos: list[str]) -> int:
    if len(argumentos) != 1 or not argumentos[0].strip():
        print("Informe o arquivo. Exemplo: make impact file=login_page.py")
        return 1

    projeto = ler_projeto()
    candidatos = resolver_alvo(argumentos[0], projeto)

    if not candidatos:
        print(f"Arquivo não encontrado no projeto: {argumentos[0]}")
        print("Só arquivos .py das pastas do projeto são analisados.")
        return 1

    if len(candidatos) > 1:
        print(f"Há mais de um arquivo chamado {argumentos[0]!r}:")

        for candidato in candidatos:
            print(f"  make impact file={candidato}")

        return 1

    alvo = candidatos[0]
    arquivo = projeto[alvo]
    impacto = calcular_impacto(alvo, projeto)
    grupos = classificar(impacto)

    print("")
    print(f"=== Impacto de mexer em: {alvo} ===")
    print("")

    if arquivo.hooks:
        print(
            "  ATENÇÃO: define hooks do pytest "
            f"({', '.join(sorted(arquivo.hooks))})."
        )
        print("  Hooks valem para toda execução em que o plugin é carregado,")
        print("  mesmo sem nenhum teste listado abaixo.")
        print("")

    if arquivo.fixtures_autouse:
        print(
            "  ATENÇÃO: fixture autouse "
            f"({', '.join(sorted(arquivo.fixtures_autouse))}): aplica-se "
            "aos testes do escopo sem ser pedida."
        )
        print("")

    if not impacto:
        print("  Nenhum arquivo depende deste (por import ou por fixture).")

        if _eh_teste(alvo):
            comando = recomendar(classificar([alvo]))[0]
            print(f"  É um arquivo de teste: rode o próprio ({comando}).")

        print("")
        return 0

    _listar("Testes de tela", grupos["tela"], impacto)
    _listar("Testes de API", grupos["api"], impacto)
    _listar("Testes unitários", grupos["unit"], impacto)
    _listar("Outros arquivos", grupos["outros"], impacto)

    print("  Para validar:")

    for comando in recomendar(grupos) or ["nenhum teste depende do arquivo"]:
        print(f"    {comando}")

    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
