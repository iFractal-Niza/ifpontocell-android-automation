class AppAutomationError(Exception):
    """
    Erro de domínio da automação.

    Carrega contexto de tela/elemento/ação para aparecer no report,
    em vez de propagar exceções nativas com mensagem vazia.
    """

    def __init__(
        self,
        message: str,
        *,
        tela: str,
        elemento: str,
        acao: str,
    ) -> None:
        super().__init__(message)
        self.tela = tela
        self.elemento = elemento
        self.acao = acao


class LoginRejeitadoInesperado(AppAutomationError):
    """Levantada quando o app rejeita um login que deveria ser válido."""


class SistemaRejeitadoInesperado(AppAutomationError):
    """Levantada quando o app rejeita um nome de sistema que deveria ser válido."""


class ConexaoIndisponivel(AppAutomationError):
    """Levantada quando o app exibe o alerta de conexão com a internet indisponível."""


class AlertaInesperado(AppAutomationError):
    """
    Levantada quando o app exibe um alerta com título/botão conhecidos
    (mesmo componente dos demais popups tratados), mas com uma mensagem
    ainda sem locator específico.
    """
