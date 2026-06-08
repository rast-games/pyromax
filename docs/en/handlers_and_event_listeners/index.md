## Event listeners
All routers have a set of event listeners.
You can see them in the [`Router`](../routers/index.md) class in the `self.events` attribute

Each event listener is managed by its own handlers. Every time an update arrives, the event listener begins iterating through its handlers. As soon as an update matches the conditions of any handler, the iteration is interrupted, and the handler performs its functions.

## Handlers

Each handler is essentially a wrapper over a function; their registration occurs using the decorator `__call__` defined in `StandardMaxEventObserver` and all its subclasses:
::: pyromax.dispatcher.event.StandardMaxEventObserver.StandardMaxEventObserver.__call__

Each subclass can override __call__ and, accordingly, other registration methods. For example, in MessageEventObserver, you can also specify the from_me parameter, which affects whether messages from the account running UserBot will be processed in this handler in the same way as messages from other accounts:

::: pyromax.dispatcher.event.MessageEventObservers.MessageEventObserver.__call__

```python
@dp.message()
async def message_others(msg: Message):
    await msg.answer(
        text='answer for messages from other users'
    )
    
@dp.message(from_me=True)
async def my_message_and_others(msg: Message):
    await msg.answer(
        text='answer for ALL messages'
    )
```

As you've noticed, the msg parameter in the string is annotated with the Message model, so the incoming message object of the Message type will be passed to it. You can also request objects of other types, and if they exist in the workflow data, they will be passed to the corresponding parameters.
If you do not specify annotations for any of the handler parameters, an `AnnotationError` exception will be thrown.

```python
@dp.message(from_me=True)
async def my_message_and_others(max_api: MaxApi, msg: Message):
    if msg.text:
        await max_api.send_message(
            chat_id=msg.chat_id,
            text = msg.text
        )
```

the order doesn't matter

```python
@dp.message(from_me=True)
async def my_message_and_others(msg: Message, max_api: MaxApi):
    if msg.text:
        await max_api.send_message(
            chat_id=msg.chat_id,
            text = msg.text
        )
```

also supported forward ref

```python
@dp.message(from_me=True)
async def my_message_and_others(msg: 'Message', max_api: 'MaxApi'):
    if msg.text:
        await max_api.send_message(
            chat_id=msg.chat_id,
            text = msg.text
        )
```

## Passing your classes to the handler

You can pass your parameters to all handlers using the workflow data attribute when initializing MaxApi.

```python
class DB:
    """Something with DataBase"""
    pass

max_api = await MaxApi(
    transport='websocket',
    device_type='WEB',
    token=websocket_token,
    workflow_data={
        DB: DB(),
        'forward_ref': 'something'
    }
)

@dp.message(from_me=True)
async def test_workflow_data(max_api: MaxApi, msg: 'Message', ref: 'forward_ref', data_base: DB):
    pass
```


If such objects do not exist in the workflow, then the data will be transferred in their place No

```python
@dp.message(from_me=True)
async def my_message_and_others(max_api: MaxApi, msg: Message, not_exist: NotExits):
    if msg.text:
        await max_api.send_message(
            chat_id=msg.chat_id,
            text = msg.text
        )
    print(not_exist)
    # >>> None
```
