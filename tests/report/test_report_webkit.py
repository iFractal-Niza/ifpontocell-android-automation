"""
O report no WebKit, o motor do Safari: o que depende do navegador
guardar dados com o report aberto como arquivo local (localStorage e
IndexedDB) e baixar a cópia.
"""

import base64

from tests.report.conftest import _PNG


def test_anexo_fica_ao_recarregar_e_vai_na_copia(
    abrir_no_webkit, report_padrao, tmp_path
):
    pagina = abrir_no_webkit(report_padrao)
    linha = pagina.adicionar(ct="CT900", status="Falhou")
    arquivo = tmp_path / "tela.png"
    arquivo.write_bytes(base64.b64decode(_PNG))

    with pagina.page.expect_file_chooser() as escolha:
        linha.locator(".qa-evidencia-anexar").click()
    escolha.value.set_files(str(arquivo))
    pagina.page.wait_for_selector(".qa-evidencia-abrir")

    pagina.recarregar()
    assert pagina.page.locator(".qa-evidencia-abrir").count() == 1

    with pagina.page.expect_download() as download:
        pagina.page.click("[data-qa-baixar]")
    copia_html = tmp_path / download.value.suggested_filename
    download.value.save_as(copia_html)

    copia = abrir_no_webkit(copia_html).page
    copia.locator(".qa-evidencia-abrir").click()

    assert copia.locator(".qa-lightbox img").count() == 1
    assert copia.locator(".qa-bloco-manuais .qa-test-title").inner_text() == (
        "CT900"
    )
