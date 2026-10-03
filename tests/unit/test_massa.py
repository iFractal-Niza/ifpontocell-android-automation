"""
Proteção dos testes que consomem massa (tests.fixtures.massa).
"""

from unittest.mock import Mock

from tests.fixtures.massa import MARKER, pular_sem_opcao


def _item(marcado: bool) -> Mock:
    item = Mock()
    item.get_closest_marker.side_effect = lambda nome: (
        object() if marcado and nome == MARKER else None
    )
    return item


def test_sem_opcao_pula_so_os_que_consomem_massa():
    destrutivo, comum = _item(True), _item(False)

    pular_sem_opcao([destrutivo, comum], consumir_massa=False)

    destrutivo.add_marker.assert_called_once()
    comum.add_marker.assert_not_called()


def test_com_opcao_nao_pula_nada():
    destrutivo = _item(True)

    pular_sem_opcao([destrutivo], consumir_massa=True)

    destrutivo.add_marker.assert_not_called()
