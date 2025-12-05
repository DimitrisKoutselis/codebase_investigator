import uuid
from dataclasses import dataclass

from ..exceptions.domain_exceptions import InvalidSessionIdError


@dataclass(frozen=True)
class SessionId:
    """Immutable value object representing a unique session identifier."""

    value: str

    def __post_init__(self) -> None:
        try:
            uuid.UUID(self.value)
        except ValueError as e:
            raise InvalidSessionIdError(
                f"Invalid session ID format: {self.value}"
            ) from e

    @classmethod
    def generate(cls) -> "SessionId":
        """Generate a new unique session ID."""
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value
