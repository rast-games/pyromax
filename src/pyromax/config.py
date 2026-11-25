from __future__ import annotations

import json
import logging
import time
import random
from collections.abc import Mapping
from copy import deepcopy
from itertools import product
from logging import Logger
from typing import Any, ClassVar, cast, Self
from uuid import uuid4
from abc import ABC

from pydantic import (
    ConfigDict,
    BaseModel,
    Field,
    model_validator,
    PrivateAttr,
)

from .models import (
    RegistrationConfig,
    TransportRegistry,
    EncodingRegistry,
    ProtocolRegistry,
    MapperRegistry,
    DeviceType,
    BaseDeviceType,
    DeviceTypeLike,
    ApkBuildFingerprint,
)
from .models.enum.Registrys import BaseRegistry
from .models.Session import SessionInfo, SyncOverrides
from .session import BaseSessionStorage
from .interaction import AuthInteractor
from .versions import VersionApi

from .utils import get_random_device_id, get_random_device_id_numeric

ANDROID_DEVICES: tuple[tuple[str, str, str, str], ...] = (
    ("Samsung SM-A525F", "Android 13", "405dpi 405dpi 1080x2400", "arm64-v8a"),
    ("Samsung SM-A536B", "Android 14", "405dpi 405dpi 1080x2400", "arm64-v8a"),
    ("Samsung SM-A546E", "Android 14", "405dpi 405dpi 1080x2340", "arm64-v8a"),
    ("Samsung SM-G991B", "Android 14", "421dpi 421dpi 1080x2400", "arm64-v8a"),
    ("Samsung SM-G998B", "Android 13", "515dpi 515dpi 1440x3200", "arm64-v8a"),
    ("Samsung SM-S901B", "Android 14", "425dpi 425dpi 1080x2340", "arm64-v8a"),
    ("Samsung SM-S911B", "Android 14", "425dpi 425dpi 1080x2340", "arm64-v8a"),
    ("Xiaomi 2109119DG", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Xiaomi 2201117TG", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Xiaomi 2201123G", "Android 14", "526dpi 526dpi 1440x3200", "arm64-v8a"),
    ("Xiaomi 2210132G", "Android 14", "446dpi 446dpi 1220x2712", "arm64-v8a"),
    (
        "Xiaomi 23049PCD8G",
        "Android 14",
        "446dpi 446dpi 1220x2712",
        "arm64-v8a",
    ),
    ("Redmi 2201116TG", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Redmi 22101316G", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Redmi 23021RAA2Y", "Android 14", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("POCO 22011211G", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("POCO 23049PCD8G", "Android 14", "446dpi 446dpi 1220x2712", "arm64-v8a"),
    ("Pixel 6", "Android 14", "411dpi 411dpi 1080x2400", "arm64-v8a"),
    ("Pixel 6a", "Android 14", "429dpi 429dpi 1080x2400", "arm64-v8a"),
    ("Pixel 7", "Android 14", "416dpi 416dpi 1080x2400", "arm64-v8a"),
    ("Pixel 7 Pro", "Android 14", "512dpi 512dpi 1440x3120", "arm64-v8a"),
    ("Pixel 8", "Android 14", "428dpi 428dpi 1080x2400", "arm64-v8a"),
    ("OnePlus NE2213", "Android 14", "525dpi 525dpi 1440x3216", "arm64-v8a"),
    ("OnePlus CPH2449", "Android 14", "451dpi 451dpi 1240x2772", "arm64-v8a"),
    ("realme RMX3085", "Android 13", "409dpi 409dpi 1080x2400", "arm64-v8a"),
    ("realme RMX3370", "Android 13", "409dpi 409dpi 1080x2400", "arm64-v8a"),
    ("realme RMX3630", "Android 13", "400dpi 400dpi 1080x2412", "arm64-v8a"),
    ("HUAWEI ELS-NX9", "Android 12", "441dpi 441dpi 1080x2340", "arm64-v8a"),
    ("HUAWEI VOG-L29", "Android 12", "398dpi 398dpi 1080x2340", "arm64-v8a"),
    ("HONOR RMO-NX1", "Android 13", "391dpi 391dpi 1080x2388", "arm64-v8a"),
    ("HONOR REA-NX9", "Android 13", "435dpi 435dpi 1200x2664", "arm64-v8a"),
)
LOCALE_TIMEZONES: tuple[tuple[str, str], ...] = (
    ("ru", "Europe/Moscow"),
    ("ru", "Europe/Kaliningrad"),
    ("ru", "Europe/Samara"),
    ("ru", "Asia/Yekaterinburg"),
    ("ru", "Asia/Omsk"),
    ("ru", "Asia/Novosibirsk"),
    ("ru", "Asia/Krasnoyarsk"),
    ("ru", "Asia/Irkutsk"),
    ("ru", "Asia/Yakutsk"),
    ("ru", "Asia/Vladivostok"),
)
WEB_APP_VERSION = "26.11.9"
WEB_SCREEN = "1080x1920 1.0x"

DEFAULT_WEB_HEADER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0"
)


NOT_HAS = object()


class BaseConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # def __getattr__(self, name: str):
    #     return NOT_HAS


class BaseTransportConfig(BaseConfig):
    pass


class SocketTransportConfig(BaseTransportConfig):
    host: str = "api.oneme.ru"
    port: int = 443
    proxy: str | None = None
    use_ssl: bool = True


class WebSocketTransportConfig(BaseTransportConfig):
    url: str = "wss://api.oneme.ru/websocket"
    proxy: str | None = None
    origin: str = "https://web.max.ru"
    user_agent_header: str = DEFAULT_WEB_HEADER_USER_AGENT
    max_size: int = 1024 * 1024 * 10


class BaseEncodingConfig(BaseConfig):
    pass


class JsonEncodingConfig(BaseEncodingConfig):
    pass


class MsgPackDictEncodingConfig(BaseEncodingConfig):
    pass


class NoEncodingConfig(BaseEncodingConfig):
    pass


class BaseProtocolConfig(BaseConfig):
    pass


class EnvelopeProtocolConfig(BaseProtocolConfig):
    sending_timeout: int = 10
    max_seq: int | float = 65_535


class BaseEnvelopeMappingUserAgentConfigV11(BaseConfig):
    device_type: str
    locale: str = "ru"
    device_id: str = Field(default_factory=get_random_device_id)
    timezone: str = "Europe/Moscow"
    device_locale: str = "ru"
    os_version: str = "Windows 10 Version 22H2"
    device_name: str = "WINDOWS10"
    client_session_id: int = Field(default_factory=lambda: random.randint(1, 30))

    @property
    def is_custom_device_id(self) -> bool:
        return "device_id" in self.model_fields_set

    @property
    def supports_versioning(self) -> bool:
        return "app_version" in type(self).model_fields

    @property
    def supports_app_fingerprint(self) -> bool:
        return False

    def to_string(self) -> str:
        parts = [f"type={type(self).__name__}"]
        for field_name, field_value in self.model_dump().items():
            if isinstance(field_value, dict):
                field_value = json.dumps(field_value)
            parts.append(f"{field_name}={field_value}")

        return ",".join(parts)

    @classmethod
    def from_string(cls: type[Self], string: str) -> Self:
        string = string.strip(",")
        parts = (part.split("=", maxsplit=1) for part in string.split(","))
        attrs = {field_name: field_value for field_name, field_value in tuple(parts)}
        user_agent_config_types = {cls.__name__: cls}
        user_agent_config_types.update(
            {subcls.__name__: subcls for subcls in cls.__subclasses__()}
        )

        user_agent_config_type_name = attrs["type"]
        user_agent_config_type = user_agent_config_types.get(
            user_agent_config_type_name
        )
        if user_agent_config_type is None:
            raise ValueError("Invalid user_agent_config_type")

        return user_agent_config_type.model_validate(attrs)

    @classmethod
    def from_session_info(
        cls: type[Self], session_info: SessionInfo, *args: Any, **kwargs: Any
    ) -> Self:
        if session_info.user_agent_config is None:
            raise ValueError("Session does not contain a user-agent configuration")
        restored_config = cls.from_string(session_info.user_agent_config)

        restored_data = restored_config.model_dump()
        restored_data["device_id"] = session_info.device_id
        restored_data.update(kwargs)

        restored_type = type(restored_config)

        return restored_type(
            *args,
            **restored_data,
        )

    @property
    def session_info_params(self) -> dict[str, Any]:
        return {}


class WebEnvelopeMappingUserAgentConfigV11(BaseEnvelopeMappingUserAgentConfigV11):
    device_type: str = DeviceType.Web
    device_id: str = Field(default_factory=get_random_device_id)
    header_user_agent: str = DEFAULT_WEB_HEADER_USER_AGENT
    app_version: str = WEB_APP_VERSION
    screen: str = WEB_SCREEN
    client_session_id: int = Field(default_factory=lambda: round(time.time() * 1000))


default_app_version, default_build_number = VersionApi().recommended_pair()


class DesktopEnvelopeMappingUserAgentConfigV11(BaseEnvelopeMappingUserAgentConfigV11):
    device_type: str = DeviceType.Desktop
    screen: str = "2.0x"
    device_id: str = Field(default_factory=get_random_device_id_numeric)
    build_number: int = default_build_number
    app_version: str = default_app_version


class AndroidEnvelopeMappingUserAgentConfigV11(BaseEnvelopeMappingUserAgentConfigV11):
    device_type: str = DeviceType.Android
    os_version: str = "Android 13"
    arch: str = "arm64-v8a"
    device_name: str = "Samsung SM-A525F"
    push_device_type: str = "GCM"
    app_version: str = default_app_version
    build_number: int = default_build_number
    device_id: str = Field(default_factory=lambda: str(uuid4()))
    mt_instance_id: str = Field(
        default_factory=lambda: str(uuid4()),
    )

    @property
    def supports_app_fingerprint(self) -> bool:
        return True

    @classmethod
    def from_session_info(
        cls: type[Self],
        session_info: SessionInfo,
        *args: Any,
        **kwargs: Any,
    ) -> Self:
        return super().from_session_info(
            session_info,
            *args,
            mt_instance_id=session_info.mt_instance_id,
            **kwargs,
        )

    @property
    def session_info_params(self) -> dict[str, Any]:
        return {
            "mt_instance_id": self.mt_instance_id,
        }


class BaseMapperConfig(BaseConfig, ABC):
    token: str | None = None
    password: str | None = None
    device_type: DeviceTypeLike
    phone: str | None = None
    user_agent_config: BaseEnvelopeMappingUserAgentConfigV11 = (
        WebEnvelopeMappingUserAgentConfigV11()
    )

    @property
    def is_custom_user_agent_config(self) -> bool:
        return "user_agent_config" in self.model_fields_set


class CircuitBreakerConfig(BaseConfig):
    """Failure policy for one category of operations."""

    enabled: bool = True
    failure_threshold: int = Field(default=1, ge=1)
    recovery_timeout: float = Field(default=1.0, ge=0)
    max_cycles: int = Field(default=5, ge=0)
    backoff_factor: float = Field(default=2.75, ge=1)
    max_recovery_timeout: float = Field(default=30.0, ge=0)
    wait_when_open: bool = True

    @model_validator(mode="after")
    def validate_recovery_timeouts(self) -> Self:
        if self.max_recovery_timeout < self.recovery_timeout:
            raise ValueError(
                "max_recovery_timeout cannot be less than recovery_timeout"
            )
        return self


class MappingCircuitBreakersConfig(BaseConfig):
    """Independent failure policies for mapper transport and API errors."""

    transport: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    api: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)


class EnvelopeMapperConfigV11(BaseMapperConfig):
    token: str | None = None
    protocol_version: int = 11
    device_type: DeviceTypeLike = DeviceType.Web
    password: str | None = None
    phone: str | None = None
    sms_auth: bool = False
    interactive: bool = True
    keepalive_ping_interval: int = 30
    connect_timeout: int | None = None
    user_agents_per_device_type: dict[
        DeviceTypeLike, type[BaseEnvelopeMappingUserAgentConfigV11]
    ] = Field(
        default_factory=lambda: {
            DeviceType.Android: AndroidEnvelopeMappingUserAgentConfigV11,
            DeviceType.Web: WebEnvelopeMappingUserAgentConfigV11,
            DeviceType.Desktop: DesktopEnvelopeMappingUserAgentConfigV11,
        }
    )
    user_agent_config: BaseEnvelopeMappingUserAgentConfigV11 = (
        WebEnvelopeMappingUserAgentConfigV11()
    )
    registration_config: RegistrationConfig | None = None
    use_mobile_fingerprint: bool = True
    use_telemetry: bool = True
    request_timeout: float = 30.0
    circuit_breakers: MappingCircuitBreakersConfig = Field(
        default_factory=MappingCircuitBreakersConfig
    )
    mapper_logger: Logger | None = None

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        original_fields_set = self.model_fields_set.copy()

        device_type = self.device_type
        if "sms_auth" not in original_fields_set:
            self.sms_auth = False if device_type == DeviceType.Web else True
        if "user_agent_config" not in original_fields_set:
            user_agent_config_per_device_type = self.user_agents_per_device_type.get(
                device_type
            )
            user_agent_config = (
                user_agent_config_per_device_type
                or WebEnvelopeMappingUserAgentConfigV11
            )
            self.user_agent_config = user_agent_config()
        self.__pydantic_fields_set__ = original_fields_set
        return self

    def register_user_agent_config(
        self,
        device_type: DeviceTypeLike,
        user_agent_config: type[BaseEnvelopeMappingUserAgentConfigV11],
    ) -> None:
        if not issubclass(user_agent_config, BaseEnvelopeMappingUserAgentConfigV11):
            raise TypeError(
                "user_agent_config must inherit "
                "BaseEnvelopeMappingUserAgentConfigV11"
            )

        original_fields_set = self.model_fields_set.copy()
        self.user_agents_per_device_type[device_type] = user_agent_config
        if (
            device_type == self.device_type
            and "user_agent_config" not in original_fields_set
        ):
            self.user_agent_config = user_agent_config()
        self.__pydantic_fields_set__ = original_fields_set


ConfigPreset = tuple[BaseRegistry, BaseRegistry, BaseRegistry, BaseRegistry]
ConfigPresetOverrides = tuple[
    BaseRegistry | None,
    BaseRegistry | None,
    BaseRegistry | None,
    BaseRegistry | None,
]
ConfigSetsRegistry = dict[
    DeviceTypeLike | str,
    list[ConfigPreset],
]
ConfigsPerRegistry = dict[
    type[BaseRegistry],
    dict[BaseRegistry | None, type[BaseConfig]],
]


CONFIG_SETS: ConfigSetsRegistry = {
    DeviceType.Web: [
        (
            TransportRegistry.WebSocketTransport,
            EncodingRegistry.MsgPackDictEncoding,
            ProtocolRegistry.EnvelopeProtocol,
            MapperRegistry.EnvelopeV11Mapper,
        ),
        (
            TransportRegistry.SocketTransport,
            EncodingRegistry.MsgPackDictEncoding,
            ProtocolRegistry.EnvelopeProtocol,
            MapperRegistry.EnvelopeV11Mapper,
        ),
    ],
    DeviceType.Desktop: [
        (
            TransportRegistry.SocketTransport,
            EncodingRegistry.MsgPackDictEncoding,
            ProtocolRegistry.EnvelopeProtocol,
            MapperRegistry.EnvelopeV11Mapper,
        ),
    ],
    DeviceType.Android: [
        (
            TransportRegistry.SocketTransport,
            EncodingRegistry.MsgPackDictEncoding,
            ProtocolRegistry.EnvelopeProtocol,
            MapperRegistry.EnvelopeV11Mapper,
        ),
    ],
}


def register_config_set(
    device_type: DeviceTypeLike | str,
    configuration: ConfigPreset,
    configs_sets_registry: ConfigSetsRegistry | None = None,
) -> None:
    if configs_sets_registry is None:
        configs_sets_registry = CONFIG_SETS

    if device_type not in configs_sets_registry:
        configs_sets_registry[device_type] = []
    if configuration not in configs_sets_registry[device_type]:
        configs_sets_registry[device_type].append(configuration)


default_transport_config = WebSocketTransportConfig
default_encoding_config = JsonEncodingConfig
default_protocol_config = EnvelopeProtocolConfig
default_mapper_config = EnvelopeMapperConfigV11


class Default:
    pass


class DefaultTransportConfig(default_transport_config, Default):
    pass


class DefaultEncodingConfig(default_encoding_config, Default):
    pass


class DefaultProtocolConfig(default_protocol_config, Default):
    pass


class DefaultMapperConfig(default_mapper_config, Default):
    pass


CONFIGS_PER_REGISTRY_ITEM: ConfigsPerRegistry = {
    TransportRegistry: {
        TransportRegistry.WebSocketTransport: WebSocketTransportConfig,
        TransportRegistry.SocketTransport: SocketTransportConfig,
    },
    ProtocolRegistry: {
        ProtocolRegistry.EnvelopeProtocol: EnvelopeProtocolConfig,
    },
    EncodingRegistry: {
        EncodingRegistry.JsonEncoding: JsonEncodingConfig,
        EncodingRegistry.MsgPackDictEncoding: MsgPackDictEncodingConfig,
        EncodingRegistry.NoEncoding: NoEncodingConfig,
    },
    MapperRegistry: {MapperRegistry.EnvelopeV11Mapper: EnvelopeMapperConfigV11},
}


def _unwrap_keys(value: Any, d: dict[Any, Any]) -> set[Any]:
    unwrapped = set()
    for k, v in d.items():
        if isinstance(v, dict):
            unwrapped.update(_unwrap_keys(value, v))

            continue

        if v == value:
            unwrapped.add(k)
    return unwrapped


def _unwrap(d: dict[Any, Any]) -> dict[Any, Any]:
    unwrapped = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for kk, vv in _unwrap(v).items():
                if kk not in unwrapped:
                    unwrapped[kk] = vv
            continue

        if k not in unwrapped:
            unwrapped[k] = v
    return unwrapped


def _get_keys_to_config(value: Any, d: dict[Any, Any]) -> dict[Any, Any]:
    pass


# FROM_CONFIG_TO_REGISTRY_DEFAULT_SNAPSHOT = deepcopy(FROM_CONFIG_TO_REGISTRY)
CONFIGS_PER_REGISTRY_ITEM_DEFAULT_SNAPSHOT = deepcopy(CONFIGS_PER_REGISTRY_ITEM)


def register_config_to_registry(
    config: type[BaseConfig],
    registry: BaseRegistry,
    configs_per_registry: ConfigsPerRegistry | None = None,
) -> None:
    if configs_per_registry is None:
        # Default global scope
        configs_per_registry = CONFIGS_PER_REGISTRY_ITEM

    registry_family = type(registry)

    if registry_family not in configs_per_registry:
        configs_per_registry[registry_family] = {}
    configs_per_registry[registry_family][registry] = config


def from_config_to_registry(
    conf: type[BaseConfig],
    configs_per_registry: ConfigsPerRegistry | None = None,
) -> BaseRegistry | None:
    """Return first satisfied registry item."""

    if configs_per_registry is None:
        configs_per_registry = CONFIGS_PER_REGISTRY_ITEM

    if issubclass(conf, Default):
        defaults_map: dict[type[Default], type[BaseConfig]] = {
            DefaultTransportConfig: default_transport_config,
            DefaultEncodingConfig: default_encoding_config,
            DefaultProtocolConfig: default_protocol_config,
            DefaultMapperConfig: default_mapper_config,
        }
        conf = defaults_map[conf]

    for registrations in configs_per_registry.values():
        for registry, registered_config in registrations.items():
            if registered_config is conf:
                return registry
    return None


def from_registry_to_config(
    registry_family: type[BaseRegistry],
    reg: BaseRegistry | type[BaseConfig] | None,
    configs_per_registry: ConfigsPerRegistry | None = None,
) -> type[BaseConfig] | None:
    if configs_per_registry is None:
        # Default global scope
        configs_per_registry = CONFIGS_PER_REGISTRY_ITEM

    if registry_family not in configs_per_registry:
        logging.warning("registry family '%s' is not supported", registry_family)

    registrations = configs_per_registry.get(registry_family, {})
    if isinstance(reg, type) and issubclass(reg, BaseConfig):
        reg_resolved = from_config_to_registry(reg, configs_per_registry)
        resolved_config = registrations.get(reg_resolved)
        if resolved_config is not None:
            return resolved_config
        return next(
            (
                registered_config
                for registered_config in registrations.values()
                if registered_config is reg
            ),
            None,
        )
    return registrations.get(reg)


def get_defaults():
    def t():
        from .transport.registry import TRANSPORTS

        return TRANSPORTS

    def e():
        from .encoding.registry import ENCODINGS

        return ENCODINGS

    def p():
        from .protocol.registry import PROTOCOLS

        return PROTOCOLS

    def m():
        from .mapping.registry import MAPPERS

        return MAPPERS

    return t, e, p, m


TRANSPORTS, ENCODINGS, PROTOCOLS, MAPPERS = get_defaults()


class ExtraConfig(BaseConfig):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    transport: BaseTransportConfig = Field(default_factory=DefaultTransportConfig)
    encoding: BaseEncodingConfig = (
        DefaultEncodingConfig()
    )  # not used by now, for future
    protocol: BaseProtocolConfig = Field(default_factory=DefaultProtocolConfig)
    mapper: BaseMapperConfig = Field(default_factory=DefaultMapperConfig)

    transport_registry: Mapping[str, Any] = Field(default_factory=TRANSPORTS)
    encoding_registry: Mapping[str, Any] = Field(default_factory=ENCODINGS)
    protocol_registry: Mapping[str, Any] = Field(default_factory=PROTOCOLS)
    mapper_registry: Mapping[str, Any] = Field(default_factory=MAPPERS)

    session_storage: BaseSessionStorage | None = None
    auth_interactor: AuthInteractor | None = None
    work_dir: str = "."
    session_name: str = "session.db"
    session_id: str | None = None

    app_version: str | None = None
    app_fingerprint: ApkBuildFingerprint | None = None
    version_api: VersionApi | None = None
    catalog: VersionApi | None = None
    config_sets_source: ConfigSetsRegistry = Field(
        default_factory=lambda: deepcopy(CONFIG_SETS)
    )
    config_registry_source: ConfigsPerRegistry = Field(
        default_factory=lambda: deepcopy(CONFIGS_PER_REGISTRY_ITEM)
    )

    # directives
    restore_user_agent_from_session: bool = True
    auto_connect_after_init: bool = True
    strict_fingerprint_pair: bool = False
    reconnect: bool = True
    reconnect_delay: float = 1.0
    relogin: bool = True
    allow_registry_config_matching: bool = False
    autochange_app_version_if_current_unsupported: bool = True

    sync: SyncOverrides = Field(default_factory=SyncOverrides)

    _logger: ClassVar[Logger] = logging.getLogger("ExtraConfig")
    _current_preset: ConfigPreset | None = PrivateAttr(None)
    _register_configs_overrides: ConfigsPerRegistry = PrivateAttr(default_factory=dict)
    _config_sets_overrides: ConfigSetsRegistry = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def validate_version_api_aliases(self) -> Self:
        if self.version_api is not None and self.catalog is not None:
            raise ValueError("version_api and catalog cannot be used together")
        return self

    @property
    def resolved_version_api(self) -> VersionApi | None:
        return self.version_api or self.catalog

    def resolve_app_version(self) -> None:
        """Apply an explicit app version to a compatible user agent."""

        if self.app_version is None:
            return
        user_agent_config = self.mapper.user_agent_config
        if not user_agent_config.supports_versioning:
            self._logger.warning(
                "The selected user-agent configuration does not support app versions"
            )
            return

        self.mapper.user_agent_config = user_agent_config.model_copy(
            update={"app_version": self.app_version}
        )

    async def resolve_app_fingerprint(self) -> None:
        """Resolve and apply an Android APK fingerprint when requested."""

        user_agent_config = self.mapper.user_agent_config
        if not user_agent_config.supports_app_fingerprint:
            return

        fingerprint_requested = any(
            value is not None
            for value in (
                self.app_version,
                self.app_fingerprint,
                self.resolved_version_api,
            )
        )
        if not fingerprint_requested:
            return

        app_version = user_agent_config.app_version
        app_fingerprint = self.app_fingerprint
        if app_fingerprint is None:
            version_api = self.resolved_version_api or VersionApi()
            await version_api.load()
            if self.strict_fingerprint_pair:
                app_fingerprint = version_api.resolve(app_version)
            else:
                app_fingerprint = version_api.versions.get(app_version)
                if app_fingerprint is None:
                    self._logger.warning(
                        "Not found app fingerprint for selected app version"
                    )
                    return

        self.app_fingerprint = app_fingerprint
        self.mapper.user_agent_config = user_agent_config.model_copy(
            update={"build_number": app_fingerprint.build_number}
        )

    @property
    def _app_layers(self) -> tuple[BaseConfig, ...]:
        return self.transport, self.encoding, self.protocol, self.mapper

    def _search_available_config_presets(
        self,
        config_presets: list[ConfigPreset],
        overrides: ConfigPresetOverrides | None = None,
    ) -> list[ConfigPreset]:
        if overrides is None:
            overrides = (None, None, None, None)

        available_config_presets = []
        for config_preset in config_presets:
            for preset, override in zip(config_preset, overrides):
                if override is None:
                    continue
                if override == preset:
                    continue
                if not self.allow_registry_config_matching:
                    break

                preset_config = from_registry_to_config(
                    type(preset),
                    preset,
                    configs_per_registry=self._configs_per_registry,
                )
                override_config = from_registry_to_config(
                    type(override),
                    override,
                    configs_per_registry=self._configs_per_registry,
                )
                if override_config is None or override_config is not preset_config:
                    break
            else:
                available_config_presets.append(config_preset)
        return available_config_presets

    def _compute_all_combinations(
        self,
        available_config_presets: list[ConfigPreset],
    ) -> set[ConfigPreset]:

        allowed_combinations = {
            combination
            for config_presets in self._config_sets.values()
            for combination in config_presets
        }
        if not self.allow_registry_config_matching:
            return set(available_config_presets) & allowed_combinations

        configs_per_registry = self._configs_per_registry
        all_combinations: set[ConfigPreset] = set()
        for available_config_preset in available_config_presets:
            variants = []
            for registry_item in available_config_preset:
                config = from_registry_to_config(
                    type(registry_item),
                    registry_item,
                    configs_per_registry=configs_per_registry,
                )
                registry_variants = _unwrap_keys(config, configs_per_registry)
                variants.append(registry_variants or {registry_item})

            for combination in product(*variants):
                if combination in allowed_combinations:
                    all_combinations.add(combination)

        return all_combinations

    def _is_supported_config_mask(
        self,
        config_mask: ConfigPreset,
        config_presets: list[ConfigPreset],
    ) -> bool:
        if not self.allow_registry_config_matching:
            return config_mask in config_presets

        configs_per_registry = self._configs_per_registry
        for config_preset in config_presets:
            for selected, preset in zip(config_mask, config_preset):
                if selected == preset:
                    continue
                selected_config = from_registry_to_config(
                    type(selected),
                    selected,
                    configs_per_registry=configs_per_registry,
                )
                preset_config = from_registry_to_config(
                    type(preset),
                    preset,
                    configs_per_registry=configs_per_registry,
                )
                if selected_config is None or selected_config is not preset_config:
                    break
            else:
                return True
        return False

    @property
    def current_preset(
        self,
    ) -> ConfigPreset | None:
        return self._current_preset

    def register_config_to_registry(
        self,
        config: type[BaseConfig],
        registry: BaseRegistry,
    ) -> None:

        register_config_to_registry(
            config=config,
            registry=registry,
            configs_per_registry=self._register_configs_overrides,
        )

    @property
    def _config_sets(self) -> ConfigSetsRegistry:
        config_set = deepcopy(self.config_sets_source)
        for device_type, configurations in self._config_sets_overrides.items():
            merged_configurations = config_set.setdefault(device_type, [])
            for configuration in configurations:
                if configuration not in merged_configurations:
                    merged_configurations.append(configuration)

        return config_set

    def register_config_set(
        self,
        device_type: DeviceTypeLike | str,
        configuration: ConfigPreset,
    ) -> None:

        register_config_set(
            device_type=device_type,
            configuration=configuration,
            configs_sets_registry=self._config_sets_overrides,
        )

    @property
    def _configs_per_registry(
        self,
    ) -> ConfigsPerRegistry:
        registry = deepcopy(self.config_registry_source)
        for registry_family, registrations in self._register_configs_overrides.items():
            registry.setdefault(registry_family, {}).update(registrations)

        return registry

    def config_rebuild(
        self,
        transport: BaseRegistry | None,
        encoding: BaseRegistry | None,
        protocol: BaseRegistry | None,
        mapper: BaseRegistry | None,
    ) -> "ExtraConfig":

        device_type = self.mapper.device_type

        device_type_value = (
            device_type.value
            if isinstance(device_type, BaseDeviceType)
            else str(device_type)
        )
        config_presets = self._config_sets.get(device_type) or self._config_sets.get(
            device_type_value
        )
        if not config_presets:
            default_preset = (
                from_config_to_registry(
                    default_transport_config, self._configs_per_registry
                ),
                from_config_to_registry(
                    default_encoding_config, self._configs_per_registry
                ),
                from_config_to_registry(
                    default_protocol_config, self._configs_per_registry
                ),
                from_config_to_registry(
                    default_mapper_config, self._configs_per_registry
                ),
            )
            if any(registry is None for registry in default_preset):
                raise RuntimeError("default configuration registries are incomplete")
            config_presets = [cast(ConfigPreset, default_preset)]

        default_mask = config_presets[0]

        layer_names = ("transport", "encoding", "protocol", "mapper")
        layer_overrides = (transport, encoding, protocol, mapper)
        explicit_layer_names = {
            field_name
            for override, field_name in zip(layer_overrides, layer_names)
            if override is not None or field_name in self.model_fields_set
        }
        requested_registries: list[BaseRegistry | None] = []
        for override, field_name, config in zip(
            layer_overrides,
            layer_names,
            self._app_layers,
        ):
            requested_registries.append(
                override
                if override is not None
                else (
                    from_config_to_registry(type(config), self._configs_per_registry)
                    if field_name in self.model_fields_set
                    else None
                )
            )

        requested_preset = cast(ConfigPresetOverrides, tuple(requested_registries))
        config_masks = self._search_available_config_presets(
            config_presets,
            overrides=requested_preset,
        )

        all_combinations = self._compute_all_combinations(config_masks)

        base_mask = next(
            (preset for preset in config_presets if preset in all_combinations),
            config_presets[0],
        )
        config_mask = cast(
            ConfigPreset,
            tuple(
                requested if requested is not None else default
                for requested, default in zip(requested_registries, base_mask)
            ),
        )

        transport_config = (
            from_registry_to_config(
                type(config_mask[0]),
                config_mask[0],
                configs_per_registry=self._configs_per_registry,
            )
            or from_registry_to_config(
                type(default_mask[0]),
                default_mask[0],
                configs_per_registry=self._configs_per_registry,
            )
            or self.transport
        )

        encoding_config = (
            from_registry_to_config(
                type(config_mask[1]),
                config_mask[1],
                configs_per_registry=self._configs_per_registry,
            )
            or from_registry_to_config(
                type(default_mask[1]),
                default_mask[1],
                configs_per_registry=self._configs_per_registry,
            )
            or self.encoding
        )
        protocol_config = (
            from_registry_to_config(
                type(config_mask[2]),
                config_mask[2],
                configs_per_registry=self._configs_per_registry,
            )
            or from_registry_to_config(
                type(default_mask[2]),
                default_mask[2],
                configs_per_registry=self._configs_per_registry,
            )
            or self.protocol
        )
        mapper_config = (
            from_registry_to_config(
                type(config_mask[3]),
                config_mask[3],
                configs_per_registry=self._configs_per_registry,
            )
            or from_registry_to_config(
                type(default_mask[3]),
                default_mask[3],
                configs_per_registry=self._configs_per_registry,
            )
            or self.mapper
        )

        if not self._is_supported_config_mask(config_mask, config_presets):
            self._logger.warning(
                "Your chosen settings not found in presets, a big chance for errors."
            )

        mapper_user_agent_config = self.mapper.user_agent_config

        mapper_dump = self.mapper.model_dump()
        mapper_fields_to_preserve = {"user_agents_per_device_type"}
        for key in mapper_dump.copy():
            if (
                key not in self.mapper.model_fields_set
                and key not in mapper_fields_to_preserve
            ):
                del mapper_dump[key]
        if not self.mapper.is_custom_user_agent_config:
            mapper_dump.pop("user_agent_config", None)
        else:
            mapper_dump["user_agent_config"] = mapper_user_agent_config

        other_params = self.model_dump()
        other_params.pop("transport")
        other_params.pop("encoding")
        other_params.pop("protocol")
        other_params.pop("mapper")

        config_updated = ExtraConfig(
            transport=cast(
                BaseTransportConfig,
                transport_config.model_validate(self.transport.model_dump()),
            ),
            encoding=cast(
                BaseEncodingConfig,
                encoding_config.model_validate(self.encoding.model_dump()),
            ),
            protocol=cast(
                BaseProtocolConfig,
                protocol_config.model_validate(self.protocol.model_dump()),
            ),
            mapper=cast(BaseMapperConfig, mapper_config.model_validate(mapper_dump)),
            **other_params,
        )
        config_updated.__pydantic_fields_set__.difference_update(
            set(layer_names) - explicit_layer_names
        )
        config_updated._register_configs_overrides = deepcopy(
            self._register_configs_overrides
        )
        config_updated._config_sets_overrides = deepcopy(self._config_sets_overrides)
        config_updated._current_preset = config_mask

        return config_updated
