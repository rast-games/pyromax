class VersionNotFoundError(ValueError):
    """Raised when an application version is absent from the catalog."""

    def __init__(self, version: str) -> None:
        super().__init__(f"Could not find version {version} in registry")


class VersionAlreadyExistsError(ValueError):
    """Raised when adding a version that is already in the catalog."""

    def __init__(self, version: str) -> None:
        super().__init__(f"Version {version} already exists in registry")
