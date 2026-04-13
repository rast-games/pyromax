import asyncio
import json
from pathlib import Path
from typing import cast

import aiofiles

ROOT_DIR = Path().resolve()
JSON_FILE = ROOT_DIR / "tokens.json"


async def write_token(token: str, name_of_token: str = 'max_token') -> None:
    """Write or overwriting token from json file."""
    # Читаем существующие данные
    existing_data = {}
    if JSON_FILE.exists():
        try:
            async with aiofiles.open(JSON_FILE, mode="r") as f:
                content = await f.read()
                if content.strip():
                    existing_data = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = {}

    # Обновляем данные
    existing_data[name_of_token] = token

    # Записываем обратно
    async with aiofiles.open(JSON_FILE, mode="w", encoding="utf-8") as f:
        await f.write(json.dumps(existing_data, indent=4, ensure_ascii=False))

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
            return cast(str | None, data.get(name_of_token))
        except json.JSONDecodeError:
            return None

async def main() -> None:
    await write_token("test")

    token = await read_token()
    print(token)

if __name__ == "__main__":
    asyncio.run(main())