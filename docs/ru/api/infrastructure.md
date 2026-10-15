# API инфраструктуры

## Конфигурация

::: pyromax.config
    options:
      members:
        - ExtraConfig
        - SocketTransportConfig
        - WebSocketTransportConfig
        - JsonEncodingConfig
        - MsgPackDictEncodingConfig
        - EnvelopeProtocolConfig
        - EnvelopeMapperConfigV11
        - WebEnvelopeMappingUserAgentConfigV11
        - DesktopEnvelopeMappingUserAgentConfigV11
        - AndroidEnvelopeMappingUserAgentConfigV11

## Сессии

::: pyromax.session

## Взаимодействие при авторизации

::: pyromax.interaction

## Кодирования

::: pyromax.encoding

## Транспорты

::: pyromax.transport
    options:
      members:
        - BaseTransport
        - StreamTransport
        - WebSocketTransport
        - SocketTransport

## Протоколы

::: pyromax.protocol
    options:
      members:
        - BaseMaxProtocol
        - StreamMaxProtocol
        - EnvelopeProtocol
        - Request
        - Response

## Мапперы

::: pyromax.mapping
    options:
      members:
        - BaseMapper
        - EnvelopeMapperV11

## High-level методы

::: pyromax.methods.BaseMaxApiMethod

## Декораторы реестров

::: pyromax.transport.registry.register_transport

::: pyromax.encoding.registry.register_encoding

::: pyromax.protocol.registry.register_protocol

::: pyromax.mapping.registry.register_mapper
