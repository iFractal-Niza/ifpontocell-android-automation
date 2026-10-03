import json
import logging
import os
import uuid
from datetime import datetime, timezone

# =========================
# EXECUÇÃO GLOBAL
# =========================
# Identificador único gerado uma vez por execução — compartilhado em
# todos os logs
EXECUTION_ID = str(uuid.uuid4())


# =========================
# FORMATADORES
# =========================
class JsonFormatter(logging.Formatter):
    """
    Formata logs em JSON estruturado para observabilidade.

    Inclui timestamp UTC, nível, logger, mensagem e execution_id.
    Campos extras passados via extra={} são adicionados automaticamente,
    exceto os atributos reservados do LogRecord.
    """

    RESERVED_ATTRS = frozenset(
        {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        """
        Serializa o LogRecord em JSON, com fallback para string em caso
        de erro.
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "execution_id": EXECUTION_ID,
        }

        # Adiciona campos extras vindos de extra={}
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and key not in log_data:
                log_data[key] = value

        # Adiciona exception se existir
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        try:
            return json.dumps(log_data, ensure_ascii=False)
        except Exception:
            log_data["serialization_error"] = True
            return json.dumps(
                {k: str(v) for k, v in log_data.items()},
                ensure_ascii=False,
            )


class ConsoleFormatter(logging.Formatter):
    """
    Formata logs para leitura humana no terminal.

    Exibe hora, nível e mensagem em formato compacto.
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"{timestamp} | {record.levelname} | {record.getMessage()}"


# =========================
# HELPERS INTERNOS
# =========================
def _resolve_log_level() -> int:
    """
    Resolve o nível de log com base na variável de ambiente LOG_LEVEL.
    Usa INFO como padrão quando a variável não está definida ou é inválida.
    """
    env_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, env_log_level, logging.INFO)


def _build_console_handler() -> logging.Handler:
    """
    Cria handler para saída legível no terminal usando ConsoleFormatter.
    """
    console_handler = logging.StreamHandler()
    console_handler.setLevel(_resolve_log_level())
    console_handler.setFormatter(ConsoleFormatter())
    return console_handler


def _build_json_handler() -> logging.Handler:
    """
    Cria handler JSON para observabilidade usando JsonFormatter.

    Reservado para uso futuro — ativar em get_logger quando a saída
    em arquivo ou sistema de log centralizado for necessária.
    """
    json_handler = logging.StreamHandler()
    json_handler.setLevel(_resolve_log_level())
    json_handler.setFormatter(JsonFormatter())
    return json_handler


# =========================
# LOGGER FACTORY
# =========================
def get_logger(name: str = "automation") -> logging.Logger:
    """
    Retorna logger configurado para uso no projeto.

    Evita duplicação de handlers em chamadas repetidas.
    Por padrão, usa ConsoleFormatter para leitura humana no terminal.
    Para ativar saída JSON estruturada, adicionar _build_json_handler().
    """
    project_logger = logging.getLogger(name)

    # Evita duplicação de handlers
    if project_logger.handlers:
        return project_logger

    project_logger.setLevel(_resolve_log_level())
    project_logger.propagate = False

    # Terminal limpo e legível
    project_logger.addHandler(_build_console_handler())

    return project_logger


# =========================
# HELPERS DE LOG
# =========================
def log_event(project_logger: logging.Logger, message: str, **kwargs) -> None:
    """
    Registra um evento informativo com campos extras estruturados.
    """
    project_logger.info(message, extra=kwargs)


def log_warning(
    project_logger: logging.Logger,
    message: str,
    **kwargs,
) -> None:
    """
    Registra um aviso com campos extras estruturados.
    """
    project_logger.warning(message, extra=kwargs)


def log_error(project_logger: logging.Logger, message: str, **kwargs) -> None:
    """
    Registra um erro com campos extras estruturados.
    """
    project_logger.error(message, extra=kwargs)
