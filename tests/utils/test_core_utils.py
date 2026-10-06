import asyncio
import unittest
from unittest.mock import patch

from pyromax.exceptions import AnnotationError, BackoffError
from pyromax.utils.backoff import Backoff, BackoffConfig
from pyromax.utils.clean_and_map import clean_and_map
from pyromax.utils.correlator import Correlator
from pyromax.utils.html_parser import DeepestTagScanner
from pyromax.utils.inspect_func_and_form_args import inspect_and_form
from pyromax.utils.return_self import return_self_after_method


class UtilityTest(unittest.IsolatedAsyncioTestCase):
    def test_html_scanner_is_case_insensitive_and_handles_lines(self) -> None:
        scanner = DeepestTagScanner(["strong"])
        scanner.feed('a\n<STRONG data-id="7">hello</STRONG>')
        self.assertEqual(scanner.results[0]["content"], "hello")
        self.assertEqual(scanner.results[0]["attrs"], {"data-id": "7"})

    def test_scanner_returns_only_deepest_target(self) -> None:
        scanner = DeepestTagScanner(["b"])
        scanner.feed("<b>outer <b>inner</b></b>")
        self.assertEqual([item["content"] for item in scanner.results], ["inner"])

    def test_clean_and_map_removes_markup_and_maps_offsets(self) -> None:
        text, elements = clean_and_map(
            'Hi <strong role="note">bold</strong> and <em>x</em>.', ["strong", "em"]
        )
        self.assertEqual(text, "Hi bold and x.")
        self.assertEqual(elements, [
            {"type": "STRONG", "from": 3, "length": 4, "attributes": {"role": "note"}},
            {"type": "EM", "from": 12, "length": 1, "attributes": {}},
        ])

    async def test_correlator_is_unique_under_concurrency(self) -> None:
        correlator = Correlator()
        values = await asyncio.gather(*(correlator.next_counter() for _ in range(100)))
        self.assertEqual(values, list(range(100)))

    def test_inspect_and_form_matches_annotations(self) -> None:
        class Dependency:
            pass

        dependency = Dependency()

        def handler(item: Dependency) -> None:
            pass

        self.assertEqual(inspect_and_form(handler, {Dependency: dependency}), {"item": dependency})

    def test_inspect_and_form_strict_and_non_strict(self) -> None:
        def handler(missing) -> None:
            pass

        with self.assertRaises(AnnotationError):
            inspect_and_form(handler, {})
        self.assertEqual(inspect_and_form(handler, {}, strict=False), {"missing": None})

    async def test_return_self_decorator(self) -> None:
        owner = object()

        async def empty(self: object) -> None:
            return None

        async def replacement(self: object) -> str:
            return "replacement"

        self.assertIs(await return_self_after_method(empty)(owner), owner)
        self.assertEqual(await return_self_after_method(replacement)(owner), "replacement")

    def test_backoff_validation_sequence_and_reset(self) -> None:
        with self.assertRaises(ValueError):
            BackoffConfig(1, 1, 2, 0)
        with self.assertRaises(ValueError):
            BackoffConfig(1, 2, 1, 0)

        backoff = Backoff(BackoffConfig(1, 8, 2, 0))
        self.assertEqual([next(backoff), next(backoff), next(backoff)], [1, 2, 4])
        self.assertEqual(backoff.counter, 3)
        backoff.reset()
        self.assertEqual((backoff.current_delay, backoff.next_delay, backoff.counter), (0, 1, 0))

    def test_backoff_rejects_jitter_above_maximum(self) -> None:
        backoff = Backoff(BackoffConfig(1, 2, 2, 1))
        with patch("pyromax.utils.backoff.normalvariate", return_value=3):
            with self.assertRaises(BackoffError):
                next(backoff)
