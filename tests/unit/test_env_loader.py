"""
Carga do env.<device>.yaml (config.env_loader.carregar_env).
"""

import pytest

from config.env_loader import (
    PROJECT_ROOT,
    carregar_env,
    ler_yaml,
    resolver_env_file,
)
from config.settings import ConfiguracaoInvalida


def _carregar(ambiente, tmp_path, conteudo: str) -> None:
    arquivo = tmp_path / "env.yaml"
    arquivo.write_text(conteudo, encoding="utf-8")
    ambiente["IFPONTO_ENV_FILE"] = str(arquivo)

    assert carregar_env() is True


def test_valores_viram_string(ambiente, tmp_path):
    _carregar(
        ambiente,
        tmp_path,
        'ANDROID_TARGET: "emulator"\nANDROID_NEW_COMMAND_TIMEOUT: 120\n',
    )

    assert ambiente["ANDROID_TARGET"] == "emulator"
    assert ambiente["ANDROID_NEW_COMMAND_TIMEOUT"] == "120"


def test_booleano_sem_aspas_vira_true_capitalizado(ambiente, tmp_path):
    # Documenta o comportamento: YAML converte true em bool e str()
    # gera "True". Os leitores de booleano fazem .lower() antes.
    _carregar(ambiente, tmp_path, "ANDROID_NO_RESET: true\n")

    assert ambiente["ANDROID_NO_RESET"] == "True"


def test_chave_sem_valor_vira_string_vazia(ambiente, tmp_path):
    # Antes virava "None", que passava como valor preenchido.
    _carregar(ambiente, tmp_path, "ANDROID_UDID:\n")

    assert ambiente["ANDROID_UDID"] == ""


def test_variavel_do_shell_tem_precedencia(ambiente, tmp_path):
    ambiente["ANDROID_LOCATION_ENABLED"] = "true"

    _carregar(ambiente, tmp_path, 'ANDROID_LOCATION_ENABLED: "false"\n')

    assert ambiente["ANDROID_LOCATION_ENABLED"] == "true"


def test_arquivo_inexistente_nao_levanta(ambiente, tmp_path):
    ambiente["IFPONTO_ENV_FILE"] = str(tmp_path / "nao_existe.yaml")

    assert carregar_env() is False
    assert "ANDROID_TARGET" not in ambiente


def test_arquivo_vazio_nao_levanta(ambiente, tmp_path):
    arquivo = tmp_path / "env.yaml"
    arquivo.write_text("", encoding="utf-8")
    ambiente["IFPONTO_ENV_FILE"] = str(arquivo)

    assert carregar_env() is False
    assert "ANDROID_TARGET" not in ambiente


def test_resolver_env_file_padrao_e_o_do_emulador(ambiente):
    assert resolver_env_file() == PROJECT_ROOT / "config" / "env.emulator.yaml"


def test_chave_repetida_e_recusada_com_as_linhas(ambiente, tmp_path):
    arquivo = tmp_path / "env.yaml"
    arquivo.write_text(
        'ANDROID_LOCATION_ENABLED: "true"\n'
        'ANDROID_TARGET: "emulator"\n'
        'ANDROID_LOCATION_ENABLED: "false"\n',
        encoding="utf-8",
    )
    ambiente["IFPONTO_ENV_FILE"] = str(arquivo)

    with pytest.raises(ConfiguracaoInvalida) as erro:
        carregar_env()

    assert erro.value.erros == [
        "ANDROID_LOCATION_ENABLED aparece mais de uma vez (linhas 1 e 3); "
        "apague uma: senão vale a última, em silêncio."
    ]
    assert "ANDROID_LOCATION_ENABLED" not in ambiente


def test_lista_todas_as_chaves_repetidas(tmp_path):
    arquivo = tmp_path / "env.yaml"
    arquivo.write_text("A: 1\nB: 2\nA: 3\nB: 4\n", encoding="utf-8")

    with pytest.raises(ConfiguracaoInvalida) as erro:
        ler_yaml(arquivo)

    assert len(erro.value.erros) == 2


def _examples():
    return sorted((PROJECT_ROOT / "config").glob("env.*.example.yaml"))


def test_examples_nao_tem_chave_repetida():
    # Trava: o template já teve APP_PASSWORD_NOVA duas vezes.
    assert len(_examples()) >= 2

    for exemplo in _examples():
        assert ler_yaml(exemplo), exemplo.name


def test_examples_tem_as_mesmas_chaves():
    # Chave nova (usuário, API, geo...) tem de entrar nos dois: emulador
    # e celular usam a mesma seção Android (só os valores mudam).
    chaves = {exemplo.name: set(ler_yaml(exemplo)) for exemplo in _examples()}
    emulador = chaves["env.emulator.example.yaml"]

    for nome, encontradas in chaves.items():
        assert encontradas == emulador, nome


def test_examples_apontam_para_o_seu_aparelho():
    config = PROJECT_ROOT / "config"
    emulador = ler_yaml(config / "env.emulator.example.yaml")
    real = ler_yaml(config / "env.real.example.yaml")

    assert emulador["ANDROID_TARGET"] == "emulator"
    assert real["ANDROID_TARGET"] == "real"


def test_examples_tem_system_port_diferentes():
    # Emulador e celular no mesmo Appium derrubam a sessão um do outro
    # com a mesma porta do UiAutomator2.
    config = PROJECT_ROOT / "config"
    emulador = ler_yaml(config / "env.emulator.example.yaml")
    real = ler_yaml(config / "env.real.example.yaml")

    assert emulador["ANDROID_SYSTEM_PORT"] != real["ANDROID_SYSTEM_PORT"]
