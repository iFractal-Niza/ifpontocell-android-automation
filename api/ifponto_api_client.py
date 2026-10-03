"""
Clientes da API do sistema web ifPonto.

O ifPonto é o painel administrativo que hospeda os menus manipulados
pela automação. Cada menu vira uma subclasse; a base carrega o
transporte comum e roteia por 'pag'.

Estrutura:
- IfPontoApiClient      : base (o sistema web ifPonto). Transporte, auth,
                          parse/erro e a escrita genérica (cmd=up, um
                          campo por chamada). Não conhece nenhum menu
                          específico; roteia por self.PAG.
- MonitorCelularClient  : menu "Monitor > Celular" (pag=monitor_celular).
                          Lista os aparelhos de todos os colaboradores que
                          fizeram login no app, ordenados pela última
                          comunicação. Além dos checkboxes, concentra TODA
                          a leitura-e-filtro (listagem, extractors,
                          codigos_anteriores, orquestração de ativação com
                          guard idempotente).
- ConfiguracaoAppBase   : base das seções de "Configuração > Tela do
                          aplicativo". Esquema de escrita à parte (codigo
                          carrega o slug da config, não um id de
                          aparelho); expõe _definir_config() para as
                          subclasses.
- ConfiguracaoAppClient : seção "Botões" (pag=configuracao_app). Liga/
                          desliga recursos/telas exibidos no app.
- ConfiguracaoAppConfClient : seção "Configurações"
                          (pag=configuracao_app+conf). Regras de
                          marcação (geo, foto/reconhecimento facial,
                          offline, timezone, centro de custo etc.).

Menus "Monitor" e "Configuração" são irmãos no ifPonto (nenhum está
dentro do outro), por isso a base leva o nome do sistema, não de um dos
menus.

Para dividir em arquivos no projeto, os três blocos abaixo (marcados com
==== CORTE AQUI ====) podem virar módulos separados que importam a base.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any

import requests

from utils.logger import get_logger


logger = get_logger(__name__)


# ==== CORTE AQUI: base (ifponto_api_client.py) ====
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
            raise ValueError(
                "API_BASE_URL não foi configurado."
            )

        if not self.user:
            raise ValueError(
                "API_USER não foi configurado."
            )

        if not self.token_original:
            raise ValueError(
                "API_TOKEN não foi configurado."
            )

    # === Autenticação e headers ===
    def _gerar_token(self) -> str:
        """
        Gera o token diário utilizado na autenticação da API.
        """
        data_atual = datetime.now().strftime(
            "%d/%m/%Y"
        )

        conteudo_token = (
            f"{self.token_original}{data_atual}"
        )

        return hashlib.sha256(
            conteudo_token.encode()
        ).hexdigest()

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
                files=self._build_multipart_payload(
                    payload
                ),
                timeout=self.REQUEST_TIMEOUT,
            )

        except requests.RequestException:
            duration_ms = round(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000,
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
            (
                time.perf_counter()
                - start_time
            )
            * 1000,
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

        raise ValueError(
            f"Falha na operação '{operacao}': {mensagem}"
        )

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
            raise ValueError(
                "O nome do campo não pode ser vazio."
            )

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
            operacao=(
                f"atualizar_campo:{self.PAG}:{campo_normalizado}"
            ),
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


# ==== CORTE AQUI: monitor_celular (monitor_celular_client.py) ====
class MonitorCelularClient(IfPontoApiClient):
    """
    Client do menu "Monitor > Celular" (pag=monitor_celular).

    Esse menu lista os aparelhos de todos os colaboradores que fizeram
    login no app, ordenados pela última comunicação (DESC) — daí toda a
    leitura-e-filtro viver aqui: listagem, extractors, codigos_anteriores
    e a orquestração de ativação com guard idempotente.

    Os checkboxes (ativo, e demais campos do cadastro) delegam à escrita
    genérica da base.
    """

    PAG = "monitor_celular"

    DEFAULT_PAGE = 1
    DEFAULT_LIMIT = 25

    SORT_PROPERTY = "dtultima_comunicacao"
    SORT_DIRECTION = "DESC"

    # === Campos do Monitor Celular (por aparelho) ===
    # Estes três campos ficam no registro do APARELHO em monitor_celular
    # e valem só para aquele device. 'ativo' é o confirmado no código;
    # gps_obrigatorio/sem_foto são rótulos da tela — confirme o nome real
    # via obter_campos_disponiveis() antes de usar em cmd=up.
    #
    # NÃO confundir com as regras GLOBAIS de geo/foto da seção
    # "Configuração > Configurações" (ConfiguracaoAppConfClient, ex.:
    # rosto_obrigatorio). Aquelas valem para o sistema todo; estas, por
    # aparelho. Eixos independentes — mesmo assunto (geo/foto), escopos
    # diferentes.
    CAMPO_ATIVO = "ativo"
    CAMPO_GPS_OBRIGATORIO = "gps_obrigatorio"  # CONFIRMAR nome real (por aparelho)
    CAMPO_SEM_FOTO = "sem_foto"                # CONFIRMAR nome real (por aparelho)

    # === Checkbox Ativo ===
    def atualizar_status_celular(
        self,
        codigo: int,
        ativo: bool,
    ) -> Any:
        """
        Atualiza o checkbox Ativo do celular informado.

        Preserva a assinatura histórica; delega à escrita genérica.
        """
        return self.atualizar_campo(
            codigo=codigo,
            campo=self.CAMPO_ATIVO,
            value=bool(ativo),
        )

    def ativar_celular(
        self,
        codigo: int,
    ) -> Any:
        """
        Seleciona o checkbox Ativo do celular informado.
        """
        logger.info(
            "Iniciando ativação do celular",
            extra={
                "event": "device_activation_started",
                "device_id": int(codigo),
            },
        )

        return self.atualizar_status_celular(
            codigo=codigo,
            ativo=True,
        )

    def desativar_celular(
        self,
        codigo: int,
    ) -> Any:
        """
        Desmarca o checkbox Ativo do celular informado.
        """
        logger.info(
            "Iniciando desativação do celular",
            extra={
                "event": "device_deactivation_started",
                "device_id": int(codigo),
            },
        )

        return self.atualizar_status_celular(
            codigo=codigo,
            ativo=False,
        )

    # === Outros checkboxes do cadastro ===
    def definir_gps_obrigatorio(
        self,
        codigo: int,
        obrigatorio: bool,
    ) -> Any:
        """
        Marca ou desmarca o checkbox de GPS obrigatório.
        """
        return self.atualizar_campo(
            codigo=codigo,
            campo=self.CAMPO_GPS_OBRIGATORIO,
            value=bool(obrigatorio),
        )

    def definir_sem_foto(
        self,
        codigo: int,
        sem_foto: bool,
    ) -> Any:
        """
        Marca ou desmarca o checkbox de registro sem foto.
        """
        return self.atualizar_campo(
            codigo=codigo,
            campo=self.CAMPO_SEM_FOTO,
            value=bool(sem_foto),
        )

    def configurar_celular(
        self,
        codigo: int,
        *,
        ativo: bool | None = None,
        gps_obrigatorio: bool | None = None,
        sem_foto: bool | None = None,
    ) -> dict[str, Any]:
        """
        Aplica somente os campos informados, em uma chamada cada.

        Retorna o mapa campo -> resposta da API. Campos com None são
        ignorados, o que permite alterar um checkbox sem tocar nos
        outros.

        Não é atômico: se a segunda chamada falhar, a primeira já foi
        aplicada. Em teardown, reponha explicitamente o estado.
        """
        alteracoes = (
            (self.CAMPO_ATIVO, ativo),
            (self.CAMPO_GPS_OBRIGATORIO, gps_obrigatorio),
            (self.CAMPO_SEM_FOTO, sem_foto),
        )

        resultados: dict[str, Any] = {}

        for campo, valor in alteracoes:
            if valor is None:
                continue

            resultados[campo] = self.atualizar_campo(
                codigo=codigo,
                campo=campo,
                value=bool(valor),
            )

        if not resultados:
            logger.warning(
                "Nenhum campo informado para configuração",
                extra={
                    "event": "device_configuration_noop",
                    "device_id": int(codigo),
                },
            )

        return resultados

    # === Diagnóstico ===
    def obter_campos_disponiveis(
        self,
        nome_pessoa: str,
    ) -> list[str]:
        """
        Lista as chaves do registro mais recente da pessoa.

        Serve para descobrir o nome real dos campos aceitos em cmd=up,
        que nem sempre coincide com o rótulo exibido na tela.
        """
        registro = self.obter_registro_celular_por_nome_pessoa(
            nome_pessoa
        )

        return sorted(registro.keys())

    # === Listagem ===
    def listar_celulares(
        self,
        page: int = DEFAULT_PAGE,
        limit: int = DEFAULT_LIMIT,
    ) -> Any:
        """
        Lista os celulares ordenados pela última comunicação,
        do registro mais recente para o mais antigo.

        Contrato capturado na chamada real do Monitor Celular:
        - cmd: get
        - titulo: Celular
        - sort: dtultima_comunicacao DESC
        """
        if page <= 0:
            raise ValueError(
                "A página deve ser maior que zero."
            )

        if limit <= 0:
            raise ValueError(
                "O limite deve ser maior que zero."
            )

        start = (page - 1) * limit

        ordenacao = json.dumps(
            [
                {
                    "property": self.SORT_PROPERTY,
                    "direction": self.SORT_DIRECTION,
                }
            ],
            separators=(",", ":"),
        )

        payload = self._build_payload(
            cmd="get",
            titulo="Celular",
            page=str(page),
            start=str(start),
            limit=str(limit),
            sort=ordenacao,
        )

        logger.info(
            "Iniciando listagem de celulares",
            extra={
                "event": "device_list_started",
                "page": page,
                "start": start,
                "limit": limit,
                "sort_property": self.SORT_PROPERTY,
                "sort_direction": self.SORT_DIRECTION,
            },
        )

        parsed_response = self._executar(
            payload,
            operacao="listar_celulares",
        )

        logger.info(
            "Listagem de celulares concluída",
            extra={
                "event": "device_list_finished",
                "page": page,
                "limit": limit,
            },
        )

        return parsed_response

    # === Normalização de dados ===
    def _normalizar_registros(
        self,
        resposta: Any,
    ) -> list[dict[str, Any]]:
        """
        Normaliza a resposta da API para uma lista de registros.
        """
        if not resposta:
            return []

        self._validar_resposta_negocio(
            resposta,
            operacao="normalizar_registros_celulares",
        )

        if isinstance(resposta, list):
            return [
                registro
                for registro in resposta
                if isinstance(registro, dict)
            ]

        if not isinstance(resposta, dict):
            response_type = type(
                resposta
            ).__name__

            logger.error(
                "A API retornou um formato de resposta inesperado",
                extra={
                    "event": "unexpected_api_response_format",
                    "response_type": response_type,
                },
            )

            raise ValueError(
                "Formato inesperado na resposta da API: "
                f"{response_type} - {resposta}"
            )

        chaves_de_listagem = (
            "itens",
            "data",
            "dados",
            "rows",
            "items",
            "records",
            "registros",
            "result",
            "resultado",
        )

        for chave in chaves_de_listagem:
            valor = resposta.get(chave)

            if isinstance(valor, list):
                return [
                    registro
                    for registro in valor
                    if isinstance(registro, dict)
                ]

            if isinstance(valor, dict):
                for chave_interna in chaves_de_listagem:
                    registros_internos = valor.get(
                        chave_interna
                    )

                    if isinstance(
                        registros_internos,
                        list,
                    ):
                        return [
                            registro
                            for registro
                            in registros_internos
                            if isinstance(
                                registro,
                                dict,
                            )
                        ]

                if self._extrair_codigo_registro(
                    valor
                ) is not None:
                    return [valor]

        if self._extrair_codigo_registro(
            resposta
        ) is not None:
            return [resposta]

        logger.error(
            "A resposta não contém registros de celulares",
            extra={
                "event": "device_records_not_found",
                "response_keys": list(
                    resposta.keys()
                ),
            },
        )

        raise ValueError(
            "A resposta da API não contém registros "
            "de celulares. "
            f"Chaves recebidas: {list(resposta.keys())}"
        )

    @staticmethod
    def _obter_ultima_comunicacao_registro(
        registro: dict[str, Any],
    ) -> str:
        """
        Obtém a última comunicação do registro.
        """
        return str(
            registro.get("dtultima_comunicacao")
            or registro.get("ultima_comunicacao")
            or registro.get("ultima comunicação")
            or registro.get("ultimaComunicacao")
            or registro.get("last_communication")
            or ""
        ).strip()

    @staticmethod
    def _obter_nome_pessoa_registro(
        registro: dict[str, Any],
    ) -> str:
        """
        Obtém o nome da pessoa utilizando as chaves conhecidas.
        """
        return str(
            registro.get("nmpessoa")
            or registro.get("nome_pessoa")
            or registro.get("nome pessoa")
            or registro.get("nomePessoa")
            or registro.get("person_name")
            or registro.get("pessoa")
            or ""
        ).strip()

    @staticmethod
    def _extrair_codigo_registro(
        registro: dict[str, Any],
    ) -> int | None:
        """
        Extrai o código do celular utilizando as chaves conhecidas.
        """
        codigo = (
            registro.get("codigo")
            or registro.get("cod")
            or registro.get("id")
            or registro.get("device_id")
            or registro.get("celular_codigo")
        )

        if codigo is None:
            return None

        try:
            return int(codigo)

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extrair_ativo_registro(
        registro: dict[str, Any],
    ) -> bool | None:
        """
        Interpreta o campo Ativo do registro.

        Diferente dos demais extractors, NÃO encadeia as chaves com
        'or': 'ativo' é booleano e um False legítimo seria descartado
        pelo curto-circuito, caindo indevidamente na próxima chave. A
        resolução é por presença de chave (primeira chave existente).

        Retorna None quando nenhuma chave conhecida existe ou quando o
        valor é irreconhecível, deixando a decisão de ativar com o
        chamador (que, por segurança, deve ativar no caso None).

        ATENÇÃO: as chaves e os valores abaixo são uma suposição
        baseada em backend legado (o payload de 'up' usa campo="ativo",
        mas isso não garante a mesma chave no 'get'). Confirme com um
        registro cru antes de confiar no skip:
            logger.info("registro cru", extra={"registro": registro})
        """
        chaves_ativo = (
            "ativo",
            "active",
            "is_active",
            "ativado",
            "flativo",
        )

        valor = None

        for chave in chaves_ativo:
            if chave in registro:
                valor = registro[chave]
                break

        if valor is None:
            return None

        if isinstance(valor, bool):
            return valor

        if isinstance(valor, (int, float)):
            return valor != 0

        texto = str(valor).strip().casefold()

        if texto in (
            "true",
            "1",
            "s",
            "sim",
            "t",
            "ativo",
        ):
            return True

        if texto in (
            "false",
            "0",
            "n",
            "nao",
            "não",
            "f",
            "inativo",
            "",
        ):
            return False

        return None

    # === Consultas de negócio ===
    def listar_registros_celular_por_nome_pessoa(
        self,
        nome_pessoa: str,
        page: int = DEFAULT_PAGE,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """
        Retorna os registros associados exatamente à pessoa informada.

        A filtragem é executada localmente para não depender de um
        parâmetro de pesquisa ainda não confirmado no contrato da API.
        """
        nome_pessoa_normalizado = nome_pessoa.strip()

        if not nome_pessoa_normalizado:
            raise ValueError(
                "O nome da pessoa não pode ser vazio."
            )

        resposta = self.listar_celulares(
            page=page,
            limit=limit,
        )

        registros = self._normalizar_registros(
            resposta
        )

        nome_esperado = (
            nome_pessoa_normalizado.casefold()
        )

        registros_da_pessoa = [
            registro
            for registro in registros
            if (
                self._obter_nome_pessoa_registro(
                    registro
                ).casefold()
                == nome_esperado
            )
            and self._extrair_codigo_registro(
                registro
            )
            is not None
        ]

        logger.info(
            "Registros da pessoa filtrados",
            extra={
                "event": "person_device_records_filtered",
                "person_name": nome_pessoa_normalizado,
                "total_records": len(registros),
                "matching_records": len(
                    registros_da_pessoa
                ),
            },
        )

        return registros_da_pessoa

    def obter_codigos_celular_por_nome_pessoa(
        self,
        nome_pessoa: str,
    ) -> set[int]:
        """
        Retorna os códigos cadastrados para a pessoa informada.
        """
        registros = (
            self.listar_registros_celular_por_nome_pessoa(
                nome_pessoa
            )
        )

        codigos: set[int] = set()

        for registro in registros:
            codigo = self._extrair_codigo_registro(
                registro
            )

            if codigo is not None:
                codigos.add(codigo)

        return codigos

    def obter_registro_celular_por_nome_pessoa(
        self,
        nome_pessoa: str,
        codigos_ignorados: set[int] | None = None,
    ) -> dict[str, Any]:
        """
        Retorna o registro da pessoa com a última comunicação
        mais recente.

        A API já retorna os registros ordenados por
        dtultima_comunicacao em ordem decrescente.

        Quando codigos_ignorados for informado, os registros
        correspondentes são desconsiderados.
        """
        nome_pessoa_normalizado = nome_pessoa.strip()

        if not nome_pessoa_normalizado:
            raise ValueError(
                "O nome da pessoa não pode ser vazio."
            )

        logger.info(
            "Iniciando busca do celular mais recente",
            extra={
                "event": "latest_device_record_lookup_started",
                "person_name": nome_pessoa_normalizado,
                "ignored_codes_count": len(
                    codigos_ignorados or set()
                ),
            },
        )

        registros = (
            self.listar_registros_celular_por_nome_pessoa(
                nome_pessoa_normalizado
            )
        )

        if codigos_ignorados:
            registros = [
                registro
                for registro in registros
                if self._extrair_codigo_registro(
                    registro
                )
                not in codigos_ignorados
            ]

        if not registros:
            raise ValueError(
                "Nenhum registro de celular foi encontrado "
                f"para '{nome_pessoa_normalizado}'."
            )

        # A API já retorna os registros ordenados por
        # dtultima_comunicacao em ordem decrescente.
        registro_mais_recente = registros[0]

        codigo = self._extrair_codigo_registro(
            registro_mais_recente
        )

        if codigo is None:
            raise ValueError(
                "O registro mais recente não possui "
                "identificador de celular."
            )

        logger.info(
            "Registro com a última comunicação mais recente localizado",
            extra={
                "event": "latest_device_record_found",
                "person_name": nome_pessoa_normalizado,
                "device_id": codigo,
                "ultima_comunicacao": (
                    self._obter_ultima_comunicacao_registro(
                        registro_mais_recente
                    )
                ),
            },
        )

        return registro_mais_recente

    def obter_codigo_celular_por_nome_pessoa(
        self,
        nome_pessoa: str,
        codigos_ignorados: set[int] | None = None,
    ) -> int:
        """
        Retorna o código da pessoa com a última comunicação
        mais recente.
        """
        registro = (
            self.obter_registro_celular_por_nome_pessoa(
                nome_pessoa=nome_pessoa,
                codigos_ignorados=codigos_ignorados,
            )
        )

        codigo = self._extrair_codigo_registro(
            registro
        )

        if codigo is None:
            raise ValueError(
                "Não foi possível encontrar o identificador "
                f"do celular para '{nome_pessoa.strip()}'."
            )

        return codigo

    def aguardar_e_ativar_celular_mais_recente(
        self,
        nome_pessoa: str,
        codigos_anteriores: set[int] | None = None,
        timeout: float = 60,
        poll_interval: float = 2,
    ) -> int:
        """
        Aguarda o registro com a última comunicação mais recente
        e garante que seu checkbox Ativo esteja marcado.

        Quando codigos_anteriores for informado, somente um código
        criado após o início do fluxo será considerado.

        Idempotência: quando o registro já indica ativo=True, a
        ativação é ignorada (não emite o POST de 'up'). Isso permite
        reutilizar o mesmo fluxo em plataformas onde o celular já sobe
        ativo (ex.: Android, que não bloqueia o device por cold start),
        sem esperar nem reativar à toa. Quando o estado é desconhecido
        (_extrair_ativo_registro retorna None), ativa por segurança.
        """
        nome_pessoa_normalizado = nome_pessoa.strip()

        if not nome_pessoa_normalizado:
            raise ValueError(
                "O nome da pessoa não pode ser vazio."
            )

        if timeout <= 0:
            raise ValueError(
                "O timeout deve ser maior que zero."
            )

        if poll_interval <= 0:
            raise ValueError(
                "O intervalo de polling deve ser maior que zero."
            )

        limite = time.monotonic() + timeout
        ultimo_erro: Exception | None = None

        logger.info(
            "Aguardando o celular mais recente para ativação",
            extra={
                "event": "latest_device_activation_wait_started",
                "person_name": nome_pessoa_normalizado,
                "previous_codes_count": len(
                    codigos_anteriores or set()
                ),
                "timeout": timeout,
                "poll_interval": poll_interval,
            },
        )

        while time.monotonic() < limite:
            try:
                registro = (
                    self.obter_registro_celular_por_nome_pessoa(
                        nome_pessoa=nome_pessoa_normalizado,
                        codigos_ignorados=codigos_anteriores,
                    )
                )

                codigo = self._extrair_codigo_registro(
                    registro
                )

                if codigo is None:
                    raise ValueError(
                        "O registro mais recente não possui "
                        "identificador de celular."
                    )

                if self._extrair_ativo_registro(
                    registro
                ) is True:
                    logger.info(
                        "Celular mais recente já está ativo; "
                        "ativação ignorada (idempotente).",
                        extra={
                            "event": (
                                "latest_device_already_active"
                            ),
                            "person_name": (
                                nome_pessoa_normalizado
                            ),
                            "device_id": codigo,
                            "ultima_comunicacao": (
                                self
                                ._obter_ultima_comunicacao_registro(
                                    registro
                                )
                            ),
                        },
                    )

                    return codigo

                self.ativar_celular(
                    codigo
                )

                logger.info(
                    "Celular mais recente localizado e ativado",
                    extra={
                        "event": "latest_device_activated",
                        "person_name": nome_pessoa_normalizado,
                        "device_id": codigo,
                        "ultima_comunicacao": (
                            self
                            ._obter_ultima_comunicacao_registro(
                                registro
                            )
                        ),
                    },
                )

                return codigo

            except (
                ValueError,
                requests.RequestException,
            ) as error:
                ultimo_erro = error

                logger.info(
                    "Novo celular ainda não está disponível",
                    extra={
                        "event": "latest_device_activation_retry",
                        "person_name": nome_pessoa_normalizado,
                        "error": str(error),
                    },
                )

                time.sleep(poll_interval)

        raise TimeoutError(
            "Não foi possível localizar e ativar o celular "
            f"mais recente de '{nome_pessoa_normalizado}' "
            f"em até {timeout} segundos. "
            f"Último erro: {ultimo_erro}"
        )

    def resolver_codigo_celular(
        self,
        codigo: int | None = None,
        nome_pessoa: str | None = None,
    ) -> int:
        """
        Resolve o código pelo identificador direto
        ou pelo nome da pessoa.
        """
        if codigo is not None:
            try:
                codigo_resolvido = int(codigo)

            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Código do celular inválido: {codigo!r}"
                ) from error

            logger.info(
                "Código do celular recebido diretamente",
                extra={
                    "event": "device_code_received_directly",
                    "device_id": codigo_resolvido,
                },
            )

            return codigo_resolvido

        if nome_pessoa and nome_pessoa.strip():
            return (
                self.obter_codigo_celular_por_nome_pessoa(
                    nome_pessoa
                )
            )

        logger.error(
            "Nenhum identificador de celular foi informado",
            extra={
                "event": "device_identifier_not_provided",
            },
        )

        raise ValueError(
            "Informe 'codigo' ou 'nome_pessoa' "
            "para identificar o celular."
        )


# ==== CORTE AQUI: configuracao_app (configuracao_app_client.py) ====
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
            raise ValueError(
                "O slug da configuração não pode ser vazio."
            )

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