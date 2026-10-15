import hashlib
import struct
from collections.abc import Mapping
from typing import Any

from ..models.ApkBuildFingerprint import ApkBuildFingerprint
from ..versions import VersionApi


class FingerprintGenerator:
    def __init__(
        self,
        versions: Mapping[str, ApkBuildFingerprint | Mapping[str, Any]] | None = None,
    ) -> None:
        """Initialize the fingerprint generator."""

        source: dict[str, ApkBuildFingerprint | Mapping[str, Any]] = {}
        source.update(self.load_fingerprints())
        if versions is not None:
            source.update(versions)
        self.data = {
            version: (
                fingerprint
                if isinstance(fingerprint, ApkBuildFingerprint)
                else ApkBuildFingerprint.model_validate(fingerprint)
            )
            for version, fingerprint in source.items()
        }

    def load_fingerprints(self) -> dict[str, ApkBuildFingerprint]:
        """Load fingerprints through the version catalog."""

        return dict(VersionApi().versions)

    def generate_fingerprint(
        self,
        version: str,
        device_id: str,
        calls_seed: int,
        arch: str = "arm64-v8a",
    ) -> bytes | None:
        """Generate fingerprint.

        :param version: The version value.
        :type version: str
        :param device_id: Identifier of the device.
        :type device_id: str
        :param calls_seed: The calls seed value.
        :type calls_seed: int
        :param arch: The arch value.
        :type arch: str
        :returns: The resulting bytes | None value.
        :rtype: bytes | None
        """
        model = self.data.get(version)
        if model is None:
            return None

        seed_bytes = struct.pack(">q", calls_seed)
        device_bytes = device_id.encode("utf-8")

        h1 = hashlib.sha256(
            bytes.fromhex(model.certificate_meta_sha256) + seed_bytes + device_bytes
        ).digest()
        h2 = hashlib.sha256(
            bytes.fromhex(model.dex_meta_sha256) + seed_bytes + device_bytes
        ).digest()
        h3 = hashlib.sha256(
            bytes.fromhex(model.so_meta_sha256[arch]) + seed_bytes + device_bytes
        ).digest()

        return h1 + h2 + h3
