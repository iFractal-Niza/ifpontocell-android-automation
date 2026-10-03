from dataclasses import dataclass, field


@dataclass(frozen=True)
class LaunchProfile:
    """Intenção de inicialização da sessão Android."""

    cold_start: bool = False
    arguments: tuple[str, ...] = ()
    permissions: frozenset[str] = field(default_factory=frozenset)

    def com_argumentos(self, *argumentos: str) -> "LaunchProfile":
        # Mantido por compatibilidade; argumentos de processo não são usados
        # pela estratégia Android atual.
        return LaunchProfile(
            cold_start=self.cold_start,
            arguments=(*self.arguments, *argumentos),
            permissions=self.permissions,
        )

    def com_permissoes(self, *servicos: str) -> "LaunchProfile":
        return LaunchProfile(
            cold_start=self.cold_start,
            arguments=self.arguments,
            permissions=self.permissions | frozenset(servicos),
        )

    def sem_captura_simulada(self) -> "LaunchProfile":
        return self

    def com_captura_simulada(self, asset: str) -> "LaunchProfile":
        # API mantida para compatibilidade; fake capture era exclusiva do iOS.
        return self
