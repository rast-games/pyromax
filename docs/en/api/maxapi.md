# API Reference

# MaxApi

::: pyromax.core.client.MaxApi

`MaxApi` is the main asynchronous client used to work with MAX Messenger.

## Supported backends

| Kind | Available options                        |
|---|------------------------------------------|
| Transport | `websocket`, `socket_envelope`, `socket` |
| Protocol | `EnvelopeProtocol`                       |
| Mapper | `EnvelopeV11`                            |

Necessary to maintain the correct mapping of the [device types supported by the transport](../support-device-type-transport)

## Initialization scenarios
- [Initialization with phone number(Only for socket_envelope transport).](../phone-number-init)
- [QR code initialization.](../QR-Code-init)
- [Initialization with token.](../phone-number-init)

