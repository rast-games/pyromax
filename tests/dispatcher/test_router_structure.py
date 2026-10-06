import unittest

from pyromax.dispatcher.Router import Router


class RouterStructureTest(unittest.TestCase):
    def test_include_builds_head_and_tail_chains(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        grandchild = Router(name="grandchild")
        root.include_router(child)
        child.include_router(grandchild)

        self.assertEqual(list(root.chain_tail), [root, child, grandchild])
        self.assertEqual(list(grandchild.chain_head), [grandchild, child, root])

    def test_invalid_self_duplicate_and_circular_links_are_rejected(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        with self.assertRaises(ValueError):
            root.include_router(object())  # type: ignore[arg-type]
        with self.assertRaises(RuntimeError):
            root.include_router(root)
        root.include_router(child)
        with self.assertRaises(RuntimeError):
            Router(name="other").include_router(child)
        with self.assertRaises(RuntimeError):
            child.include_router(root)

    def test_include_routers_requires_at_least_one_child(self) -> None:
        with self.assertRaisesRegex(ValueError, "At least one"):
            Router().include_routers()
