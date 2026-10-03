from pages.android_locators import android_text


class AlertaAppMixin:
    """
    Alertas do próprio app: título (em geral "ifPontoCell") + mensagem +
    botão OK, sem ids técnicos. Usado após salvar documento, assinar
    espelho, e onde mais o app confirmar uma ação com esse componente.

    Requer os métodos da BasePage. Declarar antes de BasePage nas bases.
    """

    TITULO_ALERTA_PADRAO = "ifPontoCell"

    # TODO: substituir por resource-id técnico quando disponível.
    ALERTA_BOTAO_OK = android_text("OK")

    @staticmethod
    def _texto_alerta(texto: str) -> tuple[str, str]:
        return android_text(texto)

    def alerta_visivel(self, mensagem: str, timeout: float) -> bool:
        return self._is_visible(self._texto_alerta(mensagem), timeout=timeout)

    def confirmar_alerta(
        self,
        mensagem: str,
        acao: str,
        titulo: str = TITULO_ALERTA_PADRAO,
    ) -> None:
        """
        Espera o alerta com a mensagem exata, toca OK e confere que
        fechou.

        Se aparecer outro alerta no lugar (ex.: erro), falha mostrando o
        texto dele, em vez de um timeout genérico. 'acao' descreve o que
        disparou o alerta, para a mensagem de erro.
        """
        if not self.alerta_visivel(mensagem, timeout=self.LONG_TIMEOUT):
            outro_alerta = self._obter_texto_desconhecido_do_alerta(
                self._texto_alerta(titulo),
                self.ALERTA_BOTAO_OK,
                {mensagem, titulo},
            )

            raise AssertionError(
                f"O alerta {mensagem!r} não apareceu após {acao}. "
                + (
                    f"O app exibiu outro alerta: {outro_alerta!r}."
                    if outro_alerta
                    else "Nenhum alerta do app foi exibido."
                )
            )

        self._click(
            self.ALERTA_BOTAO_OK,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_ok_alerta",
        )

        assert self._wait_for_absence(
            self._texto_alerta(mensagem),
            timeout=self.DEFAULT_TIMEOUT,
        ), f"O alerta {mensagem!r} não fechou após o OK."

        self._log_info(
            "Alerta do app confirmado",
            event="app_alert_confirmed",
            mensagem=mensagem,
        )
