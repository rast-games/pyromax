import json
from importlib import resources
from typing import Any

import aiohttp

from ..models.ApkBuildFingerprint import ApkBuildFingerprint
from ..exceptions import VersionAlreadyExistsError, VersionNotFoundError


class VersionApi:
    """Catalog of Android MAX versions and their APK fingerprints.

    Built-in versions are available immediately. When ``remote_url`` is set,
    :meth:`load` merges that remote catalog over the bundled data.
    Network, HTTP, JSON, and validation errors are intentionally propagated.

    :param remote_url: Optional URL fetched when :meth:`load` is called.
    """

    RECOMMENDED_APP_VERSION = "26.25.0"

    def __init__(self, remote_url: str | None = None) -> None:
        self.path = resources.files("pyromax._data") / "apk_fingerprints.json"
        self.remote_url = remote_url
        self.versions = self._convert_data(self._load_fingerprints())

    @staticmethod
    def recommended() -> str:
        """Return the application version used by mobile clients by default."""

        return VersionApi.RECOMMENDED_APP_VERSION

    def recommended_pair(self) -> tuple[str, int]:
        """Return the recommended app version and its build number."""

        version = self.recommended()
        return version, self.resolve(version).build_number

    async def load(self) -> "VersionApi":
        """Load and merge remote versions when remote loading is enabled."""

        if self.remote_url is not None:
            self.versions.update(await self.fetch())
        return self

    def add(
        self,
        version: str,
        fingerprint: ApkBuildFingerprint,
        override: bool = False,
    ) -> None:
        """Add a version to this catalog."""

        if version in self.versions and not override:
            raise VersionAlreadyExistsError(version)
        self.versions[version] = fingerprint

    def resolve(self, version: str) -> ApkBuildFingerprint:
        """Resolve a version or raise :class:`VersionNotFoundError`."""

        try:
            return self.versions[version]
        except KeyError as error:
            raise VersionNotFoundError(version) from error

    async def fetch(self) -> dict[str, ApkBuildFingerprint]:
        if self.remote_url is None:
            raise ValueError("remote_url must be configured before fetching versions")

        async with (
            aiohttp.ClientSession() as session,
            session.get(self.remote_url) as response,
        ):
            response.raise_for_status()
            data = await response.json()

        if not isinstance(data, dict):
            raise ValueError("Version catalog response must be an object")
        return self._convert_data(data)

    def _load_fingerprints(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("Bundled version catalog must be an object")
        return data

    @staticmethod
    def _convert_data(data: dict[str, Any]) -> dict[str, ApkBuildFingerprint]:
        return {
            version: ApkBuildFingerprint.model_validate(fingerprint)
            for version, fingerprint in data.items()
        }


# PyMax calls this object VersionCatalog. Keep that spelling as a public alias
# while exposing the requested Pyromax-style VersionApi name.
VersionCatalog = VersionApi
