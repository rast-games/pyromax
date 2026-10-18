from .BaseMaxApiException import BaseMaxApiException


class CircuitBreakerOpenError(BaseMaxApiException):
    """Raised when an operation is rejected by an open circuit."""

    def __init__(self, retry_after: float, circuit: str | None = None) -> None:
        self.retry_after = max(0.0, retry_after)
        self.circuit = circuit
        circuit_name = f" {circuit!r}" if circuit is not None else ""
        super().__init__(
            f"Circuit breaker{circuit_name} is open; "
            f"retry in {self.retry_after:.3f} seconds"
        )


__all__ = ["CircuitBreakerOpenError"]
