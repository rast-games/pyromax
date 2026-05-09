## Your filters
To create your own filter, inherit from `Filter` and override `_check`.

`_check` signature:
```python
T = TypeVar('T')
Callable[..., bool | dict[type[T], T]]
```

In the `__call__` function, all parameters must be annotated, and depending on the annotation, the arguments of the corresponding class will be passed.

```python
from pyromax.filters import Filter
from pyromax.models import Message
from pyromax import MaxApi

MY_CHAT_ID = 24843722

class FromMyChat(Filter):
    async def _check(
            self,
            msg: Message,
            max_api: MaxApi
    ) -> bool | dict[type[T], T]:
        return msg.chat_id == MY_CHAT_ID
```

It is also necessary to override the getter work_with so that the filter is applied only to incoming objects of the specified class, in our case we are working with Message and specifying it
Getter signature:

```python
Callable[..., tuple[type[BaseMaxObject]]]
```

```python
from pyromax.filters import Filter
from pyromax.models import Message
from pyromax import MaxApi

MY_CHAT_ID = 24843722

class FromMyChat(Filter):
    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)
    
    async def _check(
            self,
            msg: Message,
            max_api: MaxApi
    ) -> bool | dict[type[T], T]:
        return msg.chat_id == MY_CHAT_ID
```
```python
@dp.message(FromMyChat())
async def handle_message_from_my_chat(msg: Message):
    #something with message
    pass
```

You can also override the initializer by calling the parent class's initializer first.

```python
from pyromax.filters import Filter
from pyromax.models import Message
from pyromax import MaxApi


class FromMyChat(Filter):
    
    def __init__(self, chat_id: int):
        super().__init__()
        self.chat_id = chat_id
    
    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)
    
    async def _check(
            self,
            msg: Message,
            max_api: MaxApi
    ) -> bool | dict[type[T], T]:
        return msg.chat_id == self.chat_id
```

```python
@dp.message(FromMyChat(24843722))
async def handle_message_from_my_chat(msg: Message):
    #something with message
    pass
```

Of course, this doesn't matter because there is already a similar built-in method - FromChatFilter, but this is just an example

# Return filtered object
There's also a more complex use case where a dictionary containing the filter results is returned instead of a Boolean value. The dictionary keys are the result type.

```python
from pyromax.filters import Filter
from pyromax.models import Message
from pyromax import MaxApi


class HaveWordObj:
    def __init__(self, word_start: int):
        self.word_start = word_start

class HaveWord(Filter):
    
    def __init__(self, word: str):
        super().__init__()
        self.word = word
    
    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)
    
    async def _check(
            self,
            msg: Message,
            max_api: MaxApi
    ) -> bool | dict[type[T], T]:
        if msg.text and self.word in msg.text:
            word_inx = msg.text.index(self.word)
            result = HaveWordObj(word_start=word_inx)
            # return {
            #     type(result): result
            # }
            # or
            return {
                HaveWordObj: result
            }
        else:
            return False
```

Next, in the handler, you can request the returned object from the filter.

```python
@dp.message(HaveWord('Pyromax'))
async def pyromax_word_handler(have_word_obj: HaveWordObj, msg: Message):
    await msg.answer(
        text=f'"Pyromax" started from {have_word_obj.word_start}'
    )
```

in chat:

    >>> my favorite lib is Pyromax
    >>> "Pyromax" started from 19
