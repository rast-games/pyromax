# Formatting

## Supported tags

You can use formatting in your responses using tags:

```python
@dp.message(Command('lyric'), from_me=True)
async def lyric(msg):
    await msg.answer(
        text='<STRONG>They tell me, "keep it simple"</STRONG>'
             '<QUOTE>I tell them, "take it slow"</QUOTE>'
             '<STRIKETHROUGH>I feed a water an idea so I let it grow</STRIKETHROUGH>\n'
             '<UNDERLINE>I tell them, "take it easy"</UNDERLINE>\n'
             '<EMPHASIZED>They laugh and tell me, "No"</EMPHASIZED>\n'
             '<LINK url="https://www.youtube.com/watch?v=9Zj0JOHJR-s">its cool...</LINK>'
    )
```

## Note
This section can then be expanded with a full list of all supported tags and escaping rules.