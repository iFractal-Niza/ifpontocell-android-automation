"""
Toque nas opções do menu do perfil (MenuPerfilPage): quando o app ignora
o toque e o menu continua aberto, o toque é repetido uma vez.
"""

from unittest.mock import Mock

import pytest

from pages.menu_page import MenuPerfilPage


def _menu(fecha_em: list[bool]) -> MenuPerfilPage:
    """Menu cujas esperas pelo fechamento respondem 'fecha_em', em ordem."""
    menu = MenuPerfilPage(Mock())
    menu.abrir_se_necessario = Mock()
    menu._rolar_ate_opcao = Mock(return_value=True)
    menu._click_with_fallback = Mock()
    menu._wait_for_absence = Mock(side_effect=fecha_em)
    menu._obter_elemento_visivel_imediatamente = Mock(return_value=Mock())
    menu._force_tap_element = Mock()
    return menu


def test_menu_fechou_no_primeiro_toque():
    menu = _menu([True])

    menu.acessar(MenuPerfilPage.PRIVACIDADE)

    menu._force_tap_element.assert_not_called()


def test_toque_ignorado_e_repetido_uma_vez():
    menu = _menu([False, True])

    menu.acessar(MenuPerfilPage.PRIVACIDADE)

    menu._force_tap_element.assert_called_once()


def test_dois_toques_ignorados_falham_com_mensagem_clara():
    menu = _menu([False, False])

    with pytest.raises(AssertionError, match="PRIVACIDADE duas vezes"):
        menu.acessar(MenuPerfilPage.PRIVACIDADE)


def test_opcao_que_mantem_o_menu_nao_e_conferida():
    # ZERAR DADOS abre um alerta e deixa o menu atrás.
    menu = _menu([])

    menu.acessar(MenuPerfilPage.ZERAR_DADOS)

    menu._wait_for_absence.assert_not_called()
    menu._force_tap_element.assert_not_called()
