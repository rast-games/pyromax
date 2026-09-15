# MIN_PREFERRED_BUILD = 6712
import json
import logging
import time
from collections.abc import Callable, Coroutine
import random
from logging import Logger
from typing import Any, ClassVar, cast, Self
from uuid import uuid4
from abc import ABC, abstractmethod

from pydantic import (
    ConfigDict,
    BaseModel,
    Field,
    model_validator,
    PrivateAttr,
    field_validator,
)

from .encoding import MsgPackDictEncoding
from .models import (
    RegistrationConfig,
    TransportRegistry,
    EncodingRegistry,
    ProtocolRegistry,
    MapperRegistry,
    DeviceType,
)
from .models.enum.Registrys import BaseRegistry
from .models.Session import SessionInfo, SyncOverrides
from .session import BaseSessionStorage

from .utils import get_random_device_id, get_random_device_id_numeric

APP_VERSIONS: tuple[tuple[str, int], ...] = (
    ("26.25.0", 6790),
    ("26.24.0", 6784),
    ("26.23.2", 6779),
    ("26.23.1", 6778),
    ("26.23.0", 6777),
    ("26.22.2", 6773),
    ("26.22.1", 6772),
    ("26.22.0", 6770),
    ("26.21.1", 6763),
    ("26.20.2", 6758),
    ("26.20.1", 6740),
    ("26.19.3", 6734),
    ("26.19.2", 6732),
    ("26.19.1", 6729),
    # ("26.19.0", 6727),
    # ("26.18.4", 6724),
    # ("26.18.2", 6720),
    # ("26.18.1", 6716),
    # ("26.18.0", 6715),
    # ("26.17.1", 6712),
    # ("26.16.4", 6704),
    # ("26.16.3", 6702),
    # ("26.16.2", 6701),
    # ("26.16.1", 6700),
    # ("26.16.0", 6698),
    # ("26.15.3", 6695),
    # ("26.15.1", 6690),
    # ("26.15.0", 6689),
    # ("26.14.1", 6686),
    # ("26.14.0", 6685),
    # ("26.13.0", 6683),
    # ("26.12.2", 6681),
    # ("26.12.1", 6679),
    # ("26.12.0", 6676),
    # ("26.11.3", 6670),
    # ("26.11.2", 6669),
    # ("26.11.1", 6665),
    # ("26.10.1", 6653),
    # ("26.10.0", 6648),
    # ("26.9.1", 6643),
)
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
WEB_APP_VERSION = "26.7.15"
WEB_SCREEN = "1080x1920 1.0x"

DEFAULT_WEB_HEADER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0"
)

# PREFERRED_VERSION = [
#     version for version in APP_VERSIONS if version[1] >= MIN_PREFERRED_BUILD
# ]
# LEGACY_VERSIONS = [
#     version for version in APP_VERSIONS if version[1] < MIN_PREFERRED_BUILD
# ]


# class ClientConfig(BaseModel):
#     model_config = ConfigDict(arbitrary_types_allowed=True)
#
#     phone: str | None = None
#     work_dir: str = "."
#     session_name: str = "session.db"
#     device: DeviceConfig
#     token: str | None = None
#     proxy: str | None = None
#     registration_config: RegistrationConfig | None = None
#
#     host: str = "api.oneme.ru"
#     port: int = 443
#     use_ssl: bool = True
#
#     protocol_version: int = 10
#     request_timeout: float = 30.0
#     log_level: str = "INFO"
#     telemetry: bool = False
#
#     interactive: bool = True
#
#     store: StoreProtocol | None = None
#
#     sync: SyncOverrides = Field(default_factory=SyncOverrides)
#
#     def ensure_config(self) -> None:
#         if not self.phone:
#             raise ValueError("Phone must be provided when no saved session exists.")


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
    url: str = "wss://ws-api.oneme.ru/websocket"
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


# class TransportConfig(BaseModel):
#     socket: SocketTransportConfig
#     websocket: WebSocketTransportConfig


class BaseProtocolConfig(BaseConfig):
    pass


class EnvelopeProtocolConfig(BaseProtocolConfig):
    pass


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

        return user_agent_config_type(**attrs)

    @classmethod
    def from_session_info(
        cls: type[Self], session_info: SessionInfo, *args: Any, **kwargs: Any
    ) -> Self:
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


default_app_version, default_build_number = random.choice(APP_VERSIONS)


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

    @classmethod
    def from_session_info(
        cls: type[Self],
        session_info: SessionInfo,
        *args: Any,
        **kwargs: Any,
    ) -> Self:
        return super().from_session_info(
            session_info=session_info,
            device_id=session_info.device_id,
            mt_instance_id=session_info.mt_instance_id,
            *args,
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
    device_type: DeviceType
    phone: str | None = None
    user_agent_config: BaseEnvelopeMappingUserAgentConfigV11 = (
        WebEnvelopeMappingUserAgentConfigV11()
    )

    @property
    def is_custom_user_agent_config(self):
        return "user_agent_config" in self.model_fields_set


USER_AGENTS_V11_PER_DEVICE_TYPE = {
    DeviceType.Android: AndroidEnvelopeMappingUserAgentConfigV11,
    DeviceType.Web: WebEnvelopeMappingUserAgentConfigV11,
    DeviceType.Desktop: DesktopEnvelopeMappingUserAgentConfigV11,
}


class EnvelopeMapperConfigV11(BaseMapperConfig):
    token: str | None = None
    protocol_version: int = 11
    device_type: DeviceType = DeviceType.Web
    password: str | None = None
    phone: str | None = None
    sms_auth: bool = False
    interactive: bool = True
    keepalive_ping_interval: int = 30
    url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None
    connect_timeout: int | None = None
    user_agent_config: BaseEnvelopeMappingUserAgentConfigV11 = (
        WebEnvelopeMappingUserAgentConfigV11()
    )
    registration_config: RegistrationConfig | None = None
    use_mobile_fingerprint: bool = True
    use_telemetry: bool = True
    request_timeout: float = 30.0
    mapper_logger: Logger | None = None

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        original_fields_set = self.model_fields_set.copy()

        device_type = self.device_type
        if "sms_auth" not in original_fields_set:
            self.sms_auth = False if device_type == DeviceType.Web else True
        if "user_agent_config" not in original_fields_set:
            user_agent_config_per_device_type = USER_AGENTS_V11_PER_DEVICE_TYPE.get(
                device_type
            )
            user_agent_config = (
                user_agent_config_per_device_type
                or WebEnvelopeMappingUserAgentConfigV11
            )
            self.user_agent_config = user_agent_config()
        self.__pydantic_fields_set__ = original_fields_set
        return self


CONFIG_SETS: dict[
    DeviceType | str,
    tuple[
        tuple[TransportRegistry, EncodingRegistry, ProtocolRegistry, MapperRegistry],
        ...,
    ],
] = {
    DeviceType.Web: (
        (
            TransportRegistry.WebSocketTransport,
            EncodingRegistry.JsonEncoding,
            ProtocolRegistry.EnvelopeProtocol,
            MapperRegistry.EnvelopeV11Mapper,
        ),
    ),
    DeviceType.Desktop: (
        (
            TransportRegistry.SocketTransport,
            EncodingRegistry.MsgPackDictEncoding,
            ProtocolRegistry.EnvelopeProtocol,
            MapperRegistry.EnvelopeV11Mapper,
        ),
    ),
    DeviceType.Android: (
        (
            TransportRegistry.SocketTransport,
            EncodingRegistry.MsgPackDictEncoding,
            ProtocolRegistry.EnvelopeProtocol,
            MapperRegistry.EnvelopeV11Mapper,
        ),
    ),
}

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


def from_config_to_registry(conf: type[BaseConfig]) -> BaseRegistry | None:
    if issubclass(conf, Default):
        defaults_map: dict[type[Default], type[BaseConfig]] = {
            DefaultTransportConfig: default_transport_config,
            DefaultEncodingConfig: default_encoding_config,
            DefaultProtocolConfig: default_protocol_config,
            DefaultMapperConfig: default_mapper_config,
        }
        conf = defaults_map[conf]

    config_family = conf.__bases__[0]

    FROM_CONFIG_TO_REGISTRY: dict[type, dict[type[BaseConfig], BaseRegistry]] = {
        BaseTransportConfig: {
            SocketTransportConfig: TransportRegistry.SocketTransport,
            WebSocketTransportConfig: TransportRegistry.WebSocketTransport,
        },
        BaseEncodingConfig: {
            JsonEncodingConfig: EncodingRegistry.JsonEncoding,
            NoEncodingConfig: EncodingRegistry.NoEncoding,
            MsgPackDictEncodingConfig: EncodingRegistry.MsgPackDictEncoding,
        },
        BaseProtocolConfig: {
            EnvelopeProtocolConfig: ProtocolRegistry.EnvelopeProtocol,
        },
        BaseMapperConfig: {
            EnvelopeMapperConfigV11: MapperRegistry.EnvelopeV11Mapper,
        },
    }
    return FROM_CONFIG_TO_REGISTRY.get(config_family, {}).get(conf)


def from_registry_to_config(
    registry_family: type[BaseRegistry], reg: BaseRegistry | type[BaseConfig] | None
) -> type[BaseConfig] | None:
    if isinstance(reg, type) and issubclass(reg, BaseConfig):
        reg_resolved = from_config_to_registry(reg)
    else:
        reg_resolved = reg

    CONFIGS_PER_REGISTRY_ITEM: dict[
        type[BaseRegistry], dict[BaseRegistry | None, type[BaseConfig]]
    ] = {
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
    if registry_family not in CONFIGS_PER_REGISTRY_ITEM:
        logging.warning("registry family '%s' is not supported", registry_family)

    return CONFIGS_PER_REGISTRY_ITEM.get(registry_family, {}).get(reg_resolved)


class ExtraConfig(BaseConfig):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    transport: BaseTransportConfig = Field(default_factory=DefaultTransportConfig)
    encoding: BaseEncodingConfig = (
        DefaultEncodingConfig()
    )  # not used by now, for future
    protocol: BaseProtocolConfig = Field(default_factory=DefaultProtocolConfig)
    mapper: BaseMapperConfig = Field(default_factory=DefaultMapperConfig)

    session_storage: BaseSessionStorage | None = None
    work_dir: str = "."
    session_name: str = "session.db"
    session_id: str | None = None
    restore_user_agent_from_session: bool = True

    sync: SyncOverrides = Field(default_factory=SyncOverrides)

    _logger: ClassVar[Logger] = logging.getLogger("ExtraConfig")

    @model_validator(mode="before")
    @classmethod
    def validate_transport(self, data: Any) -> Any:
        if isinstance(data, dict):
            extra_config_device_type = data.get("device_type", DeviceType.Web)
        elif isinstance(data, BaseModel):
            extra_config_device_type = data.model_dump().get(
                "device_type", DeviceType.Web
            )
        else:
            extra_config_device_type = DeviceType.Web

        if isinstance(data, dict):
            if "mapper" in data and "transport" not in data:
                mapper = data["mapper"]
                if isinstance(mapper, dict):
                    device_type = mapper.get("device_type", extra_config_device_type)
                elif isinstance(mapper, BaseModel):
                    device_type = mapper.model_dump().get(
                        "device_type", extra_config_device_type
                    )
                else:
                    return data
                data["transport"] = (
                    WebSocketTransportConfig()
                    if device_type == DeviceType.Web
                    else SocketTransportConfig()
                )
            return data
        else:
            return data

    def config_rebuild(
        self,
        transport: TransportRegistry | None,
        encoding: EncodingRegistry | None,
        protocol: ProtocolRegistry | None,
        mapper: MapperRegistry | None,
    ) -> "ExtraConfig":

        device_type = self.mapper.device_type

        config_presets = CONFIG_SETS.get(device_type) or (
            (
                from_config_to_registry(default_transport_config),
                from_config_to_registry(default_encoding_config),
                from_config_to_registry(default_protocol_config),
                from_config_to_registry(default_mapper_config),
            ),
        )
        config_mask = config_presets[0]

        transport_config = (
            from_registry_to_config(TransportRegistry, transport)
            or (
                type(self.transport)
                if not issubclass(type(self.transport), Default)
                else None
            )
            or from_registry_to_config(TransportRegistry, config_mask[0])
            or default_transport_config
        )
        encoding_config = (
            from_registry_to_config(EncodingRegistry, encoding)
            or (
                type(self.encoding)
                if not issubclass(type(self.encoding), Default)
                else None
            )
            or from_registry_to_config(EncodingRegistry, config_mask[1])
            or default_encoding_config
        )
        protocol_config = (
            from_registry_to_config(ProtocolRegistry, protocol)
            or (
                type(self.protocol)
                if not issubclass(type(self.protocol), Default)
                else None
            )
            or from_registry_to_config(ProtocolRegistry, config_mask[2])
            or default_protocol_config
        )
        mapper_config = (
            from_registry_to_config(MapperRegistry, mapper)
            or (
                type(self.mapper)
                if not issubclass(type(self.mapper), Default)
                else None
            )
            or from_registry_to_config(MapperRegistry, config_mask[3])
            or default_mapper_config
        )

        user_preset = (
            from_config_to_registry(transport_config),
            from_config_to_registry(encoding_config),
            from_config_to_registry(protocol_config),
            from_config_to_registry(mapper_config),
        )
        if user_preset not in config_presets:
            self._logger.warning(
                "Your chosen settings not found in presets, a big chance for errors."
            )

        mapper_user_agent_config = self.mapper.user_agent_config

        mapper_dump = self.mapper.model_dump()
        for key in mapper_dump.copy():
            if key not in self.mapper.model_fields_set:
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
        return config_updated
