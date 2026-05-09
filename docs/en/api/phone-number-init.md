# Phone number initialization

Working only when transport is socket_envelope, device_type is 'DESKTOP' and sms_auth is True value

```python
max_api = await MaxApi(
    transport='socket_envelope',
    device_type='DESKTOP',
    sms_auth=True
)
```

You can give a callback getter for sms with signature:
```python
Callable[None, Courutine[Any, Any, int]]
```
```python
async def get_sms_code() -> int:
    # getting code from another source
    code = 1234
    return code
max_api = await MaxApi(
    transport='socket_envelope',
    device_type='DESKTOP',
    sms_auth=True,
    code_getter=get_sms_code
)
```
it will be called when need sms code

else if you dont give callback you will need type sms in console
```console
>>> Write a sms code: 
```

# probable exceptions
this auth method have limits

if you will spam server to give you code, server will ban you in undefined time

and in MaxApi will be used fallback auth method - QR code

so it's better to pass on QR callback even in this auth method

```python
async def get_sms_code() -> int:
    # getting code from another source
    code = 1234
    return code

async def url_callback(qr_url: str) -> None:
    # need turn qr code into a image and scan it in Max app
    pass
max_api = await MaxApi(
    transport='socket_envelope',
    device_type='DESKTOP',
    sms_auth=True,
    code_getter=get_sms_code,
    url_callback=url_callback
)
```
