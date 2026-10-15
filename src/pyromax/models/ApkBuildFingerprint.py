from pydantic import BaseModel


class ApkBuildFingerprint(BaseModel):
    """Hashes and build metadata for one Android MAX release."""

    signature_scheme: str
    certificate_count: int
    certificate_meta_sha256: str
    certificate_sha256: list[str]
    dex_meta_sha256: str
    so_meta_sha256_arm64_v8a: str | None = None
    so_meta_sha256: dict[str, str]
    build_number: int
