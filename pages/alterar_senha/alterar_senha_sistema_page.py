import re
from time import monotonic, sleep

from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
)

from pages.alterar_senha.alterar_senha_base_page import AlterarSenhaBasePage
from pages.android_locators import android_pendente, android_text_matches
from utils.texto import normalizar_texto


class AlterarSenhaSistemaPage(AlterarSenhaBasePage):
    """
    Page: aba SENHA SISTEMA (a senha de login no sistema, no servidor) da
    tela "Alterar Senha" (menu do perfil -> ALTERAR SENHA).

    Campos senha atual, nova senha e confirmação, com ids técnicos. Regras
    da nova senha (maiúscula, minúscula e número) avisadas ao vivo abaixo
    dos campos ("Faltam: ..."). A resposta ao SALVAR vem num alerta do
    app (título "ifPontoCell" + OK).

    Ao abrir a aba, liga o "mostrar senha" dos três campos (ambiente de
    homologação): com a senha visível, a digitação confere o valor e
    redigita se o simulador perder uma tecla. O valor continua oculto no
    log; os prints do report mostram a senha.
    """

    SCREEN_NAME = "alterar_senha_sistema"
    ABA = "SENHA SISTEMA"

    # PENDENTE: ids da aba no Android (iOS: alterarSenhaSistema.*).
    CAMPO_SENHA_ATUAL = android_pendente("alterarSenhaSistema_campoSenhaAtual")
    CAMPO_NOVA_SENHA = android_pendente("alterarSenhaSistema_campoNovaSenha")
    CAMPO_CONFIRMAR_SENHA = android_pendente(
        "alterarSenhaSistema_campoConfirmarSenha"
    )
    ERRO_NOVA_SENHA = android_pendente("alterarSenhaSistema_lblErroNovaSenha")
    ERRO_CONFIRMAR_SENHA = android_pendente(
        "alterarSenhaSistema_lblErroConfirmarSenha"
    )
    BOTAO_SALVAR = android_pendente("alterarSenhaSistema_btnSalvar")

    # Campo -> botão "mostrar ou ocultar senha".
    BOTOES_MOSTRAR_SENHA = {
        CAMPO_SENHA_ATUAL: android_pendente(
            "alterarSenhaSistema_btnVerSenhaAtual"
        ),
        CAMPO_NOVA_SENHA: android_pendente(
            "alterarSenhaSistema_btnVerNovaSenha"
        ),
        CAMPO_CONFIRMAR_SENHA: android_pendente(
            "alterarSenhaSistema_btnVerConfirmarSenha"
        ),
    }

    MENSAGEM_NOVA_IGUAL_A_ATUAL = (
        "A senha atual não pode ser igual a anterior."
    )

    # Troca aceita: alerta de sucesso e, após o OK, o app volta à Home.
    MENSAGEM_SUCESSO = "Senha alterada com sucesso."

    # Confirmação diferente da nova: o app empilha dois alertas ("Senha
    # não confere." e "Confirmação de senha não conferem / Favor tentar
    # novamente"), cada um com o seu OK.
    TRECHO_NAO_CONFERE = "confere"

    # === Acesso ===
    def acessar(self) -> None:
        self._abrir_tela_na_aba()

        assert self._is_visible(
            self.CAMPO_SENHA_ATUAL, timeout=self.DEFAULT_TIMEOUT
        ), "A aba SENHA SISTEMA não exibiu o campo da senha atual."

        self.mostrar_senhas()

    def mostrar_senhas(self) -> None:
        """Liga o "mostrar senha" dos campos que estiverem ocultos."""
        for campo, botao in self.BOTOES_MOSTRAR_SENHA.items():
            # No iOS, o tipo XCUIElementTypeSecureTextField; no Android,
            # o atributo password do EditText.
            oculto = self._find(
                campo, element_name="campo_senha"
            ).get_attribute("password")

            if oculto == "true":
                self._click(
                    botao,
                    timeout=self.DEFAULT_TIMEOUT,
                    element_name="botao_mostrar_senha",
                )

    # === Preenchimento ===
    def _preencher_campo(self, locator, texto: str, nome: str) -> None:
        # Senha visível: confere o valor digitado, mas não o loga.
        self._type(
            locator, texto, field_name=nome, sensitive=True, conferir=True
        )

    def preencher(self, atual: str, nova: str, confirmacao: str) -> None:
        """Preenche os três campos."""
        self._preencher_campo(
            self.CAMPO_SENHA_ATUAL, atual, "campo_senha_atual"
        )
        self.preencher_nova(nova, confirmacao)

    def preencher_nova(self, nova: str, confirmacao: str) -> None:
        """
        Só a nova senha e a confirmação: a senha atual já está preenchida
        (continuação do teste anterior na mesma aba).
        """
        self._preencher_campo(self.CAMPO_NOVA_SENHA, nova, "campo_nova_senha")
        self._preencher_campo(
            self.CAMPO_CONFIRMAR_SENHA, confirmacao, "campo_confirmar_senha"
        )

    def salvar(self) -> None:
        self._click(
            self.BOTAO_SALVAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_salvar_senha_sistema",
        )

    def salvar_esperando_alerta(self, mensagem: str, acao: str) -> None:
        """SALVAR e confirma (OK) o alerta com a mensagem esperada."""
        self.salvar()
        self.confirmar_alerta(mensagem, acao=acao)

    def fechar_alertas_contendo(self, trecho: str) -> list[str]:
        """
        Fecha, um a um, os alertas do app empilhados (o OK de cima é o
        último na árvore) e devolve as mensagens que contêm o trecho, na
        ordem em que foram vistas. Para quando não sobrar alerta.
        """
        mensagens: list[str] = []
        # Sem distinguir caixa, como o CONTAINS[c] do iOS.
        textos = android_text_matches(f"(?is).*{re.escape(trecho)}.*")
        limite = monotonic() + self.LONG_TIMEOUT

        while monotonic() < limite:
            try:
                botoes_ok = self.driver.find_elements(*self.ALERTA_BOTAO_OK)

                if not botoes_ok:
                    if mensagens:
                        break

                    sleep(self.POLL_FREQUENCY)
                    continue

                for elemento in self.driver.find_elements(*textos):
                    mensagem = normalizar_texto(elemento.text)

                    if mensagem not in mensagens:
                        mensagens.append(mensagem)

                botoes_ok[-1].click()
                sleep(self.POLL_FREQUENCY)
            except (StaleElementReferenceException, WebDriverException):
                sleep(self.POLL_FREQUENCY)

        self._log_info(
            "Alertas fechados após SALVAR",
            event="system_password_alerts_closed",
            mensagens=mensagens,
        )

        return mensagens

    def trocar_senha(self, atual: str, nova: str) -> list[str]:
        """
        Preenche atual/nova/confirmação, salva e fecha os alertas,
        devolvendo as mensagens (para quem precisa decidir pelo resultado,
        como a restauração). Trocou se MENSAGEM_SUCESSO estiver nelas.
        """
        self.preencher(atual, nova, nova)
        self.salvar()

        return self.fechar_alertas_contendo("senha")

    def esta_aberta(self, timeout: float | None = None) -> bool:
        return self._is_visible(self.CAMPO_SENHA_ATUAL, timeout=timeout)
