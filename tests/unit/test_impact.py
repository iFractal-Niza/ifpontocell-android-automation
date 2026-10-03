"""
Análise de impacto (scripts.impact): dependência por import e por
fixture, até o fim da cadeia, e a recomendação do que rodar.
"""

from scripts.impact import (
    calcular_impacto,
    classificar,
    ler_projeto,
    recomendar,
    resolver_alvo,
)

ARQUIVOS = {
    "conftest.py": 'pytest_plugins = ["tests.fixtures.jornada"]\n',
    "pages/base_page.py": "class BasePage: ...\n",
    "pages/assinar_page.py": "from pages.base_page import BasePage\n",
    "pages/impressao_page.py": "from pages.assinar_page import X\n",
    "pages/assinatura_page.py": "from pages import impressao_page\n",
    "pages/solta_page.py": "import os\n",
    "observability/casos.py": "x = 1\n",
    "tests/fixtures/casos.py": "x = 2\n",
    "tests/fixtures/jornada.py": (
        "import pytest\n"
        "from pages.base_page import BasePage\n\n\n"
        "@pytest.fixture\n"
        "def sessao():\n"
        "    ...\n\n\n"
        "@pytest.fixture(name='home_autenticada')\n"
        "def _home(sessao):\n"
        "    ...\n"
    ),
    "tests/app/test_ass_espelho.py": (
        "from pages.assinatura_page import Y\n\n\n"
        "def test_assinar(home_autenticada):\n"
        "    ...\n"
    ),
    "tests/app/test_holerite.py": (
        "def test_holerite(home_autenticada):\n    ...\n"
    ),
    "tests/app/test_ferias.py": (
        "import pytest\n\n\n"
        "@pytest.mark.usefixtures('sessao')\n"
        "def test_ferias():\n"
        "    ...\n"
    ),
    "tests/app/test_login.py": "def test_login(tmp_path):\n    ...\n",
    "tests/api/test_celular.py": "from pages.base_page import BasePage\n",
    "tests/unit/test_base.py": "from pages.base_page import BasePage\n",
}


def _projeto(tmp_path):
    for caminho, codigo in ARQUIVOS.items():
        arquivo = tmp_path / caminho
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(codigo, encoding="utf-8")

    return ler_projeto(tmp_path)


def test_segue_os_imports_ate_o_fim_da_cadeia(tmp_path):
    # Caso real: assinar -> impressão -> assinatura -> teste (3 níveis)
    # saía como "0 testes afetados".
    impacto = calcular_impacto("pages/assinar_page.py", _projeto(tmp_path))

    assert impacto["pages/impressao_page.py"][0] == 1
    assert impacto["pages/assinatura_page.py"][0] == 2
    assert impacto["tests/app/test_ass_espelho.py"][0] == 3


def test_fixture_liga_o_arquivo_aos_testes_que_a_pedem(tmp_path):
    # Caso real: tests/fixtures/jornada.py parecia afetar só um teste
    # unitário; os testes pedem a fixture pelo nome, sem import.
    impacto = calcular_impacto("tests/fixtures/jornada.py", _projeto(tmp_path))

    assert "home_autenticada" in impacto["tests/app/test_holerite.py"][2]
    assert "tests/app/test_ass_espelho.py" in impacto
    # Pedida por usefixtures, não por parâmetro.
    assert "sessao" in impacto["tests/app/test_ferias.py"][2]
    # Carregada pelo pytest_plugins do conftest.
    assert "conftest.py" in impacto
    # Não pede nenhuma fixture do arquivo.
    assert "tests/app/test_login.py" not in impacto


def test_fixture_entra_na_cadeia_de_imports(tmp_path):
    # base_page -> jornada.py (import) -> test_holerite (fixture).
    impacto = calcular_impacto("pages/base_page.py", _projeto(tmp_path))

    assert "tests/app/test_holerite.py" in impacto
    assert "tests/unit/test_base.py" in impacto


def test_arquivo_sem_dependentes(tmp_path):
    assert calcular_impacto("pages/solta_page.py", _projeto(tmp_path)) == {}


def test_separa_tela_api_unitarios_e_outros(tmp_path):
    impacto = calcular_impacto("pages/base_page.py", _projeto(tmp_path))
    grupos = classificar(impacto)

    assert "tests/app/test_holerite.py" in grupos["tela"]
    assert grupos["api"] == ["tests/api/test_celular.py"]
    assert grupos["unit"] == ["tests/unit/test_base.py"]
    assert "tests/fixtures/jornada.py" in grupos["outros"]


def test_recomenda_o_alvo_de_cada_tela():
    comandos = recomendar(
        {
            "tela": [
                "tests/app/test_holerite.py",
                "tests/app/test_ferias.py",
            ],
            "api": [],
            "unit": ["tests/unit/test_x.py"],
            "outros": [],
        }
    )

    assert comandos == [
        "make unit",
        "make holerite",
        # Tela nova, ainda sem alvo no Makefile.
        "venv/bin/python -m pytest tests/app/test_ferias.py",
    ]


def test_muitas_telas_recomenda_a_suite_inteira():
    comandos = recomendar(
        {
            "tela": [
                "tests/app/test_holerite.py",
                "tests/app/test_login.py",
                "tests/app/test_unlock.py",
                "tests/app/test_e2e.py",
            ],
            "api": ["tests/api/test_celular_api.py"],
            "unit": [],
            "outros": [],
        }
    )

    assert comandos[0] == "make api"
    assert comandos[1].startswith("make run")
    assert len(comandos) == 2


def test_so_report_recomenda_so_os_unitarios():
    grupos = {"tela": [], "api": [], "unit": ["tests/unit/t.py"], "outros": []}

    assert recomendar(grupos) == ["make unit"]


def test_alvo_pelo_nome_pelo_final_ou_pelo_caminho(tmp_path):
    projeto = _projeto(tmp_path)

    assert resolver_alvo("solta_page", projeto) == ["pages/solta_page.py"]
    assert resolver_alvo("solta_page.py", projeto) == ["pages/solta_page.py"]
    assert resolver_alvo("fixtures/jornada.py", projeto) == [
        "tests/fixtures/jornada.py"
    ]
    assert resolver_alvo("./pages/solta_page.py", projeto) == [
        "pages/solta_page.py"
    ]


def test_nome_repetido_devolve_todos_os_candidatos(tmp_path):
    assert resolver_alvo("casos.py", _projeto(tmp_path)) == [
        "observability/casos.py",
        "tests/fixtures/casos.py",
    ]


def test_arquivo_inexistente(tmp_path):
    assert resolver_alvo("nao_existe.py", _projeto(tmp_path)) == []


def test_projeto_real_e_lido_sem_erro():
    projeto = ler_projeto()

    assert "pages/base_page.py" in projeto
    assert "home_autenticada" in (
        projeto["tests/fixtures/jornada.py"].fixtures_definidas
    )
