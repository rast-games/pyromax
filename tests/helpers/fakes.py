from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


@dataclass
class MapperCall:
    method: type[Any]
    kwargs: dict[str, Any]


class FakeMapper:
    def __init__(self, result: Any = None) -> None:
        self.result = result
        self.calls: list[MapperCall] = []
        self.direct_calls: list[tuple[str, dict[str, Any]]] = []

    async def call_method(self, method: type[Any], **kwargs: Any) -> Any:
        self.calls.append(MapperCall(method, kwargs))
        return self.result

    async def send_message(self, **kwargs: Any) -> Any:
        self.direct_calls.append(("send_message", kwargs))
        return self.result

    async def upload_file(self, *args: Any, **kwargs: Any) -> Any:
        self.direct_calls.append(("upload_file", {"args": args, **kwargs}))
        return self.result

    async def download_file(self, **kwargs: Any) -> Any:
        self.direct_calls.append(("download_file", kwargs))
        return self.result

    async def get_members_by_ids(self, **kwargs: Any) -> Any:
        self.direct_calls.append(("get_members_by_ids", kwargs))
        return self.result


class FakeApi(SimpleNamespace):
    def __init__(self, result: Any = None) -> None:
        super().__init__(mapper=FakeMapper(result))
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(("__call__", kwargs))
        return self.mapper.result

    def __getattr__(self, name: str):
        async def call(**kwargs: Any) -> Any:
            self.calls.append((name, kwargs))
            return self.mapper.result

        return call
