from abc import ABC


class BaseInteractor(ABC):
    """Base class for user interaction implementations.

    The class intentionally has no domain-specific methods. Authentication and
    future interaction areas extend it with their own contracts.
    """

