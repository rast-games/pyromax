from copy import deepcopy

import pyromax.config as config_module
import pyromax.transport.registry as transport_registry_module
import pytest
from pyromax.config import (
    CONFIG_SETS,
    BaseEncodingConfig,
    BaseEnvelopeMappingUserAgentConfigV11,
    BaseProtocolConfig,
    BaseTransportConfig,
    EnvelopeMapperConfigV11,
    ExtraConfig,
    SocketTransportConfig,
    from_registry_to_config,
    register_config_set,
    register_config_to_registry,
)
from pyromax.core import MaxApi
from pyromax.models import (
    BaseDeviceType,
    DeviceType,
    MapperRegistry,
    TransportRegistry,
)
from pyromax.models.enum.Registrys import BaseRegistry
from pyromax.session import BaseSessionStorage
from pyromax.transport.registry import register_transport


class CustomTransportRegistry(BaseRegistry):
    Primary = "CustomTransportPrimary"
    Alias = "CustomTransportAlias"


class CustomEncodingRegistry(BaseRegistry):
    Encoding = "CustomEncoding"


class CustomProtocolRegistry(BaseRegistry):
    Protocol = "CustomProtocol"


class CustomMapperRegistry(BaseRegistry):
    Mapper = "CustomMapper"


class CustomDeviceType(BaseDeviceType):
    Console = "CONSOLE"


class CustomTransportConfig(BaseTransportConfig):
    pass


class CustomEncodingConfig(BaseEncodingConfig):
    pass


class CustomProtocolConfig(BaseProtocolConfig):
    pass


class CustomMapperConfig(EnvelopeMapperConfigV11):
    pass


class ConsoleUserAgentConfig(BaseEnvelopeMappingUserAgentConfigV11):
    device_type: str = CustomDeviceType.Console


class MemorySessionStorage(BaseSessionStorage):
    def __init__(self) -> None:
        self.closed = False
        self.load_calls = 0

    async def load_session(self, _session_key):
        self.load_calls += 1
        return None

    async def update_session(self, _session_key, _session_info) -> None:
        pass

    async def close(self) -> None:
        self.closed = True


class RuntimeEncoding:
    def __init__(self, extra_config: ExtraConfig) -> None:
        self.extra_config = extra_config


class RuntimeTransport:
    pass


class RuntimeProtocol:
    pass


class RuntimeMapper:
    def __init__(self) -> None:
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


async def make_runtime_transport(_encoding, _extra_config) -> RuntimeTransport:
    return RuntimeTransport()


async def make_runtime_protocol(**_kwargs) -> RuntimeProtocol:
    return RuntimeProtocol()


async def make_runtime_mapper(*_args, **_kwargs) -> RuntimeMapper:
    return RuntimeMapper()


PRIMARY_PRESET = (
    CustomTransportRegistry.Primary,
    CustomEncodingRegistry.Encoding,
    CustomProtocolRegistry.Protocol,
    CustomMapperRegistry.Mapper,
)
ALIAS_PRESET = (
    CustomTransportRegistry.Alias,
    CustomEncodingRegistry.Encoding,
    CustomProtocolRegistry.Protocol,
    CustomMapperRegistry.Mapper,
)


def _custom_config() -> ExtraConfig:
    config = ExtraConfig(
        transport=CustomTransportConfig(),
        encoding=CustomEncodingConfig(),
        protocol=CustomProtocolConfig(),
        mapper=CustomMapperConfig(device_type=DeviceType.Web),
    )
    config.register_config_to_registry(
        CustomTransportConfig, CustomTransportRegistry.Primary
    )
    config.register_config_to_registry(
        CustomTransportConfig, CustomTransportRegistry.Alias
    )
    config.register_config_to_registry(
        CustomEncodingConfig, CustomEncodingRegistry.Encoding
    )
    config.register_config_to_registry(
        CustomProtocolConfig, CustomProtocolRegistry.Protocol
    )
    config.register_config_to_registry(CustomMapperConfig, CustomMapperRegistry.Mapper)
    config.register_config_set(DeviceType.Web, PRIMARY_PRESET)
    config.register_config_set(DeviceType.Web, ALIAS_PRESET)
    return config


def test_from_registry_to_config_uses_the_supplied_registry() -> None:
    registry = {
        CustomTransportRegistry: {
            CustomTransportRegistry.Primary: CustomTransportConfig,
        }
    }

    assert (
        from_registry_to_config(
            CustomTransportRegistry,
            CustomTransportRegistry.Primary,
            configs_per_registry=registry,
        )
        is CustomTransportConfig
    )
    assert (
        from_registry_to_config(
            CustomTransportRegistry,
            CustomTransportConfig,
            configs_per_registry=registry,
        )
        is CustomTransportConfig
    )


def test_custom_registrations_are_merged_at_the_nested_level() -> None:
    config = ExtraConfig()
    config.register_config_to_registry(
        CustomTransportConfig, TransportRegistry.WebSocketTransport
    )
    config.register_config_set(DeviceType.Web, PRIMARY_PRESET)

    assert (
        config._configs_per_registry[TransportRegistry][
            TransportRegistry.WebSocketTransport
        ]
        is CustomTransportConfig
    )
    assert (
        config._configs_per_registry[TransportRegistry][
            TransportRegistry.SocketTransport
        ]
        is SocketTransportConfig
    )
    assert config._config_sets[DeviceType.Web] == [
        *CONFIG_SETS[DeviceType.Web],
        PRIMARY_PRESET,
    ]
    untouched = ExtraConfig()
    assert CustomTransportRegistry not in untouched._configs_per_registry
    assert PRIMARY_PRESET not in untouched._config_sets[DeviceType.Web]


def test_each_config_gets_independent_default_config_sources() -> None:
    first = ExtraConfig()
    second = ExtraConfig()

    assert first.config_sets_source is not second.config_sets_source
    assert first.config_registry_source is not second.config_registry_source


def test_custom_device_type_supports_local_config_presets() -> None:
    custom_device_preset = CONFIG_SETS[DeviceType.Web][0]
    config = ExtraConfig(mapper={"device_type": CustomDeviceType.Console})
    config.register_config_set(CustomDeviceType.Console, custom_device_preset)

    rebuilt = config.config_rebuild(None, None, None, None)

    assert rebuilt.mapper.device_type is CustomDeviceType.Console
    assert rebuilt.current_preset == custom_device_preset
    assert rebuilt._config_sets[CustomDeviceType.Console] == [custom_device_preset]


def test_user_agent_registry_is_local_and_survives_config_rebuild() -> None:
    mapper = EnvelopeMapperConfigV11(device_type=CustomDeviceType.Console)
    untouched_mapper = EnvelopeMapperConfigV11()
    mapper.register_user_agent_config(
        CustomDeviceType.Console,
        ConsoleUserAgentConfig,
    )
    config = ExtraConfig(mapper=mapper)
    custom_device_preset = CONFIG_SETS[DeviceType.Web][0]
    config.register_config_set(CustomDeviceType.Console, custom_device_preset)

    rebuilt = config.config_rebuild(None, None, None, None)
    rebuilt_again = rebuilt.config_rebuild(None, None, None, None)

    assert isinstance(mapper.user_agent_config, ConsoleUserAgentConfig)
    assert CustomDeviceType.Console not in untouched_mapper.user_agents_per_device_type
    assert (
        rebuilt.mapper.user_agents_per_device_type[CustomDeviceType.Console]
        is ConsoleUserAgentConfig
    )
    assert isinstance(rebuilt.mapper.user_agent_config, ConsoleUserAgentConfig)
    assert isinstance(rebuilt_again.mapper.user_agent_config, ConsoleUserAgentConfig)


def test_explicit_sources_replace_defaults_before_local_registration() -> None:
    replacement_sets = {DeviceType.Web: [PRIMARY_PRESET]}
    replacement_registry = {
        CustomTransportRegistry: {
            CustomTransportRegistry.Primary: CustomTransportConfig,
        },
        CustomEncodingRegistry: {
            CustomEncodingRegistry.Encoding: CustomEncodingConfig,
        },
        CustomProtocolRegistry: {
            CustomProtocolRegistry.Protocol: CustomProtocolConfig,
        },
        CustomMapperRegistry: {
            CustomMapperRegistry.Mapper: CustomMapperConfig,
        },
    }
    config = ExtraConfig(
        config_sets_source=replacement_sets,
        config_registry_source=replacement_registry,
    )

    assert config._config_sets == replacement_sets
    assert config._configs_per_registry == replacement_registry
    assert TransportRegistry not in config._configs_per_registry

    config.register_config_to_registry(
        CustomTransportConfig, CustomTransportRegistry.Alias
    )
    config.register_config_set(DeviceType.Web, ALIAS_PRESET)

    assert config._config_sets[DeviceType.Web] == [PRIMARY_PRESET, ALIAS_PRESET]
    assert (
        config._configs_per_registry[CustomTransportRegistry][
            CustomTransportRegistry.Alias
        ]
        is CustomTransportConfig
    )
    assert TransportRegistry not in config._configs_per_registry


def test_global_registrations_are_snapshotted_by_new_configs(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "CONFIG_SETS", deepcopy(CONFIG_SETS))
    monkeypatch.setattr(
        config_module,
        "CONFIGS_PER_REGISTRY_ITEM",
        deepcopy(config_module.CONFIGS_PER_REGISTRY_ITEM),
    )
    before_registration = ExtraConfig()

    register_config_to_registry(
        CustomTransportConfig, CustomTransportRegistry.Primary
    )
    register_config_to_registry(
        CustomEncodingConfig, CustomEncodingRegistry.Encoding
    )
    register_config_to_registry(
        CustomProtocolConfig, CustomProtocolRegistry.Protocol
    )
    register_config_to_registry(CustomMapperConfig, CustomMapperRegistry.Mapper)
    register_config_set(DeviceType.Web, PRIMARY_PRESET)

    after_registration = ExtraConfig()

    assert CustomTransportRegistry not in before_registration.config_registry_source
    assert PRIMARY_PRESET not in before_registration.config_sets_source[DeviceType.Web]
    assert (
        after_registration.config_registry_source[CustomTransportRegistry][
            CustomTransportRegistry.Primary
        ]
        is CustomTransportConfig
    )
    assert PRIMARY_PRESET in after_registration.config_sets_source[DeviceType.Web]
    for standard_preset in CONFIG_SETS[DeviceType.Web]:
        assert standard_preset in after_registration.config_sets_source[DeviceType.Web]


def test_compute_combinations_resolves_config_classes_and_preset_values() -> None:
    config = _custom_config()
    config.allow_registry_config_matching = True

    assert config._compute_all_combinations([PRIMARY_PRESET]) == {
        PRIMARY_PRESET,
        ALIAS_PRESET,
    }


def test_local_config_set_supplies_unspecified_override_values(caplog) -> None:
    local_preset = (
        CustomTransportRegistry.Primary,
        CustomEncodingRegistry.Encoding,
        CustomProtocolRegistry.Protocol,
        MapperRegistry.EnvelopeV11Mapper,
    )
    config = ExtraConfig()
    config.register_config_to_registry(
        CustomTransportConfig, CustomTransportRegistry.Primary
    )
    config.register_config_to_registry(
        CustomEncodingConfig, CustomEncodingRegistry.Encoding
    )
    config.register_config_to_registry(
        CustomProtocolConfig, CustomProtocolRegistry.Protocol
    )
    config.register_config_set(DeviceType.Web, local_preset)

    with caplog.at_level("WARNING", logger="ExtraConfig"):
        rebuilt = config.config_rebuild(
            CustomTransportRegistry.Primary,
            None,
            None,
            None,
        )

    assert rebuilt.current_preset == local_preset
    assert isinstance(rebuilt.transport, CustomTransportConfig)
    assert isinstance(rebuilt.encoding, CustomEncodingConfig)
    assert isinstance(rebuilt.protocol, CustomProtocolConfig)
    assert "Your chosen settings not found in presets" not in caplog.text


def test_equivalent_registry_override_warns_with_strict_matching(caplog) -> None:
    config = ExtraConfig(mapper={"device_type": DeviceType.Android})
    config.register_config_to_registry(
        SocketTransportConfig, CustomTransportRegistry.Primary
    )
    default_preset = CONFIG_SETS[DeviceType.Android][0]

    with caplog.at_level("WARNING", logger="ExtraConfig"):
        rebuilt = config.config_rebuild(
            CustomTransportRegistry.Primary,
            default_preset[1],
            default_preset[2],
            default_preset[3],
        )

    assert rebuilt.current_preset == (
        CustomTransportRegistry.Primary,
        *default_preset[1:],
    )
    assert "Your chosen settings not found in presets" in caplog.text


def test_config_matching_directive_accepts_equivalent_registry_override(
    caplog,
) -> None:
    config = ExtraConfig(
        mapper={"device_type": DeviceType.Android},
        allow_registry_config_matching=True,
    )
    config.register_config_to_registry(
        SocketTransportConfig, CustomTransportRegistry.Primary
    )
    default_preset = CONFIG_SETS[DeviceType.Android][0]

    with caplog.at_level("WARNING", logger="ExtraConfig"):
        rebuilt = config.config_rebuild(
            CustomTransportRegistry.Primary,
            default_preset[1],
            default_preset[2],
            default_preset[3],
        )

    assert rebuilt.current_preset == (
        CustomTransportRegistry.Primary,
        *default_preset[1:],
    )
    assert "Your chosen settings not found in presets" not in caplog.text


def test_config_rebuild_preserves_custom_registrations() -> None:
    config = _custom_config()

    rebuilt = config.config_rebuild(None, None, None, None)
    rebuilt_again = rebuilt.config_rebuild(None, None, None, None)

    assert isinstance(rebuilt.transport, CustomTransportConfig)
    assert isinstance(rebuilt.encoding, CustomEncodingConfig)
    assert isinstance(rebuilt.protocol, CustomProtocolConfig)
    assert isinstance(rebuilt.mapper, CustomMapperConfig)
    assert rebuilt.current_preset == PRIMARY_PRESET
    assert isinstance(rebuilt_again.transport, CustomTransportConfig)
    assert PRIMARY_PRESET in rebuilt_again._config_sets[DeviceType.Web]
    assert (
        rebuilt_again._configs_per_registry[CustomTransportRegistry][
            CustomTransportRegistry.Primary
        ]
        is CustomTransportConfig
    )


async def test_max_api_sees_global_runtime_registration_made_after_config(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        transport_registry_module,
        "TRANSPORTS",
        deepcopy(transport_registry_module.TRANSPORTS),
    )
    config = _custom_config()
    storage = MemorySessionStorage()
    register_transport(CustomTransportRegistry.Primary.value)(make_runtime_transport)
    config.encoding_registry = {
        CustomEncodingRegistry.Encoding.value: RuntimeEncoding,
    }
    config.protocol_registry = {
        CustomProtocolRegistry.Protocol.value: make_runtime_protocol,
    }
    config.mapper_registry = {
        CustomMapperRegistry.Mapper.value: make_runtime_mapper,
    }
    config.session_storage = storage
    config.auto_connect_after_init = False

    api = await MaxApi(extra_config=config)
    try:
        assert isinstance(api.transport, RuntimeTransport)
        assert isinstance(api.protocol, RuntimeProtocol)
        assert isinstance(api.mapper, RuntimeMapper)
    finally:
        await api.stop()

    assert storage.closed


async def test_max_api_accepts_custom_device_type_with_custom_preset() -> None:
    config = _custom_config()
    config.mapper.device_type = CustomDeviceType.Console
    config.register_config_set(CustomDeviceType.Console, PRIMARY_PRESET)
    config.transport_registry = {
        CustomTransportRegistry.Primary.value: make_runtime_transport,
    }
    config.encoding_registry = {
        CustomEncodingRegistry.Encoding.value: RuntimeEncoding,
    }
    config.protocol_registry = {
        CustomProtocolRegistry.Protocol.value: make_runtime_protocol,
    }
    config.mapper_registry = {
        CustomMapperRegistry.Mapper.value: make_runtime_mapper,
    }
    config.session_storage = MemorySessionStorage()
    config.auto_connect_after_init = False

    api = await MaxApi(extra_config=config)
    try:
        assert api.device_type is CustomDeviceType.Console
        assert api.extra_config.mapper.device_type is CustomDeviceType.Console
        assert api.extra_config.current_preset == PRIMARY_PRESET
    finally:
        await api.stop()


async def test_runtime_registry_validation_precedes_session_storage() -> None:
    config = _custom_config()
    storage = MemorySessionStorage()
    config.transport_registry = {}
    config.session_storage = storage
    config.auto_connect_after_init = False

    with pytest.raises(RuntimeError, match="transport .* is not supported"):
        await MaxApi(extra_config=config)

    assert storage.load_calls == 0
