"""
Base dos clientes da API do sistema web ifPonto.

O ifPonto é o painel administrativo que hospeda os menus manipulados
pela automação. Cada menu vira uma subclasse em seu próprio módulo; a
base carrega o transporte comum e roteia por 'pag'.

- IfPontoApiClient (aqui): transporte, auth, parse/erro e a escrita
  genérica (cmd=up, um campo por chamada). Não conhece nenhum menu
  específico; roteia por self.PAG.
- MonitorCelularClient (api/monitor_celular_client.py): menu
  "Monitor > Celular" (pag=monitor_celular).
- ConfiguracaoAppClient / ConfiguracaoAppConfClient
  (api/configuracao_app_client.py): seções de "Configuração > Tela do
  aplicativo".

Menus "Monitor" e "Configuração" são irmãos no ifPonto (nenhum está
dentro do outro), por isso a base leva o nome do sistema, não de um dos
menus. Menu novo: subclasse nova, em módulo próprio, fixando PAG.
"""

import hashlib
import time
from datetime import datetime
from typing import Any

import requests

from utils.logger import get_logger

logger = get_logger(__name__)


class IfPontoApiClient:
    """
    Base de comunicação com a API do sistema web ifPonto.

    Concentra o encanamento compartilhado por todos os menus:
    autenticação diária, transporte multipart, parse/validação de
    resposta e a escrita genérica de um campo (cmd=up).

    Subclasses fixam PAG (o menu alvo) e expõem os métodos de negócio
    do seu menu. A base não conhece 'celular' nem 'configuração' — só
    sabe rotear cmd por PAG.
    """

    REQUEST_TIMEOUT = 30

    # Cada subclasse concreta fixa o seu módulo.
    PAG: str = ""

    # === Inicialização ===
    def __init__(
        self,
        base_url: str,
        user: str,
        token_original: str,
    ):
        if not self.PAG:
            raise ValueError(
                f"{type(self).__name__} não definiu PAG. "
                "Cada client concreto precisa fixar o módulo alvo."
            )

        self.base_url = base_url.strip()
        self.user = user.strip()
        self.token_original = token_original.strip()
        self.session = requests.Session()

        self._validar_configuracao()

        logger.info(
            "Cliente da API do ifPonto inicializado",
            extra={
                "event": "api_client_initialized",
                "client": type(self).__name__,
                "pag": self.PAG,
                "base_url": self.base_url,
                "api_user": self.user,
            },
        )

    # === Configuração ===
    def _validar_configuracao(self) -> None:
        """
        Valida as configurações obrigatórias para comunicação com a API.
        """
        if not self.base_url:
            raise ValueError("API_BASE_URL não foi configurado.")

        if not self.user:
            raise ValueError("API_USER não foi configurado.")

        if not self.token_original:
            raise ValueError("API_TOKEN não foi configurado.")

    # === Autenticação e headers ===
    def _gerar_token(self) -> str:
        """
        Gera o token diário utilizado na autenticação da API.
        """
        data_atual = datetime.now().strftime("%d/%m/%Y")

        conteudo_token = f"{self.token_original}{data_atual}"

        return hashlib.sha256(conteudo_token.encode()).hexdigest()

    def _headers(self) -> dict[str, str]:
        """
        Monta os headers de autenticação da requisição.
        """
        return {
            "User": self.user,
            "Token": self._gerar_token(),
        }

    # === Requisições e respostas ===
    @staticmethod
    def _build_multipart_payload(
        payload: dict[str, Any],
    ) -> dict[str, tuple[None, str]]:
        """
        Converte o payload para multipart/form-data.

        O Content-Type não é definido manualmente para permitir
        que o requests gere corretamente o boundary da requisição.
        """
        return {
            campo: (
                None,
                (
                    str(valor).lower()
                    if isinstance(valor, bool)
                    else str(valor)
                ),
            )
            for campo, valor in payload.items()
        }

    def _post(
        self,
        payload: dict[str, Any],
    ) -> requests.Response:
        """
        Executa uma requisição POST multipart para a API do ifPonto.
        """
        start_time = time.perf_counter()

        logger.info(
            "Iniciando requisição POST para a API do ifPonto",
            extra={
                "event": "api_request_started",
                "http_method": "POST",
                "endpoint": self.base_url,
                "api_user": self.user,
                "payload_cmd": payload.get("cmd"),
                "payload_pag": payload.get("pag"),
            },
        )

        try:
            response = self.session.post(
                self.base_url,
                headers=self._headers(),
                files=self._build_multipart_payload(payload),
                timeout=self.REQUEST_TIMEOUT,
            )

        except requests.RequestException:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "Falha na requisição para a API do ifPonto",
                extra={
                    "event": "api_request_failed",
                    "http_method": "POST",
                    "endpoint": self.base_url,
                    "api_user": self.user,
                    "duration_ms": duration_ms,
                    "payload_cmd": payload.get("cmd"),
                    "payload_pag": payload.get("pag"),
                },
            )

            raise

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "Requisição POST concluída",
            extra={
                "event": "api_request_finished",
                "http_method": "POST",
                "endpoint": self.base_url,
                "api_user": self.user,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "payload_cmd": payload.get("cmd"),
                "payload_pag": payload.get("pag"),
            },
        )

        response.raise_for_status()

        return response

    def _parse_response(
        self,
        response: requests.Response,
    ) -> Any:
        """
        Converte a resposta para JSON quando possível.

        Respostas HTML são rejeitadas por normalmente indicarem
        redirecionamento indevido para uma tela de autenticação.
        """
        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if "text/html" in content_type:
            logger.error(
                "A API retornou uma resposta em HTML",
                extra={
                    "event": "api_html_response_received",
                    "status_code": response.status_code,
                    "content_type": content_type,
                },
            )

            raise ValueError(
                "A API retornou uma resposta em HTML. "
                "Verifique se ocorreu um redirecionamento "
                "para a tela de login."
            )

        try:
            parsed_response = response.json()

            logger.info(
                "Resposta da API convertida para JSON",
                extra={
                    "event": "api_response_parsed_json",
                    "status_code": response.status_code,
                },
            )

            return parsed_response

        except ValueError:
            logger.warning(
                "A resposta da API não está em formato JSON; "
                "retornando o conteúdo textual",
                extra={
                    "event": "api_response_parsed_text",
                    "status_code": response.status_code,
                    "content_type": content_type,
                },
            )

            return response.text

    def _validar_resposta_negocio(
        self,
        resposta: Any,
        operacao: str,
    ) -> None:
        """
        Interrompe o fluxo quando a API retorna erro de negócio,
        mesmo quando o status HTTP indica sucesso.
        """
        if not isinstance(resposta, dict):
            return

        sucesso = resposta.get("success")

        resposta_indica_falha = sucesso in (
            False,
            0,
            "0",
            "false",
            "False",
        )

        if not resposta_indica_falha:
            return

        mensagem = str(
            resposta.get("info")
            or resposta.get("message")
            or resposta.get("mensagem")
            or "Erro de negócio não informado."
        ).strip()

        logger.error(
            "A API recusou a operação solicitada",
            extra={
                "event": "api_business_error",
                "operation": operacao,
                "api_message": mensagem,
            },
        )

        raise ValueError(f"Falha na operação '{operacao}': {mensagem}")

    # === Payload e execução ===
    def _build_payload(
        self,
        cmd: str,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """
        Monta o payload base para operações do módulo (self.PAG).

        Generaliza o antigo _build_payload_monitor_celular: o 'pag'
        deixa de ser fixo e passa a vir de self.PAG, permitindo que
        cada subclasse roteie para o seu módulo.
        """
        payload = {
            "pag": self.PAG,
            "cmd": cmd,
        }

        payload.update(extra_fields)

        return payload

    def _executar(
        self,
        payload: dict[str, Any],
        *,
        operacao: str,
    ) -> Any:
        """
        Executa post -> parse -> validação de negócio.

        Colapsa o tripé repetido em todos os métodos de leitura e
        escrita. Retorna a resposta já convertida e validada.
        """
        response = self._post(payload)
        parsed_response = self._parse_response(response)

        self._validar_resposta_negocio(
            parsed_response,
            operacao=operacao,
        )

        return parsed_response

    # === Escrita genérica ===
    def atualizar_campo(
        self,
        codigo: int,
        campo: str,
        value: Any,
    ) -> Any:
        """
        Atualiza um campo do registro (cmd=up).

        A API aceita um campo por chamada, então não há atomicidade
        entre atualizações consecutivas. Booleanos são normalizados
        para "true"/"false" pelo _build_multipart_payload.

        Comum a todos os módulos: um checkbox é sempre um campo do
        registro atualizado por cmd=up.
        """
        try:
            codigo_resolvido = int(codigo)

        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Código do registro inválido: {codigo!r}"
            ) from error

        campo_normalizado = campo.strip()

        if not campo_normalizado:
            raise ValueError("O nome do campo não pode ser vazio.")

        payload = self._build_payload(
            cmd="up",
            codigo=str(codigo_resolvido),
            campo=campo_normalizado,
            value=value,
        )

        logger.info(
            "Iniciando atualização de campo",
            extra={
                "event": "field_update_started",
                "pag": self.PAG,
                "record_id": codigo_resolvido,
                "field": campo_normalizado,
                "field_value": value,
            },
        )

        parsed_response = self._executar(
            payload,
            operacao=(f"atualizar_campo:{self.PAG}:{campo_normalizado}"),
        )

        logger.info(
            "Campo atualizado",
            extra={
                "event": "field_updated",
                "pag": self.PAG,
                "record_id": codigo_resolvido,
                "field": campo_normalizado,
                "field_value": value,
            },
        )

        return parsed_response
