"""
Digitação conferida (BasePage._type). O campo é um objeto falso que
simula o teclado descartando teclas (visto no iOS).
"""

from unittest.mock import Mock

import pytest

from pages.base_page import BasePage


class _Campo:
    """
    Campo de texto falso. 'digitados' é o que o campo realmente recebe
    em cada tentativa (permite simular tecla perdida).
    """

    def __init__(self, digitados: list[str]):
        self._digitados = iter(digitados)
        self.valor = ""
        self.tentativas = 0

    def click(self):
        pass

    def clear(self):
        self.valor = ""

    def send_keys(self, texto):
        self.tentativas += 1
        self.valor += next(self._digitados, texto)

    def get_attribute(self, nome):
        return self.valor if nome == "text" else None


@pytest.fixture
def pagina(monkeypatch):
    page = BasePage(driver=Mock())

    def com_campo(campo: _Campo) -> BasePage:
        monkeypatch.setattr(page, "_wait_for_clickable", lambda *a, **k: campo)
        return page

    return com_campo


def test_valor_certo_na_primeira_tentativa(pagina):
    campo = _Campo(["exemplo"])

    pagina(campo)._type(("id", "x"), "exemplo", field_name="sistema")

    assert campo.valor == "exemplo"
    assert campo.tentativas == 1


def test_tecla_perdida_e_redigitada(pagina):
    # Caso real: "exemplo" virou "exeplo" e o teste seguiu com o erro.
    campo = _Campo(["exeplo", "exemplo"])

    pagina(campo)._type(("id", "x"), "exemplo", field_name="sistema")

    assert campo.valor == "exemplo"
    assert campo.tentativas == 2


def test_falha_apos_todas_as_tentativas_mostra_esperado_e_obtido(pagina):
    campo = _Campo(["exeplo"] * BasePage.TYPE_ATTEMPTS)

    with pytest.raises(AssertionError, match="'exemplo'.*'exeplo'"):
        pagina(campo)._type(("id", "x"), "exemplo", field_name="sistema")

    assert campo.tentativas == BasePage.TYPE_ATTEMPTS


def test_campo_sensivel_nao_e_conferido(pagina):
    # O iOS devolve a senha mascarada: conferir geraria falso negativo.
    campo = _Campo(["••••"])

    pagina(campo)._type(
        ("id", "x"), "1234", field_name="senha", sensitive=True
    )

    assert campo.tentativas == 1


def test_senha_visivel_e_conferida_e_redigitada(pagina):
    # Com "mostrar senha", o campo expõe o texto: dá para conferir.
    campo = _Campo(["Senh123", "Senha123"])

    pagina(campo)._type(
        ("id", "x"),
        "Senha123",
        field_name="senha",
        sensitive=True,
        conferir=True,
    )

    assert campo.valor == "Senha123"
    assert campo.tentativas == 2


def test_senha_conferida_nao_aparece_na_mensagem_de_erro(pagina):
    campo = _Campo(["Senh123"] * BasePage.TYPE_ATTEMPTS)

    with pytest.raises(AssertionError) as erro:
        pagina(campo)._type(
            ("id", "x"),
            "Senha123",
            field_name="senha",
            sensitive=True,
            conferir=True,
        )

    assert "Senha123" not in str(erro.value)
    assert "Senh123" not in str(erro.value)
    assert "***" in str(erro.value)
