import re
from datetime import datetime
from time import monotonic, sleep

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.timeouts import (
    FLOW_TIMEOUT,
    OPTIONAL_POPUP_TIMEOUT,
)
from pages.android_locators import (
    android_description,
    android_id,
    android_text,
    android_text_contains,
)
from pages.base_page import BasePage


class HomePage(BasePage):
    SCREEN_NAME = "home"

    OPTIONAL_POPUP_TIMEOUT = OPTIONAL_POPUP_TIMEOUT

    POPUP_POLL_INTERVAL = 0.2

    # Mantém uma pequena janela de estabilidade antes de considerar
    # a Home definitivamente livre: um popup pode surgir logo após o
    # fechamento de outro modal. No iOS caiu para 1,5s porque "Opinião"
    # e o alerta de atualização são suprimidos por launch argument; no
    # Android não há equivalente (ver DECISOES.md, "Popups oportunistas"),
    # então eles ainda podem aparecer e a janela continua em 4s.
    HOME_STABILITY_TIMEOUT = 4.0

    # FLOW_TIMEOUT (8s) é curto demais para loops que podem precisar
    # resolver popups encadeados (Opinião -> Melhoria) antes de
    # clicar no alvo: cada um consome tempo (clicar + aguardar
    # fechar) antes do próximo aparecer.
    POPUP_RESOLUTION_TIMEOUT = 20.0

    # === Home Android (locators confirmados no projeto de referência) ===
    BOTAO_ABRIR_MENU = android_id("menu_esquerdo")
    MARCADOR_HOME = android_id("linearPonto")
    ABA_PONTO = android_id("ponto")
    ABA_PONTO_FALLBACK = android_text("PONTO")
    BOTAO_REGISTRAR = android_id("bt_init")
    # O texto do botão é a hora corrente ("00:56:38"); "Registrar" está
    # no content-desc (confirmado no Inspector).
    BOTAO_REGISTRAR_FALLBACK = android_description("Registrar")
    BOTAO_ABRIR_TOTALIZADOR = android_id("abrirFecharTotalizador")
    BOTAO_DIA_ANTERIOR = android_id("carregarDadosMenos")
    BOTAO_PROXIMO_DIA = android_id("carregarDadosMais")

    # === Popup de lembrete (confirmado no Inspector) ===
    # Diálogo genérico do app: mensagem no id "mensagem", DEPOIS no
    # btnEsquerdo e ATIVAR no btnDireito. Os botões ficam pelo texto: os
    # ids são genéricos (OK dos erros, SIM/NÃO da confirmação do ponto),
    # e ATIVAR é o que identifica este popup.
    POPUP_LEMBRETE_MENSAGEM = android_text_contains(
        "oferece lembretes para suas marcações de ponto"
    )
    BOTAO_LEMBRETE_ATIVAR = android_text("ATIVAR")
    BOTAO_LEMBRETE_DEPOIS = android_text("DEPOIS")

    # === Demais popups ===
    # Sem resource-id no projeto de referência; por texto até
    # confirmação no Appium Inspector.
    POPUP_OPINIAO_TITULO = android_text("Opinião")
    POPUP_OPINIAO_BOTAO_NAO = android_text("NÃO")
    POPUP_ATUALIZACAO_ALERTA = android_text_contains("Tem novidade pra você")
    POPUP_ATUALIZACAO_MENSAGEM = POPUP_ATUALIZACAO_ALERTA
    POPUP_ATUALIZACAO_BOTAO_CANCELAR = android_text("Cancelar")
    POPUP_MELHORIA_TITULO = android_text_contains("O que podemos melhorar")
    POPUP_MELHORIA_BOTAO_DEPOIS = android_text("DEPOIS")

    # === Popup de espelho pendente ===
    # Aparece ao abrir o app enquanto houver espelho de ponto pendente de
    # assinatura (DEPOIS / ASSINAR). Identificado pelo título, que é fixo
    # (a mensagem muda com a quantidade de espelhos). Como no iOS, o
    # DEPOIS tem o mesmo texto dos popups de lembrete e melhoria.
    # TODO: provisório por texto; confirmar no Inspector
    # (PENDENCIAS_LOCATORS_ANDROID.md).
    POPUP_ESPELHO_PENDENTE_MENSAGEM = android_text("Assinatura do espelho")
    POPUP_ESPELHO_PENDENTE_BOTAO_DEPOIS = android_text("DEPOIS")
    POPUP_ESPELHO_PENDENTE_BOTAO_ASSINAR = android_text("ASSINAR")

    # === Aviso de fora da geo delimitação ===
    # Aparece depois do SIM da confirmação do registro, com a localização
    # fora da área cadastrada. NÃO volta à Home sem registrar; SIM segue
    # com o registro.
    # TODO: provisório por texto; confirmar no Inspector
    # (PENDENCIAS_LOCATORS_ANDROID.md).
    POPUP_FORA_GEO_MENSAGEM = android_text_contains(
        "Você está fora da geo localização"
    )
    POPUP_FORA_GEO_BOTAO_NAO = android_text("NÃO")
    POPUP_FORA_GEO_BOTAO_SIM = android_text("SIM")

    # === Registro de ponto Android ===
    CONFIRMACAO_PONTO_TITULO = android_id(
        "linear_dialog_geral", "relativeDialogPopUp"
    )
    CONFIRMACAO_PONTO_BOTAO_NAO = android_id("btnEsquerdo")
    CONFIRMACAO_PONTO_BOTAO_SIM = android_id("btnDireito")
    CENTRO_CUSTO = android_id("linearCentroCusto")
    SWITCH_CENTRO_CUSTO = android_id("switchCentroCusto")
    BOTAO_CONFIRMAR_GENERICO = android_id("btn_confirmar")
    BOTAO_TIRAR_FOTO = android_id("tirarFoto")
    BOTAO_CONFIRMAR_SEM_FOTO = android_id("btn_confirmar_sem_foto")
    MENSAGEM_PONTO_REGISTRADO_SUCESSO = android_id("mensagemCamera")
    DATA_HORA_REGISTRO = android_id("textViewRegistroEfetuadoHora")

    PERMISSAO_ANDROID = android_id(
        "com.android.permissioncontroller:id/permission_allow_button",
        "com.android.permissioncontroller:id/permission_allow_foreground_only_button",
        "com.android.permissioncontroller:id/permission_allow_one_time_button",
        "com.android.packageinstaller:id/permission_allow_button",
    )

    REGEX_DATA_HORA_REGISTRO = re.compile(
        r"Dia (\d{2}/\d{2}/\d{4}) às (\d{2}:\d{2}(?::\d{2})?)"
    )
    REGEX_HORA_REGISTRO = re.compile(r"(\d{2}:\d{2}(?::\d{2})?)")

    # === Helpers imediatos ===
    # _obter_elemento_visivel_imediatamente e _esta_visivel_imediatamente
    # vêm de BasePage.

    def _clicar_com_nova_referencia(
        self,
        locator: tuple[str, str],
        element_name: str,
        timeout: float,
    ) -> None:
        """
        Localiza e clica usando uma referência nova em cada tentativa.

        Evita StaleElementReferenceException em componentes cuja árvore
        é recriada durante animações ou atualizações de estado.
        """
        ultimo_erro: Exception | None = None

        def clicar_elemento_atualizado(_):
            nonlocal ultimo_erro

            try:
                elemento = self.driver.find_element(*locator)

                if not elemento.is_displayed() or not elemento.is_enabled():
                    return False

                elemento.click()
                return True

            except (
                StaleElementReferenceException,
                WebDriverException,
            ) as error:
                ultimo_erro = error
                return False

        try:
            WebDriverWait(
                self.driver,
                timeout,
                poll_frequency=self.POPUP_POLL_INTERVAL,
                ignored_exceptions=(StaleElementReferenceException,),
            ).until(
                clicar_elemento_atualizado,
                message=(
                    f"{element_name} não ficou disponível "
                    f"para clique em {timeout}s. "
                    f"Locator: {locator}"
                ),
            )

        except TimeoutException as error:
            raise TimeoutException(
                f"{element_name} não ficou disponível "
                f"para clique em {timeout}s. "
                f"Locator: {locator}. "
                f"Último erro: {ultimo_erro}"
            ) from error

        self._log_info(
            "Elemento acionado com referência atualizada",
            event="fresh_element_clicked",
            element=element_name,
        )

    def _home_esta_pronta_imediatamente(self) -> bool:
        """
        Reconhece a Home por locators técnicos ou visuais.

        O botão Registrar pode estar disponível apenas pelo label
        durante a reconstrução inicial da árvore do UiAutomator2.

        A aba PONTO não entra: a barra de abas aparece também em outras
        telas (ex.: lista da Assinatura do Espelho), e a Home era dada
        como aberta fora dela.
        """
        if self._esta_visivel_imediatamente(
            self.POPUP_ATUALIZACAO_ALERTA,
        ):
            return False

        return any(
            self._esta_visivel_imediatamente(locator)
            for locator in (
                self.BOTAO_REGISTRAR,
                self.BOTAO_REGISTRAR_FALLBACK,
                self.BOTAO_ABRIR_MENU,
                self.MARCADOR_HOME,
                self.BOTAO_ABRIR_TOTALIZADOR,
                self.BOTAO_DIA_ANTERIOR,
                self.BOTAO_PROXIMO_DIA,
            )
        )

    def aguardar_primeiro_acesso_pronto(self) -> None:
        """
        Aguarda a Home ou o popup de lembrete do primeiro acesso.
        """
        WebDriverWait(
            self.driver,
            FLOW_TIMEOUT,
            poll_frequency=self.POPUP_POLL_INTERVAL,
        ).until(
            lambda _: (
                self._home_esta_pronta_imediatamente()
                or self._esta_visivel_imediatamente(
                    self.BOTAO_LEMBRETE_ATIVAR,
                )
            ),
            message=(
                "A Home ou o popup de lembrete não foram reconhecidos "
                f"em {FLOW_TIMEOUT}s. A tela pode estar carregada, mas "
                "sem expor nenhum dos locators usados como referência."
            ),
        )

    # === Popup de lembrete ===
    def popup_lembrete_esta_visivel(
        self,
        timeout: float | None = None,
    ) -> bool:
        timeout_resolvido = (
            self.OPTIONAL_POPUP_TIMEOUT if timeout is None else timeout
        )

        is_visible = self._is_visible(
            self.BOTAO_LEMBRETE_ATIVAR,
            timeout=timeout_resolvido,
        )

        if not is_visible:
            is_visible = self._esta_visivel_imediatamente(
                self.POPUP_LEMBRETE_MENSAGEM,
            )

        self._log_info(
            "Verificação do popup de lembrete executada",
            event="reminder_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def clicar_depois_popup_lembrete(self) -> None:
        """
        Recusa o lembrete. Levanta quando o botão não fica disponível.

        Use apenas quando o popup é o objeto sob teste. Em trechos de
        fluxo onde o popup é opcional, use
        tratar_popup_lembrete_se_existir().
        """
        self._click(
            self.BOTAO_LEMBRETE_DEPOIS,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_depois_popup_lembrete",
        )

    def clicar_ativar_popup_lembrete(
        self,
        timeout: float | None = None,
    ) -> bool:
        """
        Tenta ativar o lembrete em uma única operação atômica.

        Retorna False quando o popup já desapareceu e a Home está
        disponível. A validação definitiva permanece sendo o estado
        do switch nos Ajustes do Aplicativo.
        """
        timeout_resolvido = (
            self.DEFAULT_TIMEOUT if timeout is None else timeout
        )

        try:
            self._clicar_com_nova_referencia(
                self.BOTAO_LEMBRETE_ATIVAR,
                element_name="botao_ativar_popup_lembrete",
                timeout=timeout_resolvido,
            )

        except TimeoutException:
            if self._home_esta_pronta_imediatamente():
                self._log_warning(
                    "Botão ATIVAR não estava mais disponível; "
                    "a Home já estava carregada",
                    event="reminder_popup_no_longer_available",
                )
                return False

            raise

        popup_fechou = self._wait_for_absence(
            self.BOTAO_LEMBRETE_ATIVAR,
            timeout=self.SHORT_TIMEOUT,
        )

        if not popup_fechou:
            self._log_warning(
                "Popup de lembrete permaneceu visível após selecionar ATIVAR",
                event="reminder_popup_still_visible_after_enable",
            )

        self._log_info(
            "Lembrete ativado pelo popup do primeiro acesso",
            event="reminder_popup_enabled",
        )

        return True

    def tratar_popup_lembrete_se_existir(
        self,
        ativar: bool = False,
    ) -> bool:
        if not self.popup_lembrete_esta_visivel():
            return False

        if ativar:
            self.clicar_ativar_popup_lembrete()
            return True

        tocou = self._dismiss_if_present(
            self.BOTAO_LEMBRETE_DEPOIS,
            timeout=self.SHORT_TIMEOUT,
            element_name="botao_depois_popup_lembrete",
        )

        if not tocou:
            return False

        # Sem esperar a saída do modal, o próximo toque por
        # coordenada cai no popup ainda em animação.
        fechou = self._wait_for_absence(
            self.BOTAO_LEMBRETE_ATIVAR,
            timeout=self.SHORT_TIMEOUT,
        )

        if not fechou:
            self._log_warning(
                "Popup de lembrete permaneceu visível após o toque",
                event="reminder_popup_still_visible",
            )

        return fechou

    # === Popup de opinião ===
    def popup_opiniao_esta_visivel(self) -> bool:
        """
        Verifica o título exclusivo do popup de opinião.

        O botão "NÃO" não é utilizado isoladamente para detectar
        o popup, pois também existe em outros fluxos do aplicativo.
        """
        is_visible = self._esta_visivel_imediatamente(
            self.POPUP_OPINIAO_TITULO,
        )

        self._log_info(
            "Verificação do popup de opinião executada",
            event="opinion_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def tratar_popup_opiniao_se_existir(self) -> bool:
        """
        Dispensa o popup opcional de opinião selecionando "NÃO".

        Após o clique, aguarda o fechamento do modal para impedir
        que a próxima ação seja enviada enquanto a animação ainda
        estiver bloqueando a Home.
        """
        if not self.popup_opiniao_esta_visivel():
            return False

        tocou = self._dismiss_if_present(
            self.POPUP_OPINIAO_BOTAO_NAO,
            timeout=self.SHORT_TIMEOUT,
            element_name="botao_nao_popup_opiniao",
        )

        if not tocou:
            return False

        fechou = self._wait_for_absence(
            self.POPUP_OPINIAO_TITULO,
            timeout=self.SHORT_TIMEOUT,
        )

        if not fechou:
            self._log_warning(
                "Popup de opinião permaneceu visível após selecionar 'NÃO'",
                event="opinion_popup_still_visible",
            )

        return True

    # === Popup de melhoria ===
    def popup_melhoria_esta_visivel(self) -> bool:
        is_visible = self._esta_visivel_imediatamente(
            self.POPUP_MELHORIA_TITULO,
        )

        self._log_info(
            "Verificação do popup de melhoria executada",
            event="improvement_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def tratar_popup_melhoria_se_existir(self) -> bool:
        if not self.popup_melhoria_esta_visivel():
            return False

        return self._dismiss_if_present(
            self.POPUP_MELHORIA_BOTAO_DEPOIS,
            timeout=self.SHORT_TIMEOUT,
            element_name="botao_depois_popup_melhoria",
        )

    # === Popup de espelho pendente ===
    def popup_espelho_pendente_esta_visivel(
        self,
        timeout: float | None = None,
    ) -> bool:
        if timeout is None:
            is_visible = self._esta_visivel_imediatamente(
                self.POPUP_ESPELHO_PENDENTE_MENSAGEM,
            )
        else:
            is_visible = self._is_visible(
                self.POPUP_ESPELHO_PENDENTE_MENSAGEM,
                timeout=timeout,
            )

        self._log_info(
            "Verificação do popup de espelho pendente executada",
            event="pending_mirror_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def tratar_popup_espelho_pendente_se_existir(self) -> bool:
        """
        Adia a assinatura (DEPOIS): mantém o espelho pendente, sem
        consumir a massa de teste.
        """
        if not self.popup_espelho_pendente_esta_visivel():
            return False

        tocou = self._dismiss_if_present(
            self.POPUP_ESPELHO_PENDENTE_BOTAO_DEPOIS,
            timeout=self.SHORT_TIMEOUT,
            element_name="botao_depois_popup_espelho_pendente",
        )

        if not tocou:
            return False

        fechou = self._wait_for_absence(
            self.POPUP_ESPELHO_PENDENTE_MENSAGEM,
            timeout=self.SHORT_TIMEOUT,
        )

        if not fechou:
            self._log_warning(
                "Popup de espelho pendente permaneceu visível após DEPOIS",
                event="pending_mirror_popup_still_visible",
            )

        return True

    def aceitar_popup_espelho_pendente(self) -> None:
        """
        Toca em ASSINAR no popup (redireciona para a Assinatura do
        Espelho). Não assina nada por si só.
        """
        self._click(
            self.POPUP_ESPELHO_PENDENTE_BOTAO_ASSINAR,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_assinar_popup_espelho_pendente",
        )

    def dispensar_popups_sobrepostos(self) -> None:
        """
        Dispensa Opinião, Melhoria e espelho pendente (DEPOIS),
        encadeados, com checagem imediata.

        Não espera a Home: serve para limpar a tela antes de sondar o
        estado atual (unlock ou Home). Limitado por
        POPUP_RESOLUTION_TIMEOUT porque os tratar_* retornam True após
        o toque mesmo quando o popup não fecha; sem limite, um toque
        sem efeito prenderia o laço indefinidamente.
        """
        limite = monotonic() + self.POPUP_RESOLUTION_TIMEOUT

        while monotonic() < limite and (
            self.tratar_popup_espelho_pendente_se_existir()
            or self.tratar_popup_opiniao_se_existir()
            or self.tratar_popup_melhoria_se_existir()
        ):
            sleep(self.POPUP_POLL_INTERVAL)

    # === Popup de atualização de versão ===
    def popup_atualizacao_esta_visivel(self) -> bool:
        is_visible = self._esta_visivel_imediatamente(
            self.POPUP_ATUALIZACAO_ALERTA,
        )

        self._log_info(
            "Verificação do popup de atualização executada",
            event="update_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def tratar_popup_atualizacao_se_existir(self) -> bool:
        """
        Dispensa o alerta de atualização de versão.

        O botão é localizado novamente em cada tentativa porque a
        referência pode ficar obsoleta enquanto o alerta é animado.
        """
        if not self.popup_atualizacao_esta_visivel():
            return False

        self._clicar_com_nova_referencia(
            self.POPUP_ATUALIZACAO_BOTAO_CANCELAR,
            element_name="botao_cancelar_popup_atualizacao",
            timeout=self.DEFAULT_TIMEOUT,
        )

        fechou = self._wait_for_absence(
            self.POPUP_ATUALIZACAO_ALERTA,
            timeout=self.DEFAULT_TIMEOUT,
        )

        if not fechou:
            raise AssertionError(
                "O alerta de atualização permaneceu visível após "
                "selecionar 'Cancelar'."
            )

        self._log_info(
            "Popup de atualização cancelado",
            event="update_popup_cancelled",
        )

        return True

    # === Popups da Home ===
    def _tratar_primeiro_popup_disponivel(
        self,
        tratar_lembrete: bool,
    ) -> bool:
        """
        Trata o primeiro popup exibido, sem levantar por ausência.

        O popup de atualização é tratado primeiro por sobrepor os
        demais quando há versão nova pendente.

        A identificação do lembrete usa apenas ATIVAR: DEPOIS tem o
        mesmo accessibility id no popup de melhoria, e usá-lo aqui
        faz um popup entrar no ramo de tratamento do outro.
        """
        if self.tratar_popup_atualizacao_se_existir():
            return True

        lembrete_visivel = self._esta_visivel_imediatamente(
            self.BOTAO_LEMBRETE_ATIVAR,
        )

        if tratar_lembrete and lembrete_visivel:
            return self._dismiss_if_present(
                self.BOTAO_LEMBRETE_DEPOIS,
                timeout=self.SHORT_TIMEOUT,
                element_name="botao_depois_popup_lembrete",
            )

        return (
            self.tratar_popup_espelho_pendente_se_existir()
            or self.tratar_popup_opiniao_se_existir()
            or self.tratar_popup_melhoria_se_existir()
        )

    def tratar_popups_home_se_existirem(
        self,
        tratar_lembrete: bool = True,
    ) -> None:
        """
        Trata popups encadeados em uma única janela de polling.

        Quando tratar_lembrete=False, o popup de lembrete permanece
        disponível para validação específica do teste da Home.
        """
        self._log_info(
            "Iniciando tratamento dos popups da Home",
            event="home_popups_handle_started",
            handle_reminder=tratar_lembrete,
        )

        limite = monotonic() + FLOW_TIMEOUT
        inicio_estabilidade = None
        quantidade_tratada = 0

        while monotonic() < limite:
            if self._tratar_primeiro_popup_disponivel(
                tratar_lembrete=tratar_lembrete,
            ):
                quantidade_tratada += 1
                inicio_estabilidade = None

                sleep(self.POPUP_POLL_INTERVAL)
                continue

            # Quando o lembrete deve permanecer disponível para o
            # cenário atual, não aguardamos a janela de estabilidade
            # da Home: o modal foi preservado intencionalmente.
            if not tratar_lembrete and self._esta_visivel_imediatamente(
                self.BOTAO_LEMBRETE_ATIVAR,
            ):
                break

            if self._home_esta_pronta_imediatamente():
                if inicio_estabilidade is None:
                    inicio_estabilidade = monotonic()

                if (
                    monotonic() - inicio_estabilidade
                    >= self.HOME_STABILITY_TIMEOUT
                ):
                    break
            else:
                inicio_estabilidade = None

            sleep(self.POPUP_POLL_INTERVAL)

        self._log_info(
            "Tratamento dos popups da Home finalizado",
            event="home_popups_handle_finished",
            handled_count=quantidade_tratada,
            home_ready=self._home_esta_pronta_imediatamente(),
        )

    # === Validação da Home ===
    def _home_pronta_dispensando_popups(self) -> bool:
        """
        Uma sondagem da Home, dispensando antes Opinião, Melhoria e o
        espelho pendente (DEPOIS).

        Esses popups surgem a qualquer momento (inclusive ao voltar de
        outra tela) e cobrem a Home, fazendo os locators de referência
        ficarem invisíveis. O lembrete não é tocado: há cenários que o
        validam de propósito.
        """
        (
            self.tratar_popup_espelho_pendente_se_existir()
            or self.tratar_popup_opiniao_se_existir()
            or self.tratar_popup_melhoria_se_existir()
        )

        return self._home_esta_pronta_imediatamente()

    def esta_na_home(
        self,
        timeout: float | None = None,
    ) -> bool:
        """
        Indica se a Home está disponível dentro do timeout.

        Dispensa Opinião, Melhoria e espelho pendente durante a espera:
        um popup oportunista
        cobrindo a Home não significa que o app saiu dela.
        """
        timeout_resolvido = (
            self.DEFAULT_TIMEOUT if timeout is None else timeout
        )

        try:
            WebDriverWait(
                self.driver,
                timeout_resolvido,
                poll_frequency=self.POPUP_POLL_INTERVAL,
            ).until(
                lambda _: self._home_pronta_dispensando_popups(),
                message=(
                    "Nenhum locator de referência da Home ficou "
                    f"visível em {timeout_resolvido}s."
                ),
            )
            is_visible = True

        except TimeoutException:
            is_visible = False

        self._log_info(
            "Validação de presença da Home executada",
            event="home_screen_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def validar_home(self) -> bool:
        return self.esta_na_home()

    def aguardar_retorno_home(self) -> None:
        """
        Aguarda o retorno automático para a Home após uma marcação.

        Durante o retorno, trata os popups de opinião e melhoria
        que possam bloquear os elementos principais da Home.
        """
        self._log_info(
            "Aguardando retorno automático para a Home",
            event="home_return_wait_started",
        )

        limite = monotonic() + FLOW_TIMEOUT

        while monotonic() < limite:
            if self.tratar_popup_opiniao_se_existir():
                sleep(self.POPUP_POLL_INTERVAL)
                continue

            if self.tratar_popup_melhoria_se_existir():
                sleep(self.POPUP_POLL_INTERVAL)
                continue

            if self._home_esta_pronta_imediatamente():
                self._log_info(
                    "Retorno à Home detectado",
                    event="home_return_detected",
                )
                return

            sleep(self.POPUP_POLL_INTERVAL)

        raise AssertionError(
            "A Home não foi restabelecida após o registro do ponto. "
            "Verifique se algum popup bloqueou o retorno automático."
        )

    # === Menu lateral ===
    def abrir_menu(self) -> None:
        """
        Abre o menu lateral tratando popups que possam surgir
        imediatamente antes da interação.
        """
        limite = monotonic() + FLOW_TIMEOUT

        while monotonic() < limite:
            if self._tratar_primeiro_popup_disponivel(
                tratar_lembrete=True,
            ):
                sleep(self.POPUP_POLL_INTERVAL)
                continue

            if self._esta_visivel_imediatamente(
                self.BOTAO_ABRIR_MENU,
            ):
                self._click(
                    self.BOTAO_ABRIR_MENU,
                    timeout=self.DEFAULT_TIMEOUT,
                    element_name="botao_abrir_menu",
                )

                self._log_info(
                    "Menu lateral aberto",
                    event="side_menu_opened",
                )
                return

            sleep(self.POPUP_POLL_INTERVAL)

        raise AssertionError(
            "O menu lateral não ficou disponível e os popups "
            "da Home não puderam ser resolvidos dentro do tempo esperado."
        )

    # === Ações da Home ===
    def clicar_tab_ponto(self) -> None:
        self._click_with_fallback(
            self.ABA_PONTO,
            self.ABA_PONTO_FALLBACK,
            primary_name="aba_ponto",
            fallback_name="aba_ponto_fallback",
            timeout=self.DEFAULT_TIMEOUT,
        )

    def clicar_registrar(self) -> None:
        self._click_with_fallback(
            self.BOTAO_REGISTRAR,
            self.BOTAO_REGISTRAR_FALLBACK,
            primary_name="botao_registrar_ponto",
            fallback_name="botao_registrar_ponto_fallback",
            timeout=self.DEFAULT_TIMEOUT,
        )

    def _clicar_tratando_popups(
        self,
        locator: tuple[str, str],
        element_name: str,
    ) -> None:
        """
        Clica no elemento tratando popups que possam interceptar o
        clique nesse meio-tempo.

        Popups como Opinião/Melhoria não são exibidos sempre e podem
        surgir a qualquer momento do fluxo — inclusive depois que a
        tela já foi validada, mas antes do clique em si.
        """
        limite = monotonic() + self.POPUP_RESOLUTION_TIMEOUT

        while monotonic() < limite:
            if self._tratar_primeiro_popup_disponivel(
                tratar_lembrete=True,
            ):
                sleep(self.POPUP_POLL_INTERVAL)
                continue

            if self._esta_visivel_imediatamente(locator):
                self._click(
                    locator,
                    timeout=self.DEFAULT_TIMEOUT,
                    element_name=element_name,
                )
                return

            sleep(self.POPUP_POLL_INTERVAL)

        raise AssertionError(
            f"'{element_name}' não ficou disponível e os popups "
            "da Home não puderam ser resolvidos dentro do tempo "
            "esperado."
        )

    def _clicar_registrar_tratando_popups(self) -> None:
        """
        Abre a confirmação do registro, tratando popups que possam
        interceptar o fluxo nesse meio-tempo.

        A aba Ponto só é acionada quando Registrar não está visível:
        clicá-la sempre, antes de olhar a tela, repetia a abertura do
        registro (o toque em "PONTO" pode já abrir a confirmação, e a
        iteração seguinte clicava de novo).
        """
        limite = monotonic() + self.POPUP_RESOLUTION_TIMEOUT

        while monotonic() < limite:
            if self._tratar_primeiro_popup_disponivel(
                tratar_lembrete=True,
            ):
                sleep(self.POPUP_POLL_INTERVAL)
                continue

            if self._confirmacao_registro_visivel_imediatamente():
                return

            if self._esta_visivel_imediatamente(
                self.BOTAO_REGISTRAR,
            ) or self._esta_visivel_imediatamente(
                self.BOTAO_REGISTRAR_FALLBACK,
            ):
                self.clicar_registrar()
                return

            self.clicar_tab_ponto()

            sleep(self.POPUP_POLL_INTERVAL)

        raise AssertionError(
            "O botão Registrar não ficou disponível e os popups "
            "da Home não puderam ser resolvidos dentro do tempo "
            "esperado."
        )

    # === Confirmação do registro ===
    def popup_confirmacao_ponto_esta_visivel(
        self,
        timeout: float | None = None,
    ) -> bool:
        timeout_resolvido = (
            self.DEFAULT_TIMEOUT if timeout is None else timeout
        )

        is_visible = self._is_visible(
            self.CONFIRMACAO_PONTO_TITULO,
            timeout=timeout_resolvido,
        )

        if not is_visible:
            is_visible = self._esta_visivel_imediatamente(
                self.CONFIRMACAO_PONTO_BOTAO_SIM,
            )

        self._log_info(
            "Verificação do popup de confirmação executada",
            event="point_confirmation_popup_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def _confirmacao_registro_visivel_imediatamente(self) -> bool:
        return self._esta_visivel_imediatamente(
            self.CONFIRMACAO_PONTO_TITULO,
        ) or self._esta_visivel_imediatamente(
            self.CONFIRMACAO_PONTO_BOTAO_SIM,
        )

    def _aguardar_confirmacao_registro_ponto(self) -> None:
        WebDriverWait(
            self.driver,
            FLOW_TIMEOUT,
            poll_frequency=self.POPUP_POLL_INTERVAL,
        ).until(lambda _: self._confirmacao_registro_visivel_imediatamente())

    def _aguardar_resultado_do_registro(self, timeout: float) -> str | None:
        """
        Espera o que o app mostra depois do SIM da confirmação: a
        mensagem de sucesso ("sucesso") ou o aviso de fora da geo
        delimitação ("fora_geo"). None se nenhum aparecer no tempo.
        """

        def resultado(_):
            if self._esta_visivel_imediatamente(
                self.MENSAGEM_PONTO_REGISTRADO_SUCESSO
            ):
                return "sucesso"

            if self._esta_visivel_imediatamente(self.POPUP_FORA_GEO_MENSAGEM):
                return "fora_geo"

            return False

        try:
            return WebDriverWait(
                self.driver,
                timeout,
                poll_frequency=self.POPUP_POLL_INTERVAL,
            ).until(resultado)
        except TimeoutException:
            return None

    def _aguardar_fechamento_confirmacao_ponto(self) -> None:
        WebDriverWait(
            self.driver,
            FLOW_TIMEOUT,
            poll_frequency=self.POPUP_POLL_INTERVAL,
        ).until(
            EC.invisibility_of_element_located(
                self.CONFIRMACAO_PONTO_TITULO,
            )
        )

    def abrir_confirmacao_registro_ponto(self) -> None:
        """
        Abre a confirmação do registro de ponto.

        Pré-condições externas:
        - Localização concedida no emulador/device Android.
        - Câmera concedida no emulador/device Android.

        As permissões devem ser preparadas pelas fixtures de
        ambiente antes da execução do cenário.
        """
        self.tratar_popups_home_se_existirem()

        assert self.esta_na_home(
            timeout=self.SHORT_TIMEOUT,
        ), "A Home não está disponível para registrar o ponto."

        self._clicar_registrar_tratando_popups()

        self._aguardar_confirmacao_registro_ponto()

        assert self.popup_confirmacao_ponto_esta_visivel(
            timeout=self.SHORT_TIMEOUT,
        ), (
            "A confirmação do registro do ponto não foi exibida. "
            "Verifique se as permissões de localização e câmera "
            "foram concedidas antes do cenário."
        )

        self._log_info(
            "Confirmação do registro de ponto aberta",
            event="point_confirmation_opened",
        )

    def confirmar_registro_ponto(self) -> None:
        self._click(
            self.CONFIRMACAO_PONTO_BOTAO_SIM,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_sim_confirmacao_ponto",
        )

        # Runtime permissions podem surgir apenas na primeira marcação.
        for _ in range(3):
            if not self._click_if_visible(
                self.PERMISSAO_ANDROID,
                timeout=self.OPTIONAL_POPUP_TIMEOUT,
                element_name="permissao_android",
            ):
                break

        # Centro de custo é condicional no cadastro do colaborador.
        if self._is_visible(
            self.CENTRO_CUSTO,
            timeout=self.OPTIONAL_POPUP_TIMEOUT,
        ):
            self._click_if_visible(
                self.SWITCH_CENTRO_CUSTO,
                timeout=self.OPTIONAL_POPUP_TIMEOUT,
                element_name="switch_centro_custo",
            )
            self._click(
                self.BOTAO_CONFIRMAR_GENERICO,
                timeout=self.DEFAULT_TIMEOUT,
                element_name="confirmar_centro_custo",
            )

        assert self._is_visible(
            self.BOTAO_TIRAR_FOTO,
            timeout=self.LONG_TIMEOUT,
        ), "A etapa final de registro não foi exibida."

        assert self._click_if_visible(
            self.BOTAO_CONFIRMAR_SEM_FOTO,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="confirmar_registro_sem_foto",
        ), (
            "O botão Android 'btn_confirmar_sem_foto' não foi exibido. "
            "Confirme que a API deixou a confirmação de foto desabilitada."
        )

        self._log_info(
            "Registro de ponto confirmado",
            event="point_registration_confirmed",
        )

    def cancelar_registro_ponto(self) -> None:
        self._clicar_tratando_popups(
            self.CONFIRMACAO_PONTO_BOTAO_NAO,
            element_name="botao_nao_confirmacao_ponto",
        )

        self._aguardar_fechamento_confirmacao_ponto()

        self._log_info(
            "Tentativa de registro de ponto cancelada",
            event="point_registration_cancelled",
        )

    # === Fora da geo delimitação ===
    def popup_fora_geo_esta_visivel(
        self, timeout: float | None = None
    ) -> bool:
        return self._is_visible(
            self.POPUP_FORA_GEO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT if timeout is None else timeout,
        )

    def validar_aviso_fora_da_geo(self) -> None:
        """
        Depois do SIM da confirmação, espera o aviso de fora da geo
        delimitação.

        Falha com a causa se o app registrar sem avisar: a localização
        aplicada estava dentro da área (ou a geo não está cadastrada
        para o usuário).
        """
        resultado = self._aguardar_resultado_do_registro(self.LONG_TIMEOUT)

        if resultado == "sucesso":
            raise AssertionError(
                "O app registrou o ponto sem avisar que a localização "
                "está fora da geo delimitação. Confira as coordenadas "
                "ANDROID_GEO_FORA_* e se a geo está cadastrada para o usuário "
                "de teste. Atenção: este registro ficou gravado."
            )

        assert resultado == "fora_geo", (
            "Nem o aviso de fora da geo nem a mensagem de sucesso "
            "apareceram após confirmar o registro."
        )

        self._log_info(
            "Aviso de fora da geo delimitação exibido",
            event="point_outside_geofence_warning",
        )

    def cancelar_registro_fora_da_geo(self) -> None:
        """Responde NÃO ao aviso de fora da geo e espera ele fechar."""
        self._click(
            self.POPUP_FORA_GEO_BOTAO_NAO,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_nao_fora_geo",
        )

        assert self._wait_for_absence(
            self.POPUP_FORA_GEO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT,
        ), "O aviso de fora da geo não fechou após tocar em NÃO."

        self._log_info(
            "Registro fora da geo cancelado",
            event="point_outside_geofence_cancelled",
        )

    def confirmar_registro_fora_da_geo(self) -> None:
        """
        Responde SIM ao aviso de fora da geo (registra mesmo fora da
        área) e espera o aviso fechar.
        """
        self._click(
            self.POPUP_FORA_GEO_BOTAO_SIM,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="botao_sim_fora_geo",
        )

        assert self._wait_for_absence(
            self.POPUP_FORA_GEO_MENSAGEM,
            timeout=self.DEFAULT_TIMEOUT,
        ), "O aviso de fora da geo não fechou após tocar em SIM."

        self._log_info(
            "Registro fora da geo confirmado",
            event="point_outside_geofence_confirmed",
        )

    # === Sucesso do registro ===
    def validar_ponto_registrado_com_sucesso(
        self,
        timeout: float | None = None,
    ) -> bool:
        timeout_resolvido = self.LONG_TIMEOUT if timeout is None else timeout

        resultado = self._aguardar_resultado_do_registro(timeout_resolvido)

        if resultado == "fora_geo":
            raise AssertionError(
                "O app avisou que a localização está fora da geo "
                "delimitação ao confirmar o registro. A coordenada usada "
                "deve estar dentro da área cadastrada para o usuário: "
                "ANDROID_LOCATION_* (registro comum) ou ANDROID_GEO_DENTRO_* "
                "(teste de geo) no env.<device>.yaml."
            )

        is_visible = resultado == "sucesso"

        self._log_info(
            "Validação do registro de ponto executada",
            event="point_registration_success_checked",
            status="visible" if is_visible else "not_visible",
        )

        return is_visible

    def obter_data_hora_registro(self) -> datetime:
        """Lê a hora do registro Android e converte para datetime."""
        texto = self._get_text(
            self.DATA_HORA_REGISTRO,
            timeout=self.DEFAULT_TIMEOUT,
            element_name="data_hora_registro",
        )

        match_completo = self.REGEX_DATA_HORA_REGISTRO.search(texto)
        if match_completo:
            hora = match_completo.group(2)
            formato = (
                "%d/%m/%Y %H:%M:%S"
                if hora.count(":") == 2
                else "%d/%m/%Y %H:%M"
            )
            return datetime.strptime(
                f"{match_completo.group(1)} {hora}",
                formato,
            )

        match_hora = self.REGEX_HORA_REGISTRO.search(texto)
        if not match_hora:
            raise AssertionError(
                "Não foi possível interpretar a hora exibida no registro "
                f"Android: '{texto}'."
            )

        agora = datetime.now()
        hora = match_hora.group(1)
        formato = "%H:%M:%S" if hora.count(":") == 2 else "%H:%M"
        horario = datetime.strptime(hora, formato).time()
        return datetime.combine(agora.date(), horario)

    def validar_hora_registro_recente(
        self,
        tolerancia_segundos: float = 120,
    ) -> bool:
        """
        Valida que a data/hora exibida está próxima do horário atual
        da máquina de execução (mesma referência usada pelo restante
        da suíte — ver utils/helpers.current_timestamp).
        """
        hora_registrada = self.obter_data_hora_registro()

        diferenca_segundos = abs(
            (datetime.now() - hora_registrada).total_seconds()
        )

        dentro_da_tolerancia = diferenca_segundos <= tolerancia_segundos

        self._log_info(
            "Validação da hora do registro executada",
            event="point_registration_time_checked",
            diferenca_segundos=diferenca_segundos,
            tolerancia_segundos=tolerancia_segundos,
        )

        return dentro_da_tolerancia

    # === Fluxo completo de registro ===
    def registrar_ponto(self) -> None:
        """
        Executa uma marcação real e aguarda o retorno automático.
        """
        self._log_info(
            "Iniciando registro real de ponto pela Home",
            event="point_registration_started",
        )

        self.abrir_confirmacao_registro_ponto()
        self.confirmar_registro_ponto()

        assert self.validar_ponto_registrado_com_sucesso(), (
            "A mensagem de sucesso não foi exibida "
            "após confirmar o registro do ponto."
        )

        self.aguardar_retorno_home()

        self._log_info(
            "Registro real de ponto executado",
            event="point_registration_finished",
        )
