"""
Clientes das seções de "Configuração > Tela do aplicativo" do ifPonto.

- ConfiguracaoAppBase: esquema de escrita próprio (codigo carrega o
  slug da config, não um id de aparelho); expõe _definir_config().
- ConfiguracaoAppClient: seção "Botões" (pag=configuracao_app). Liga e
  desliga recursos/telas exibidos no app.
- ConfiguracaoAppConfClient: seção "Configurações"
  (pag=configuracao_app+conf). Regras de marcação (geo, foto/
  reconhecimento facial, offline, timezone, centro de custo etc.).
"""

from typing import Any

from api.ifponto_api_client import IfPontoApiClient
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfiguracaoAppBase(IfPontoApiClient):
    """
    Base das seções da tela "Configuração > Tela do aplicativo".

    Esquema de escrita DIFERENTE do monitor_celular. Aqui cada linha da
    lista é uma configuração identificada por um slug, e o payload é:

        pag=<PAG da seção>  cmd=up  codigo=<slug>  campo=ativo  value=<bool>

    Ou seja: 'codigo' carrega o SLUG da config (não o id de um aparelho),
    e 'campo' é sempre "ativo". Por isso NÃO reutiliza o atualizar_campo()
    da IfPontoApiClient (que assume codigo=id, campo=variável) — usa o
    _definir_config() próprio abaixo.

    Escopo GLOBAL: estas configurações valem para o sistema inteiro, não
    por aparelho. Consequência para os testes: um teste que ligar uma
    config e não repor vaza estado para TODA a suíte, em qualquer
    aparelho. A reposição tem que morar em teardown de fixture (roda
    mesmo se o teste falhar no meio), nunca só no corpo do teste.

    O campo fixo 'ativo' é uma constante da seção; os slugs são
    declarados nas subclasses (em inglês, conforme o cadastro real).
    """

    CAMPO_ATIVO = "ativo"

    def _definir_config(
        self,
        slug: str,
        ativo: bool,
    ) -> Any:
        """
        Liga/desliga uma configuração pelo seu slug.

        codigo=<slug>, campo="ativo", value=<bool>. Sem id de aparelho:
        estas configs são globais.
        """
        slug_normalizado = slug.strip()

        if not slug_normalizado:
            raise ValueError("O slug da configuração não pode ser vazio.")

        payload = self._build_payload(
            cmd="up",
            codigo=slug_normalizado,
            campo=self.CAMPO_ATIVO,
            value=bool(ativo),
        )

        logger.info(
            "Iniciando atualização de configuração global",
            extra={
                "event": "app_config_update_started",
                "pag": self.PAG,
                "config_slug": slug_normalizado,
                "config_value": bool(ativo),
            },
        )

        parsed_response = self._executar(
            payload,
            operacao=f"config:{self.PAG}:{slug_normalizado}",
        )

        logger.info(
            "Configuração global atualizada",
            extra={
                "event": "app_config_updated",
                "pag": self.PAG,
                "config_slug": slug_normalizado,
                "config_value": bool(ativo),
            },
        )

        return parsed_response


class ConfiguracaoAppClient(ConfiguracaoAppBase):
    """
    Seção "Botões" (pag=configuracao_app).

    Controla quais recursos/telas o app exibe (Humor, Alertas, Espelho,
    Status, Ajustes, Informe, Holerite, Marcação, Escala, Aprovações).

    Slugs em inglês, conforme o cadastro. Só 'alerts' foi confirmado no
    payload real; os demais viram do seu mapa rótulo->slug. Adicione uma
    constante + um método (ou use _definir_config direto) por item que a
    automação for tocar — não precisa mapear os 10.
    """

    PAG = "configuracao_app"

    # Confirmado no payload real:
    CONFIG_ALERTS = "alerts"

    # TODO: colar do seu mapa os slugs dos itens que os testes usarem.
    # Ex.: CONFIG_ESPELHO = "mirror"   # confirmar slug real

    def definir_alerts(self, ativo: bool) -> Any:
        """Liga/desliga o botão 'Alertas'."""
        return self._definir_config(self.CONFIG_ALERTS, ativo)


class ConfiguracaoAppConfClient(ConfiguracaoAppBase):
    """
    Seção "Configurações" (pag=configuracao_app+conf).

    Controla regras de marcação (geo, foto/reconhecimento facial,
    offline, timezone, centro de custo etc.).

    ATENÇÃO ao pag: 'configuracao_app+conf' assume o '+' LITERAL na
    string enviada. Se a captura do DevTools estava decodificada, o valor
    real pode ser 'configuracao_app conf' (com espaço). Confirmar antes
    de rodar em CI.

    Slugs em inglês. Só 'rosto_obrigatorio' apareceu no payload real —
    e cuidado com a semântica: a tela tem itens distintos para "Registrar
    sem tirar foto" e "Bloquear marcação sem reconhecimento facial".
    Confirme qual slug corresponde a qual regra antes de escrever o teste.
    """

    PAG = "configuracao_app+conf"  # '+' LITERAL — confirmar via DevTools

    # Confirmado no payload real (bloqueio por reconhecimento facial):
    CONFIG_ROSTO_OBRIGATORIO = "rosto_obrigatorio"

    # TODO: colar do seu mapa os slugs das demais regras testadas.
    # Ex.: CONFIG_SEM_LOCALIZACAO = "..."   # "Marcação sem localização"
    #      CONFIG_BLOQUEAR_FORA_GEO = "..."  # "Bloquear marcação fora da Geo"

    def definir_rosto_obrigatorio(self, ativo: bool) -> Any:
        """
        Liga/desliga o bloqueio de marcação sem reconhecimento facial.

        ativo=True  -> exige rosto (bloqueia marcação sem reconhecimento)
        ativo=False -> permite marcar sem rosto
        """
        return self._definir_config(self.CONFIG_ROSTO_OBRIGATORIO, ativo)
