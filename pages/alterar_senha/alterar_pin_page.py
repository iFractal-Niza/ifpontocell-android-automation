from functools import cached_property
from time import monotonic, sleep

from pages.alterar_senha.alterar_senha_base_page import AlterarSenhaBasePage
from pages.android_locators import android_id, android_text_contains
from pages.autenticacao.unlock_page import UnlockPage
from pages.home_page import HomePage


class AlterarPinPage(AlterarSenhaBasePage):
    """
    Page: aba SENHA 4 DÍGITOS (o PIN de acesso rápido) da tela "Alterar
    Senha" (menu do perfil -> ALTERAR SENHA). O comum às duas abas fica
    em AlterarSenhaBasePage.

    Fluxo: "Digite a senha atual" -> PIN atual -> "Crie uma senha de 4
    dígitos..." -> novo PIN -> "Repita a senha de 4 dígitos" -> novo PIN.
    Depois da senha atual, é o mesmo fluxo da criação de PIN do primeiro
    acesso (UnlockPage): mesmos textos e o mesmo teclado.
    """

    SCREEN_NAME = "alterar_pin"
    ABA = "SENHA 4 DÍGITOS"

    # Confirmado no Inspector: a aba usa a mesma tela de PIN do primeiro
    # acesso (relative_first_access, text_titulo "Alterar Senha",
    # text_instrucao, teclado numberN). No iOS, alterarSenha.lblInstrucao.
    INSTRUCAO = android_id("text_instrucao")

    TEXTO_SENHA_ATUAL = "Digite a senha atual"

    # Repetição divergente da nova senha: a instrução vira "Confirmação
    # de senha não conferem / Favor tentar novamente" e fica assim,
    # esperando o PIN (diferente do primeiro acesso, que volta a "Crie
    # uma senha..."). Confirmado no print da falha.
    AVISO_TENTAR_NOVAMENTE = android_text_contains(
        "Confirmação de senha não conferem"
    )

    # === Composição ===
    @cached_property
    def teclado(self) -> UnlockPage:
        """O teclado de PIN e as telas de criar/repetir do UnlockPage."""
        return UnlockPage(self.driver)

    # === Acesso ===
    def acessar(self) -> None:
        self._abrir_tela_na_aba()

        assert self.pedindo_senha_atual(timeout=self.DEFAULT_TIMEOUT), (
            "A aba SENHA 4 DÍGITOS não pediu a senha atual."
        )

    def pedindo_senha_atual(self, timeout: float | None = None) -> bool:
        return self._is_visible(
            android_text_contains(self.TEXTO_SENHA_ATUAL),
            timeout=timeout,
        )

    # === Senha atual ===
    def informar_senha_atual(self, atual: str) -> None:
        """PIN atual até a tela de criar a nova senha aparecer."""
        self.teclado.digitar_pin_ate(
            atual,
            etapa="senha_atual",
            transicao_concluida=lambda: self._esta_visivel_imediatamente(
                UnlockPage.TEXTO_CRIAR_PIN
            ),
            mensagem_erro=(
                "A senha atual não foi aceita: a tela de criar a nova senha "
                "não apareceu. Confira o PIN atual usado no teste."
            ),
        )

    def senha_atual_foi_recusada(self, pin_errado: str) -> bool:
        """
        Digita um PIN errado como senha atual e diz se a tela continuou
        pedindo a senha atual (sem ir para a criação da nova).
        """
        self.teclado.digitar_pin(pin_errado)
        sleep(UnlockPage.PIN_TRANSITION_TIMEOUT)

        return self.pedindo_senha_atual(
            timeout=self.SHORT_TIMEOUT
        ) and not self._esta_visivel_imediatamente(UnlockPage.TEXTO_CRIAR_PIN)

    def repeticao_divergente_recusada(self, timeout: float) -> bool:
        """
        Depois de repetir um PIN diferente do novo: o app avisa para
        tentar novamente (ou volta à criação da nova senha).
        """
        limite = monotonic() + timeout

        while monotonic() < limite:
            if self._esta_visivel_imediatamente(
                self.AVISO_TENTAR_NOVAMENTE
            ) or self._esta_visivel_imediatamente(UnlockPage.TEXTO_CRIAR_PIN):
                return True

            sleep(self.POLL_FREQUENCY)

        return False

    def aguardar_pedido_de_pin(self, timeout: float) -> str | None:
        """
        Espera a tela voltar a pedir um PIN (por exemplo, depois do
        aviso de repetição divergente): "senha_atual" ou "nova_senha".
        None se nenhum dos dois aparecer no tempo.
        """
        limite = monotonic() + timeout

        while monotonic() < limite:
            if self.pedindo_senha_atual(timeout=0):
                return "senha_atual"

            if self._pedindo_nova_senha():
                return "nova_senha"

            sleep(self.POLL_FREQUENCY)

        return None

    def _pedindo_nova_senha(self) -> bool:
        """Na criação da nova senha, ou no aviso de repetição divergente."""
        return self._esta_visivel_imediatamente(
            UnlockPage.TEXTO_CRIAR_PIN
        ) or self._esta_visivel_imediatamente(self.AVISO_TENTAR_NOVAMENTE)

    def _informar_nova_senha(self, novo: str) -> None:
        """
        Novo PIN e repetição. Depois do aviso de repetição divergente, o
        app pode pedir para criar de novo (vem "Repita a senha...") ou só
        a repetição (o aviso some e a troca termina): cobre os dois.
        """
        if not self._esta_visivel_imediatamente(self.AVISO_TENTAR_NOVAMENTE):
            self.teclado.criar_pin(novo)
            self.teclado.confirmar_pin(novo)
            return

        self.teclado.digitar_pin_ate(
            novo,
            etapa="nova_senha_apos_divergencia",
            transicao_concluida=lambda: (
                self._esta_visivel_imediatamente(
                    UnlockPage.TEXTO_CONFIRMAR_PIN
                )
                or not self._esta_visivel_imediatamente(
                    self.AVISO_TENTAR_NOVAMENTE
                )
            ),
            mensagem_erro=(
                "Depois do aviso de repetição divergente, o novo PIN não "
                "foi aceito."
            ),
        )

        if self._esta_visivel_imediatamente(UnlockPage.TEXTO_CONFIRMAR_PIN):
            self.teclado.confirmar_pin(novo)

    # === Alteração ===
    def alterar_pin(self, atual: str, novo: str) -> None:
        """
        Senha atual -> novo PIN -> repetição do novo PIN -> conclusão
        (alerta com OK, se houver, e volta à Home).

        Se a tela já estiver pedindo a nova senha (a senha atual foi
        aceita antes, como no encadeamento após a repetição divergente),
        começa dali.
        """
        if not self._pedindo_nova_senha():
            self.informar_senha_atual(atual)

        self._informar_nova_senha(novo)

        self._concluir_alteracao()

        self._log_info(
            "PIN alterado",
            event="pin_changed",
        )

    def _concluir_alteracao(self) -> None:
        """
        Depois de repetir o novo PIN: confirma o alerta do app, se
        aparecer, e garante a volta à Home (voltando da tela, se o app
        continuar nela).
        """
        limite = monotonic() + self.LONG_TIMEOUT
        home = HomePage(self.driver)

        while monotonic() < limite:
            if self._esta_visivel_imediatamente(self.ALERTA_BOTAO_OK):
                mensagem = self._obter_texto_desconhecido_do_alerta(
                    self._texto_alerta(self.TITULO_ALERTA_PADRAO),
                    self.ALERTA_BOTAO_OK,
                    {self.TITULO_ALERTA_PADRAO},
                )
                self._log_info(
                    "Alerta ao concluir a alteração do PIN",
                    event="pin_change_alert",
                    mensagem=mensagem,
                )
                self._click(
                    self.ALERTA_BOTAO_OK,
                    timeout=self.DEFAULT_TIMEOUT,
                    element_name="botao_ok_alteracao_pin",
                )
                continue

            if self._esta_visivel_imediatamente(self.TITULO):
                self.voltar_para_home()
                return

            if home.esta_na_home(timeout=0):
                return

            sleep(self.POLL_FREQUENCY)

        assert home.esta_na_home(timeout=home.LONG_TIMEOUT), (
            "Depois de repetir o novo PIN, o app não voltou à Home nem "
            "ficou na tela Alterar Senha."
        )
