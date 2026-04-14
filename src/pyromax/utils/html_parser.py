from html.parser import HTMLParser
from typing import Any


class DeepestTagScanner(HTMLParser):
    def __init__(self, target_tags: list[str]):
        super().__init__()
        self.target_tags: set[str] = {t.lower() for t in target_tags}
        self.stack: list[dict[str, Any]] = []
        self.results: list[dict[str, Any]] = []
        self.raw_html: str = ""

    def feed(self, data: str) -> None:
        self.raw_html = data
        super().feed(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.target_tags:
            line, col = self.getpos()
            idx = self._get_raw_index(line, col)
            start_content = self.raw_html.find('>', idx) + 1

            self.stack.append({
                "tag": tag.upper(),
                "attrs": dict(attrs),
                "start": start_content,
                "has_child": False
            })
            if len(self.stack) > 1:
                self.stack[-2]["has_child"] = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.target_tags and self.stack:
            node = self.stack.pop()
            if not node["has_child"]:
                line, col = self.getpos()
                end_content = self._get_raw_index(line, col)
                content = self.raw_html[node["start"]:end_content]

                self.results.append({
                    "tag": node["tag"],
                    "attrs": node["attrs"],
                    "from": node["start"],
                    "length": len(content),
                    "content": content
                })

    def _get_raw_index(self, line: int, col: int) -> int:
        lines = self.raw_html.splitlines(keepends=True)
        return sum(len(s) for s in lines[:line - 1]) + col


if __name__ == '__main__':

    text = "Hello <strong>World</strong> and <strong>Python</strong>"
    scanner = DeepestTagScanner(['STRONG'])
    scanner.feed(text)

    print(f"Results: {scanner.results}")

    elements = []
    for res in scanner.results:
        elements.append({
            'type': res['tag'],
            'from': res['from'],
            'length': res['length'],
        })

    print(f"Elements: {elements}")
