# Token auth

This scenario assumes you have a token for an already authorized account.
Therefore, you can pass it to the class constructor, but you still need to remember to correctly match the transport and token. A token obtained for a websocket transport will not work with a socket transport.

for websocket:
```python
websocket_token = ...
max_api = await MaxApi(
    token=websocket_token,
    transport='websocket',
    device_type='WEB'
)
```

for socket:
```python
socket_token = ...
max_api = await MaxApi(
    token=socket_token,
    transport='socket',
    device_type='DESKTOP',
)
```

[//]: # (# probable exceptions)

[//]: # ()
[//]: # (token can expires when bot running)