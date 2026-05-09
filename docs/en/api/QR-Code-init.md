# QR code auth

Works with EnvelopeMapperV11 and any transport supported by this mapper

but it is necessary to maintain the correct mapping of the device types supported by the transport



```python
max_api = await MaxApi(
    transport='websocket',
    device_type='WEB',
)
```

its mean for websocket transport need give in device_type 'WEB',
for 'socket_envelope' need give 'DESKTOP'

```python
max_api = await MaxApi(
    transport='socket_envelope',
    device_type='DESKTOP',
)
```

You can give a callback for qr url in class constructor.
Url callback have this signature:
```python
Callable[str, Courutine[Any, Any, None]]
```

```python
async def qr_callback(qr_url: str):
    # for resolve you need to scan qr code in Max app
    pass

max_api = await MaxApi(
    transport='websocket',
    device_type='WEB',
    url_callback=qr_callback
)
```

if url_callback is None qr will be printed in console