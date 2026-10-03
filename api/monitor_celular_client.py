"""
Cliente do menu "Monitor > Celular" do ifPonto (pag=monitor_celular).

Lista os aparelhos de todos os colaboradores que fizeram login no app,
ordenados pela última comunicação. Além dos checkboxes, concentra toda a
leitura-e-filtro (listagem, extractors, codigos_anteriores e a
orquestração de ativação com guard idempotente).
"""

import json
import time
from typing import Any

import requests

from api.ifponto_api_client import IfPontoApiClient
from utils.logger import get_logger

logger = get_logger(__name__)


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
    # CONFIRMAR nome real (por aparelho) dos dois campos abaixo.
    CAMPO_GPS_OBRIGATORIO = "gps_obrigatorio"
    CAMPO_SEM_FOTO = "sem_foto"

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
        registro = self.obter_registro_celular_por_nome_pessoa(nome_pessoa)

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
            raise ValueError("A página deve ser maior que zero.")

        if limit <= 0:
            raise ValueError("O limite deve ser maior que zero.")

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
                registro for registro in resposta if isinstance(registro, dict)
            ]

        if not isinstance(resposta, dict):
            response_type = type(resposta).__name__

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
                    registros_internos = valor.get(chave_interna)

                    if isinstance(
                        registros_internos,
                        list,
                    ):
                        return [
                            registro
                            for registro in registros_internos
                            if isinstance(
                                registro,
                                dict,
                            )
                        ]

                if self._extrair_codigo_registro(valor) is not None:
                    return [valor]

        if self._extrair_codigo_registro(resposta) is not None:
            return [resposta]

        logger.error(
            "A resposta não contém registros de celulares",
            extra={
                "event": "device_records_not_found",
                "response_keys": list(resposta.keys()),
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
    # Busca por pessoa: percorre a listagem inteira (de todos os celulares
    # do ambiente), página a página, até a última.
    LIMITE_POR_PAGINA_NA_BUSCA = 100
    MAX_PAGINAS_NA_BUSCA = 50

    def listar_registros_celular_por_nome_pessoa(
        self,
        nome_pessoa: str,
    ) -> list[dict[str, Any]]:
        """
        Retorna os registros associados exatamente à pessoa informada,
        do que se comunicou mais recentemente para o mais antigo.

        A filtragem é executada localmente para não depender de um
        parâmetro de pesquisa ainda não confirmado no contrato da API.
        Percorre todas as páginas: só a primeira (os 25 celulares que se
        comunicaram por último, de todo o ambiente) não achava o registro
        de um iPhone que não se comunicava havia algum tempo — no device
        real o login reaproveita o registro antigo, em vez de criar um.
        """
        nome_pessoa_normalizado = nome_pessoa.strip()

        if not nome_pessoa_normalizado:
            raise ValueError("O nome da pessoa não pode ser vazio.")

        registros = self._listar_todos_os_celulares()

        nome_esperado = nome_pessoa_normalizado.casefold()

        registros_da_pessoa = [
            registro
            for registro in registros
            if (
                self._obter_nome_pessoa_registro(registro).casefold()
                == nome_esperado
            )
            and self._extrair_codigo_registro(registro) is not None
        ]

        logger.info(
            "Registros da pessoa filtrados",
            extra={
                "event": "person_device_records_filtered",
                "person_name": nome_pessoa_normalizado,
                "total_records": len(registros),
                "matching_records": len(registros_da_pessoa),
            },
        )

        return registros_da_pessoa

    def _listar_todos_os_celulares(self) -> list[dict[str, Any]]:
        """
        A listagem inteira, página a página, na ordem da API (última
        comunicação, da mais recente para a mais antiga). Para na
        primeira página incompleta.
        """
        registros: list[dict[str, Any]] = []

        for pagina in range(1, self.MAX_PAGINAS_NA_BUSCA + 1):
            da_pagina = self._normalizar_registros(
                self.listar_celulares(
                    page=pagina, limit=self.LIMITE_POR_PAGINA_NA_BUSCA
                )
            )
            registros.extend(da_pagina)

            if len(da_pagina) < self.LIMITE_POR_PAGINA_NA_BUSCA:
                return registros

        logger.warning(
            "Listagem de celulares interrompida no limite de páginas",
            extra={
                "event": "device_list_page_limit",
                "max_pages": self.MAX_PAGINAS_NA_BUSCA,
            },
        )

        return registros

    def obter_codigos_celular_por_nome_pessoa(
        self,
        nome_pessoa: str,
    ) -> set[int]:
        """
        Retorna os códigos cadastrados para a pessoa informada.
        """
        registros = self.listar_registros_celular_por_nome_pessoa(nome_pessoa)

        codigos: set[int] = set()

        for registro in registros:
            codigo = self._extrair_codigo_registro(registro)

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
            raise ValueError("O nome da pessoa não pode ser vazio.")

        logger.info(
            "Iniciando busca do celular mais recente",
            extra={
                "event": "latest_device_record_lookup_started",
                "person_name": nome_pessoa_normalizado,
                "ignored_codes_count": len(codigos_ignorados or set()),
            },
        )

        registros = self.listar_registros_celular_por_nome_pessoa(
            nome_pessoa_normalizado
        )

        if codigos_ignorados:
            registros = [
                registro
                for registro in registros
                if self._extrair_codigo_registro(registro)
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

        codigo = self._extrair_codigo_registro(registro_mais_recente)

        if codigo is None:
            raise ValueError(
                "O registro mais recente não possui identificador de celular."
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
        registro = self.obter_registro_celular_por_nome_pessoa(
            nome_pessoa=nome_pessoa,
            codigos_ignorados=codigos_ignorados,
        )

        codigo = self._extrair_codigo_registro(registro)

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
            raise ValueError("O nome da pessoa não pode ser vazio.")

        if timeout <= 0:
            raise ValueError("O timeout deve ser maior que zero.")

        if poll_interval <= 0:
            raise ValueError("O intervalo de polling deve ser maior que zero.")

        limite = time.monotonic() + timeout
        ultimo_erro: Exception | None = None

        logger.info(
            "Aguardando o celular mais recente para ativação",
            extra={
                "event": "latest_device_activation_wait_started",
                "person_name": nome_pessoa_normalizado,
                "previous_codes_count": len(codigos_anteriores or set()),
                "timeout": timeout,
                "poll_interval": poll_interval,
            },
        )

        while time.monotonic() < limite:
            try:
                registro = self.obter_registro_celular_por_nome_pessoa(
                    nome_pessoa=nome_pessoa_normalizado,
                    codigos_ignorados=codigos_anteriores,
                )

                codigo = self._extrair_codigo_registro(registro)

                if codigo is None:
                    raise ValueError(
                        "O registro mais recente não possui "
                        "identificador de celular."
                    )

                if self._extrair_ativo_registro(registro) is True:
                    logger.info(
                        "Celular mais recente já está ativo; "
                        "ativação ignorada (idempotente).",
                        extra={
                            "event": ("latest_device_already_active"),
                            "person_name": (nome_pessoa_normalizado),
                            "device_id": codigo,
                            "ultima_comunicacao": (
                                self._obter_ultima_comunicacao_registro(
                                    registro
                                )
                            ),
                        },
                    )

                    return codigo

                self.ativar_celular(codigo)

                logger.info(
                    "Celular mais recente localizado e ativado",
                    extra={
                        "event": "latest_device_activated",
                        "person_name": nome_pessoa_normalizado,
                        "device_id": codigo,
                        "ultima_comunicacao": (
                            self._obter_ultima_comunicacao_registro(registro)
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
            return self.obter_codigo_celular_por_nome_pessoa(nome_pessoa)

        logger.error(
            "Nenhum identificador de celular foi informado",
            extra={
                "event": "device_identifier_not_provided",
            },
        )

        raise ValueError(
            "Informe 'codigo' ou 'nome_pessoa' para identificar o celular."
        )
