"""
A suíte completa do Makefile (APP_SUITE, usada por make run, smoke,
regression e pelos merges) lista os arquivos de teste um a um, em ordem
controlada. Teste de tela novo fora da lista só roda pelo alvo próprio:
esta checagem reprova o commit até ele ser incluído.
"""

from qa_report.casos_teste import arquivos_da_suite

from observability.automacao import RAIZ


def test_todo_teste_de_tela_esta_na_suite_completa():
    na_suite = {arquivo.name for arquivo in arquivos_da_suite()}
    existentes = {
        arquivo.name for arquivo in (RAIZ / "tests" / "app").glob("test_*.py")
    }

    faltando = sorted(existentes - na_suite)

    assert not faltando, (
        f"Fora da APP_SUITE do Makefile (não rodam em make run/smoke/"
        f"regression nem nos merges): {', '.join(faltando)}. Crie a "
        "variável TEST_... e inclua na APP_SUITE, na ordem da jornada."
    )
