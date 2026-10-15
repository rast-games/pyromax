# Infrastructure API

## Configuration

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

## Sessions

::: pyromax.session

## Authentication interaction

::: pyromax.interaction

## Encodings

::: pyromax.encoding

## Transports

::: pyromax.transport
    options:
      members:
        - BaseTransport
        - StreamTransport
        - WebSocketTransport
        - SocketTransport

## Protocols

::: pyromax.protocol
    options:
      members:
        - BaseMaxProtocol
        - StreamMaxProtocol
        - EnvelopeProtocol
        - Request
        - Response

## Mappers

::: pyromax.mapping
    options:
      members:
        - BaseMapper
        - EnvelopeMapperV11

## High-level methods

::: pyromax.methods.BaseMaxApiMethod

## Registry decorators

::: pyromax.transport.registry.register_transport

::: pyromax.encoding.registry.register_encoding

::: pyromax.protocol.registry.register_protocol

::: pyromax.mapping.registry.register_mapper
