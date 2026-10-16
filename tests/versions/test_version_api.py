import unittest
from unittest.mock import AsyncMock, patch

from pyromax import VersionApi, VersionCatalog
from pyromax.config import (
    AndroidEnvelopeMappingUserAgentConfigV11,
    BaseEnvelopeMappingUserAgentConfigV11,
    DesktopEnvelopeMappingUserAgentConfigV11,
    EnvelopeMapperConfigV11,
    ExtraConfig,
    WebEnvelopeMappingUserAgentConfigV11,
)
from pyromax.models import ApkBuildFingerprint, DeviceType
from pyromax.mapping.envelope.v11.payloads.models import (
    AppUserAgentMappingModel,
    MobileUserAgentMappingModel,
    WebUserAgentMappingModel,
)
from pyromax.utils.fingerpint import FingerprintGenerator
from pyromax.exceptions import VersionAlreadyExistsError, VersionNotFoundError


class VersionApiTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def make_fingerprint(build_number: int) -> ApkBuildFingerprint:
        return ApkBuildFingerprint(
            signature_scheme="v3",
            certificate_count=1,
            certificate_meta_sha256="00" * 32,
            certificate_sha256=["00" * 32],
            dex_meta_sha256="11" * 32,
            so_meta_sha256={"arm64-v8a": "22" * 32},
            build_number=build_number,
        )

    def test_recommended_version_is_bundled(self) -> None:
        version_api = VersionApi()

        fingerprint = version_api.resolve(version_api.recommended())

        self.assertEqual(version_api.recommended(), "26.25.0")
        self.assertEqual(fingerprint.build_number, 6790)
        self.assertEqual(version_api.recommended_pair(), ("26.25.0", 6790))
        self.assertIs(VersionCatalog, VersionApi)

    def test_user_agent_defaults_come_from_version_api(self) -> None:
        expected_version, expected_build = VersionApi().recommended_pair()

        for user_agent in (
            AndroidEnvelopeMappingUserAgentConfigV11(),
            DesktopEnvelopeMappingUserAgentConfigV11(),
        ):
            self.assertEqual(user_agent.app_version, expected_version)
            self.assertEqual(user_agent.build_number, expected_build)

    def test_http_user_agent_is_owned_by_payload_model(self) -> None:
        web = WebUserAgentMappingModel(header_user_agent="browser")
        desktop = AppUserAgentMappingModel(app_version="1.2.3", build_number=4)
        android = MobileUserAgentMappingModel(
            app_version="1.2.3",
            build_number=4,
            os_version="Android 15",
        )

        self.assertEqual(web.http_user_agent, "browser")
        self.assertEqual(desktop.http_user_agent, "OneMe Desktop/1.2.3.4")
        self.assertEqual(android.http_user_agent, "OneMe Android 15")

    def test_add_resolve_override_and_missing_version(self) -> None:
        version_api = VersionApi()
        fingerprint = version_api.resolve(version_api.recommended())
        version_api.add("test-version", fingerprint)

        self.assertIs(version_api.resolve("test-version"), fingerprint)
        with self.assertRaises(VersionAlreadyExistsError):
            version_api.add("test-version", fingerprint)

        replacement = fingerprint.model_copy(update={"build_number": 123})
        version_api.add("test-version", replacement, override=True)
        self.assertEqual(version_api.resolve("test-version").build_number, 123)

        with self.assertRaises(VersionNotFoundError):
            version_api.resolve("missing")

    async def test_remote_load_merges_validated_fingerprints(self) -> None:
        version_api = VersionApi(remote_url="https://example.test/versions.json")
        fingerprint = version_api.resolve(version_api.recommended()).model_copy(
            update={"build_number": 999}
        )

        with patch.object(
            version_api,
            "fetch",
            AsyncMock(return_value={"remote-version": fingerprint}),
        ) as fetch:
            result = await version_api.load()

        self.assertIs(result, version_api)
        self.assertEqual(version_api.resolve("remote-version").build_number, 999)
        fetch.assert_awaited_once_with()

    async def test_local_load_does_not_fetch(self) -> None:
        version_api = VersionApi()

        with patch.object(version_api, "fetch", AsyncMock()) as fetch:
            result = await version_api.load()

        self.assertIs(result, version_api)
        fetch.assert_not_awaited()

    async def test_fetch_requires_explicit_remote_url(self) -> None:
        version_api = VersionApi()

        self.assertIsNone(version_api.remote_url)
        with self.assertRaisesRegex(ValueError, "remote_url"):
            await version_api.fetch()

    def test_fingerprint_generator_accepts_catalog_models(self) -> None:
        fingerprint = self.make_fingerprint(1)
        generator = FingerprintGenerator({"test-version": fingerprint})

        result = generator.generate_fingerprint(
            version="test-version",
            device_id="device",
            calls_seed=1,
        )

        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result or b""), 96)
        self.assertIn(VersionApi.recommended(), generator.data)

    def test_user_agent_config_reports_version_capabilities(self) -> None:
        web = WebEnvelopeMappingUserAgentConfigV11()
        desktop = DesktopEnvelopeMappingUserAgentConfigV11()
        android = AndroidEnvelopeMappingUserAgentConfigV11(
            app_version="session-version",
            build_number=100,
        )

        self.assertTrue(web.supports_versioning)
        self.assertTrue(desktop.supports_versioning)
        self.assertTrue(android.supports_versioning)
        self.assertFalse(web.supports_app_fingerprint)
        self.assertFalse(desktop.supports_app_fingerprint)
        self.assertTrue(android.supports_app_fingerprint)
        self.assertEqual(android.app_version, "session-version")
        self.assertEqual(android.build_number, 100)

    async def test_web_config_accepts_app_version_without_fingerprint(self) -> None:
        config = ExtraConfig(
            mapper=EnvelopeMapperConfigV11(device_type=DeviceType.Web),
            app_version="web-version",
        )

        config.resolve_app_version()
        await config.resolve_app_fingerprint()

        self.assertEqual(config.app_version, "web-version")
        self.assertIsNone(config.app_fingerprint)
        self.assertEqual(
            getattr(config.mapper.user_agent_config, "app_version"),
            "web-version",
        )

    async def test_desktop_version_does_not_resolve_apk_fingerprint(self) -> None:
        version_api = VersionApi(remote_url="https://example.test/versions.json")
        config = ExtraConfig(
            mapper=EnvelopeMapperConfigV11(device_type=DeviceType.Desktop),
            app_version="desktop-version",
            version_api=version_api,
        )

        with patch.object(version_api, "load", AsyncMock()) as load:
            config.resolve_app_version()
            await config.resolve_app_fingerprint()

        load.assert_not_awaited()
        self.assertIsNone(config.app_fingerprint)
        self.assertEqual(
            getattr(config.mapper.user_agent_config, "app_version"),
            "desktop-version",
        )

    async def test_extra_config_resolves_version_once_by_priority(self) -> None:
        version_api = VersionApi()
        catalog_fingerprint = self.make_fingerprint(200)
        version_api.add("explicit-version", catalog_fingerprint)
        config = ExtraConfig(
            mapper=EnvelopeMapperConfigV11(
                device_type=DeviceType.Android,
                user_agent_config=AndroidEnvelopeMappingUserAgentConfigV11(
                    app_version="session-version",
                    build_number=100,
                ),
            ),
            app_version="explicit-version",
            version_api=version_api,
        )

        config.resolve_app_version()
        await config.resolve_app_fingerprint()

        self.assertEqual(config.app_version, "explicit-version")
        self.assertIs(config.app_fingerprint, catalog_fingerprint)
        self.assertEqual(
            getattr(config.mapper.user_agent_config, "app_version"),
            "explicit-version",
        )
        self.assertEqual(
            getattr(config.mapper.user_agent_config, "build_number"),
            200,
        )

    async def test_explicit_fingerprint_has_highest_priority(self) -> None:
        version_api = VersionApi(remote_url="https://example.test/versions.json")
        explicit_fingerprint = self.make_fingerprint(300)
        config = ExtraConfig(
            mapper=EnvelopeMapperConfigV11(device_type=DeviceType.Android),
            app_version="explicit-version",
            app_fingerprint=explicit_fingerprint,
            version_api=version_api,
        )

        with patch.object(version_api, "load", AsyncMock()) as load:
            config.resolve_app_version()
            await config.resolve_app_fingerprint()

        load.assert_not_awaited()
        self.assertIs(config.app_fingerprint, explicit_fingerprint)
        self.assertEqual(
            getattr(config.mapper.user_agent_config, "app_version"),
            "explicit-version",
        )
        self.assertEqual(
            getattr(config.mapper.user_agent_config, "build_number"),
            300,
        )

    def test_version_settings_require_supported_user_agent(self) -> None:
        config = ExtraConfig(
            mapper=EnvelopeMapperConfigV11(
                user_agent_config=BaseEnvelopeMappingUserAgentConfigV11(
                    device_type="UNKNOWN"
                )
            ),
            app_version="26.25.0",
        )

        with self.assertLogs("ExtraConfig", level="WARNING"):
            config.resolve_app_version()

    async def test_unknown_version_continues_without_fingerprint(self) -> None:
        config = ExtraConfig(
            mapper=EnvelopeMapperConfigV11(device_type=DeviceType.Android),
            app_version="missing",
        )

        config.resolve_app_version()
        await config.resolve_app_fingerprint()

        self.assertIsNone(config.app_fingerprint)
        self.assertEqual(
            getattr(config.mapper.user_agent_config, "app_version"),
            "missing",
        )

    def test_extra_config_owns_optional_version_settings(self) -> None:
        empty = ExtraConfig()
        self.assertIsNone(empty.app_version)
        self.assertIsNone(empty.app_fingerprint)
        self.assertIsNone(empty.resolved_version_api)

        version_api = VersionApi()
        with self.assertRaisesRegex(ValueError, "cannot be used together"):
            ExtraConfig(version_api=version_api, catalog=version_api)

        aliased = ExtraConfig(catalog=version_api)
        self.assertIs(aliased.resolved_version_api, version_api)

    def test_fingerprint_model_is_exported_from_models(self) -> None:
        self.assertEqual(
            ApkBuildFingerprint.__module__,
            "pyromax.models.ApkBuildFingerprint",
        )
