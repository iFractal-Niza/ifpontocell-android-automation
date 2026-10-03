"""
Catálogo dos casos de teste (CT), lido dos próprios arquivos de teste.

Cada teste de tela ou de API tem um @pytest.mark.ct("CT001"); o ID
aparece no report e permite rodar o caso com --ct. Daqui sai a checagem
de que todo teste tem um ID único (teste unitário, roda no pre-commit).
A leitura é estática (ast): não importa os testes, então não precisa de
Appium, emulador nem env.<device>.yaml.
"""

import ast
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Pastas cujos testes têm CT. Os unitários ficam de fora: validam a
# automação, não o app.
PASTAS_COM_CT = ("tests/app", "tests/api")

MARKER_CT = "ct"
FORMATO_ID = re.compile(r"^CT\d{3}$")


@dataclass(frozen=True)
class CasoTeste:
    # "" quando o teste ainda não tem o marker ct.
    id: str
    nodeid: str


def _id_do_ct(funcao: ast.FunctionDef) -> str:
    """Argumento do @pytest.mark.ct("...") da função; "" se não houver."""
    for decorador in funcao.decorator_list:
        if not (
            isinstance(decorador, ast.Call)
            and isinstance(decorador.func, ast.Attribute)
            and decorador.func.attr == MARKER_CT
            and decorador.args
            and isinstance(decorador.args[0], ast.Constant)
        ):
            continue

        return str(decorador.args[0].value)

    return ""


def ler_casos(raiz: Path = PROJECT_ROOT) -> list[CasoTeste]:
    """Um CasoTeste por função test_* das pastas com CT."""
    casos = []

    for pasta in PASTAS_COM_CT:
        for arquivo in sorted((raiz / pasta).glob("test_*.py")):
            casos.extend(_casos_do_arquivo(arquivo, raiz))

    return sorted(casos, key=lambda caso: (caso.id == "", caso.id))


def _casos_do_arquivo(arquivo: Path, raiz: Path) -> list[CasoTeste]:
    """As funções test_* do arquivo, na ordem em que aparecem."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    caminho = arquivo.relative_to(raiz).as_posix()

    return [
        CasoTeste(id=_id_do_ct(no), nodeid=f"{caminho}::{no.name}")
        for no in arvore.body
        if isinstance(no, ast.FunctionDef) and no.name.startswith("test_")
    ]


# === Ordem da suíte e renumeração ===
def arquivos_da_suite(raiz: Path = PROJECT_ROOT) -> list[Path]:
    """
    Arquivos de teste na ordem do make run: os da APP_SUITE do Makefile,
    na ordem listada, e depois os de tests/api.
    """
    makefile = (raiz / "Makefile").read_text(encoding="utf-8")

    variaveis = dict(
        re.findall(
            r"^(TEST_[A-Z0-9_]+)\s*:=\s*\$\(APP_TESTS\)/(test_\w+\.py)\s*$",
            makefile,
            flags=re.MULTILINE,
        )
    )
    bloco = re.search(
        r"^APP_SUITE\s*:=\s*\\\n((?:\t.*\\?\n)+)",
        makefile,
        flags=re.MULTILINE,
    )

    if bloco is None:
        raise ValueError("APP_SUITE não encontrada no Makefile.")

    arquivos = [
        raiz / "tests" / "app" / variaveis[nome]
        for nome in re.findall(r"\$\((TEST_[A-Z0-9_]+)\)", bloco.group(1))
        if nome in variaveis
    ]

    return arquivos + sorted((raiz / "tests" / "api").glob("test_*.py"))


def casos_na_ordem_da_suite(raiz: Path = PROJECT_ROOT) -> list[CasoTeste]:
    return [
        caso
        for arquivo in arquivos_da_suite(raiz)
        for caso in _casos_do_arquivo(arquivo, raiz)
    ]


def mapa_de_renumeracao(casos: list[CasoTeste]) -> dict[str, str]:
    """
    {ID atual: ID novo} numerando em sequência, na ordem recebida. Teste
    sem CT não entra (a trava de CT único já reprova esse caso).
    """
    com_id = [caso for caso in casos if caso.id]

    return {
        caso.id: f"CT{numero:03d}"
        for numero, caso in enumerate(com_id, start=1)
    }


def aplicar_renumeracao(
    mapa: dict[str, str],
    arquivos: list[Path],
) -> list[Path]:
    """
    Troca os IDs nos arquivos (markers e menções em docstrings e
    comentários), todos de uma vez: CT011 -> CT014 e CT014 -> CT011 não
    se atropelam. Devolve os arquivos alterados.
    """
    padrao = re.compile(r"\bCT\d{3}\b")
    alterados = []

    for arquivo in arquivos:
        texto = arquivo.read_text(encoding="utf-8")
        novo = padrao.sub(lambda m: mapa.get(m.group(0), m.group(0)), texto)

        if novo != texto:
            arquivo.write_text(novo, encoding="utf-8")
            alterados.append(arquivo)

    return alterados


def validar_casos(casos: list[CasoTeste]) -> list[str]:
    """
    Problemas do catálogo: teste sem CT, ID fora do formato CT000 e ID
    repetido. Lista vazia quando está tudo certo.
    """
    erros = []

    for caso in casos:
        if not caso.id:
            erros.append(
                f"{caso.nodeid}: sem @pytest.mark.{MARKER_CT}(...). "
                f"Próximo ID livre: {proximo_id(casos)}."
            )
        elif not FORMATO_ID.match(caso.id):
            erros.append(
                f"{caso.nodeid}: ID {caso.id!r} fora do formato CT000."
            )

    repetidos = Counter(caso.id for caso in casos if caso.id)

    for identificador, quantidade in sorted(repetidos.items()):
        if quantidade > 1:
            donos = ", ".join(
                caso.nodeid for caso in casos if caso.id == identificador
            )
            erros.append(f"{identificador} repetido em: {donos}.")

    return erros


def proximo_id(casos: list[CasoTeste]) -> str:
    """Próximo ID da sequência (o maior número usado + 1)."""
    numeros = [int(caso.id[2:]) for caso in casos if FORMATO_ID.match(caso.id)]

    return f"CT{max(numeros, default=0) + 1:03d}"
