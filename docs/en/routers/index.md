# Routers

Routers help you split bot logic into separate modules and keep the project organized as it grows.

::: pyromax.dispatcher.Router.Router
    options:
        show_root_heading: false
        show_root_full_path: false

## Example

```python
from pyromax.api.observer import Router

router1 = Router()

@router.message(from_me=True)
async def ping_handler(message):
    await message.reply("Pong!")
```
