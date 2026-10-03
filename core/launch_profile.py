from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class LaunchProfile:
    """
    Estado em que o app deve subir para o teste atual.

    Descreve intenção de teste. Não lê variáveis de ambiente e não
    conhece capabilities: a tradução para o Appium é responsabilidade
    de config.capabilities.

    Sem launch arguments, ao contrário do iOS: o Android não tem o
    NSArgumentDomain que suprime os popups oportunistas e o lembrete
    (ver DECISOES.md, "Popups oportunistas suprimidos por launch
    argument"); eles são tratados por polling.

    Attributes:
        cold_start:
            True para fluxos que exigem instalação limpa.

        permissions:
            Intenção de permissões da sessão (core.privacy_services).
            No Android as permissões do manifest são concedidas pelo
            autoGrantPermissions na instalação; o conjunto fica no
            perfil para a fixture declarar o que o teste precisa.

        manter_estado:
            True para subir o app como a execução anterior o deixou
            (instalado e logado): noReset, sem desinstalar. Oposto de
            cold_start; os dois não podem estar ligados juntos. Com
            ambos False, vale o ANDROID_NO_RESET/ANDROID_FULL_RESET do
            env.
    """

    cold_start: bool = False
    permissions: frozenset[str] = field(default_factory=frozenset)
    manter_estado: bool = False

    def __post_init__(self) -> None:
        if self.cold_start and self.manter_estado:
            raise ValueError(
                "LaunchProfile não pode ter cold_start e manter_estado "
                "ao mesmo tempo."
            )

    def com_permissoes(
        self,
        *servicos: str,
    ) -> "LaunchProfile":
        """
        Retorna um novo perfil com permissões adicionais.
        """
        return replace(
            self,
            permissions=self.permissions | frozenset(servicos),
        )
