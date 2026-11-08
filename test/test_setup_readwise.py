import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("setup", Path(__file__).parents[1] / "scripts/setup_readwise.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class FakeAPI:
    def __init__(self, books=None):
        self.library = books or []
        self.posts = []

    def books(self):
        return self.library.copy()

    def request(self, path, body):
        assert path == "books"
        self.posts.append(body)
        return {"results": [{"status": "created", "book_id": 123}]}


def epub(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="book.opf"/></rootfiles></container>')
        z.writestr("book.opf", '<package xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata>'
                   '<dc:title>Example Book</dc:title><dc:creator>Example Author</dc:creator></metadata></package>')


class SetupTest(unittest.TestCase):
    def test_status_uses_books_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp)
            setup.save(card / ".crosspoint/readwise/config.json", {"token": "highlight-account"})
            setup.save(card / ".crosspoint/readwise-books/config.json", {"token": "books-account"})
            with patch("sys.argv", ["setup", "--card", tmp, "--status"]), patch.object(setup, "status") as status:
                setup.main()
                status.assert_called_once_with(card.resolve(), "books-account")

    def test_match_normalization_and_ambiguity(self):
        books = [{"id": 10, "title": "EXAMPLE  Book", "author": "Example Author"}]
        self.assertEqual(setup.choose_book(books, "Example Book", "Example Author"), 10)
        self.assertIsNone(setup.choose_book(books, "Different Book", "Example Author"))
        with self.assertRaises(ValueError):
            setup.choose_book(books * 2, "Example Book", "Example Author")

    def test_preserves_credentials_sidecar_and_attempted_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp)
            (card / "plugins/almanac").mkdir(parents=True)
            token = card / "plugins/almanac/token.json"
            token.write_text('{"token":"synthetic-almanac-token"}')
            before = token.read_bytes()
            book = card / "example.epub"
            epub(book)
            sidecar = Path(str(book) + ".meta.json")
            sidecar.write_text('{"other_plugin":"keep-me"}')
            root = setup.account_root(card, "synthetic-readwise-token")
            queued = root / "queue" / ("0" * 64 + ".json")
            setup.save(queued, {"book_id": 0, "event": {"vars": {"book": "/example.epub", "document": setup.document_id(book)}}})
            untouched = root / "queue" / ("1" * 64 + ".json")
            setup.save(untouched, {"book_id": 456, "event": {"vars": {"book": "/example.epub"}}})
            api = FakeAPI()
            self.assertEqual(setup.provision(card, "synthetic-readwise-token", "Etc/UTC", api, True), (1, 0, 0))
            self.assertEqual(token.read_bytes(), before)
            meta = setup.load(sidecar)
            self.assertEqual(meta["other_plugin"], "keep-me")
            self.assertEqual(meta["readwise_books_id"], 123)
            self.assertEqual(meta["readwise_books_account"], root.name)
            self.assertEqual(setup.load(queued)["book_id"], 123)
            self.assertEqual(setup.load(untouched)["book_id"], 456)
            self.assertEqual(api.posts, [{"items": [{"product": {"title": "Example Book", "author": "Example Author"}}]}])
            self.assertEqual(setup.load(card / ".crosspoint/readwise-books/config.json")["token"], "synthetic-readwise-token")

    def test_missing_book_does_not_create_without_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp); epub(card / "example.epub")
            api = FakeAPI()
            self.assertEqual(setup.provision(card, "synthetic-token", "Etc/UTC", api), (0, 1, 0))
            self.assertFalse(api.posts)

    def test_explicit_mapping_belongs_to_account(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp); epub(card / "example.epub")
            api = FakeAPI([{"id": 99, "title": "An edition", "author": "Author"}])
            counts = setup.provision(card, "synthetic-token", "Etc/UTC", api, mapping={"/example.epub": 999})
            self.assertEqual(counts, (0, 0, 1))
            self.assertFalse(Path(str(card / "example.epub") + ".meta.json").exists())


if __name__ == "__main__":
    unittest.main()
