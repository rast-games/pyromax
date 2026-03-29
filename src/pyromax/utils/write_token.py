import asyncio
import json
from pathlib import Path
import aiofiles

ROOT_DIR = Path().resolve()
JSON_FILE = ROOT_DIR / "tokens.json"

async def write_token(token: str, name_of_token: str = 'max_token'):
    """Write or overwriting token from json file."""

    data = {name_of_token: token}
    async with aiofiles.open(JSON_FILE, mode="w") as f:
        all_json = json.loads(f.read())
        all_json[name_of_token] = token
        await f.write(json.dumps(all_json, indent=4))

async def read_token(name_of_token: str = 'max_token') -> str | None:
    """Read token from json file."""
    if not JSON_FILE.exists():
        return None
    async with aiofiles.open(JSON_FILE, mode="r") as f:
        content = await f.read()
        if not content.strip():
            return None
        try:
            data = json.loads(content)
            return data.get(name_of_token)
        except json.JSONDecodeError:
            return None

async def main():
    await write_token("test")

    token = await read_token()
    print(token)

if __name__ == "__main__":
    asyncio.run(main())