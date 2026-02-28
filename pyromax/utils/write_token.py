import asyncio
import json
from pathlib import Path
import aiofiles

ROOT_DIR = Path().resolve()
JSON_FILE = ROOT_DIR / "tokens.json"

async def write_token(token: str):
    """Write or overwriting token from json file."""

    data = {"max_token": token}
    async with aiofiles.open(JSON_FILE, mode="w") as f:
        await f.write(json.dumps(data, indent=4))

async def read_token() -> str | None:
    """Read token from json file."""
    if not JSON_FILE.exists():
        return None
    async with aiofiles.open(JSON_FILE, mode="r") as f:
        content = await f.read()
        if not content.strip():
            return None
        try:
            data = json.loads(content)
            return data.get("max_token")
        except json.JSONDecodeError:
            return None

async def main():
    await write_token("test")

    token = await read_token()
    print(token)

if __name__ == "__main__":
    asyncio.run(main())