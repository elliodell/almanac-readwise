#!/usr/bin/env python3
"""Provision the optional direct Readwise Books mirror over a mounted SD card.

Uses Python's standard library. Credentials are read from a private file or
prompt, never a command-line argument. Does not upload EPUBs or book text.
"""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from zoneinfo import ZoneInfo

API = "https://readwise.io/books/api/v1/"
REPO = Path(__file__).resolve().parents[1]
PLUGIN_FILES = ("manifest.json", "device.json", "README.md", "DETAILS.md")
MAX_XML = 2 * 1024 * 1024


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    """Atomic host write; never put a credential in output or a repo file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".setup-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward an access token to a redirected host.


class Readwise:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, path, body=None):
        url = path if path.startswith("https://") else API + path
        if not url.startswith(API):
            raise ValueError("Unexpected API pagination URL")
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Authorization": "Token " + self.token,
            "Content-Type": "application/json",
            "User-Agent": "Almanac-ReadwiseBooks-Setup/1",
        })
        try:
            with self.opener.open(req, timeout=30) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise ValueError("API response exceeded the size limit")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Readwise returned HTTP {e.code}; nothing was retried") from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError("Readwise connection failed; nothing was retried") from None

    def books(self):
        result, url, seen = [], "books?limit=100", set()
        for _ in range(200):
            if url in seen:
                raise ValueError("Repeated API pagination URL")
            seen.add(url)
            page = self.request(url)
            result.extend(page["results"])
            url = page.get("next")
            if not url:
                return result
        raise ValueError("Library exceeds setup's 20,000-book limit")


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def epub_metadata(path):
    def xml(archive, name):
        info = archive.getinfo(name)
        if info.file_size > MAX_XML:
            raise ValueError("EPUB metadata exceeds the size limit")
        raw = archive.read(info)
        # Metadata needs no custom entities; reject DTDs before parsing.
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("EPUB metadata contains a DTD")
        return ET.fromstring(raw)

    with zipfile.ZipFile(path) as archive:
        container = xml(archive, "META-INF/container.xml")
        roots = [node for node in container.iter() if node.tag.split("}")[-1] == "rootfile"]
        if not roots:
            raise ValueError("EPUB has no package document")
        package = xml(archive, roots[0].attrib["full-path"])
        def values(name):
            return ["".join(node.itertext()).strip() for node in package.iter()
                    if node.tag == "{http://purl.org/dc/elements/1.1/}" + name]
        titles, authors = values("title"), values("creator")
        if not titles or not authors or not titles[0] or not authors[0]:
            raise ValueError("EPUB needs a title and author for matching")
        title, author = titles[0], ", ".join(authors)
        if len(title) > 511 or len(author) > 511:
            raise ValueError("EPUB title or author is too long")
        return title, author


def choose_book(books, title, author):
    matches = [b for b in books if b.get("status") != "deleted" and
               normalized(b.get("title")) == normalized(title) and
               normalized(b.get("author")) == normalized(author)]
    if len(matches) > 1:
        raise ValueError("Multiple Readwise editions match; use --map-file to choose an ID")
    return matches[0]["id"] if matches else None


def account_root(card, token):
    return card / ".crosspoint/readwise-books" / hashlib.sha256(token.encode()).hexdigest()


def document_id(path):
    """CrossPoint/KOReader partial content hash; no entire EPUB is loaded."""
    result = hashlib.md5()
    size = path.stat().st_size
    with path.open("rb") as f:
        for offset in [0] + [1024 << (2 * i) for i in range(11)]:
            if offset < size:
                f.seek(offset)
                result.update(f.read(min(1024, size - offset)))
    return result.hexdigest()


def status(card, token):
    root = account_root(card, token)
    counts = {"waiting": 0, "unmapped": 0, "uncertain": 0, "receipts": 0, "damaged": 0}
    for path in (root / "queue").glob("*.json"):
        try:
            item = load(path)
            if not item.get("book_id"):
                counts["unmapped"] += 1
            elif (root / "history" / (path.stem + ".attempt")).exists():
                counts["uncertain"] += 1
            else:
                counts["waiting"] += 1
        except (ValueError, OSError):
            counts["damaged"] += 1
    counts["receipts"] = len(list((root / "history").glob("*.receipt.json")))
    print(json.dumps(counts, indent=2))


def provision(card, token, timezone, api, create_missing=False, mapping=None):
    books = api.books()  # Validate access before changing the SD card.
    by_id = {int(b["id"]): b for b in books if b.get("status") != "deleted"}
    mapping = mapping or {}
    linked, missing, failures = {}, [], []
    # Preserve the installed Almanac token and history: copy only tracked plugin files.
    for epub in sorted(card.rglob("*")):
        if epub.suffix.lower() != ".epub" or epub.name.startswith("._") or epub.is_symlink():
            continue
        relative = "/" + epub.relative_to(card).as_posix()
        if any(part.startswith(".") for part in epub.relative_to(card).parts):
            continue
        try:
            title, author = epub_metadata(epub)
            chosen = mapping.get(relative)
            if chosen is not None:
                if type(chosen) is not int or chosen not in by_id:
                    raise ValueError("Mapped book ID is not in this Readwise library")
            else:
                chosen = choose_book(books, title, author)
            if chosen is None and create_missing:
                response = api.request("books", {"items": [{"product": {"title": title, "author": author}}]})
                results = response.get("results", [])
                if len(results) != 1 or results[0].get("status") not in ("created", "existing"):
                    raise RuntimeError("Readwise could not create or find the book")
                chosen = results[0].get("book_id")
                if type(chosen) is not int or chosen <= 0:
                    raise RuntimeError("Readwise returned an invalid book ID")
                books.append({"id": chosen, "title": title, "author": author, "status": "want_to_read"})
            if chosen is None:
                missing.append(relative)
                continue
            sidecar = Path(str(epub) + ".meta.json")
            meta = load(sidecar) if sidecar.exists() else {}
            if not isinstance(meta, dict):
                raise ValueError("Existing book sidecar is not an object")
            if sidecar.exists():
                backup = Path(str(sidecar) + ".before-readwise")
                if not backup.exists():
                    shutil.copy2(sidecar, backup)
            meta["readwise_books_id"] = chosen
            meta["readwise_books_account"] = hashlib.sha256(token.encode()).hexdigest()
            meta["readwise_books_document"] = document_id(epub)
            if len((json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode()) > 2048:
                raise ValueError("Book sidecar exceeds the firmware's 2 KiB limit")
            save(sidecar, meta)
            linked[relative] = {"id": chosen, "document": meta["readwise_books_document"]}
        except (ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as e:
            failures.append({"file": relative, "error": str(e)})
    plugin = card / "plugins/almanac"
    plugin.mkdir(parents=True, exist_ok=True)
    for name in PLUGIN_FILES:
        shutil.copyfile(REPO / "almanac.crosspoint-plugin" / name, plugin / name)
    shutil.copyfile(REPO / "LICENSE", plugin / "LICENSE")
    root = account_root(card, token)
    # Only previously unmapped, never-attempted records may acquire a book ID.
    for path in (root / "queue").glob("*.json"):
        item = load(path)
        book = item.get("event", {}).get("vars", {}).get("book")
        history = root / "history" / path.stem
        document = item.get("event", {}).get("vars", {}).get("document")
        if (item.get("book_id") == 0 and book in linked and document == linked[book]["document"]
                and not any(history.parent.glob(history.name + ".*"))):
            item["book_id"] = linked[book]["id"]
            save(path, item)
    save(card / ".crosspoint/readwise-books/config.json", {"enabled": True, "token": token, "timezone": timezone})
    # This report stays on the card, with no credential, and is never printed.
    save(card / ".crosspoint/readwise-books/setup-report.json", {"linked": linked, "unmatched": missing, "errors": failures})
    return len(linked), len(missing), len(failures)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--card", type=Path, required=True, help="Mounted reader SD card")
    p.add_argument("--token-file", type=Path, help="Private JSON file containing token")
    p.add_argument("--timezone", default="Etc/UTC", help="IANA time zone, e.g. America/New_York")
    p.add_argument("--create-missing", action="store_true", help="Add unmatched EPUB titles/authors to Readwise Books")
    p.add_argument("--map-file", type=Path, help="Private JSON mapping /book.epub paths to Readwise book IDs")
    p.add_argument("--status", action="store_true", help="Show local queue totals without uploading")
    p.add_argument("--check-access", action="store_true", help="Check Readwise Books access without changing files")
    args = p.parse_args()
    card = args.card.resolve()
    if not card.is_dir() or not (card / ".crosspoint").is_dir():
        p.error("Choose a mounted CrossPoint SD card in USB Drive mode")
    if card == REPO or REPO in card.parents or card in REPO.parents:
        p.error("The SD card must be outside this source checkout")
    ZoneInfo(args.timezone)
    source = args.token_file or card / (".crosspoint/readwise-books/config.json" if args.status
                                      else ".crosspoint/readwise/config.json")
    token = load(source)["token"] if source.exists() else getpass.getpass("Readwise access token: ")
    if not isinstance(token, str) or not re.fullmatch(r"[!-~]{1,256}", token):
        p.error("Invalid Readwise token")
    if args.status:
        status(card, token)
        return
    api = Readwise(token)
    if args.check_access:
        print(f"Readwise Books access works; {len(api.books())} library entries.")
        return
    counts = provision(card, token, args.timezone, api, args.create_missing,
                       load(args.map_file) if args.map_file else None)
    print(f"Linked {counts[0]} EPUBs; {counts[1]} unmatched; {counts[2]} metadata errors.")
    print("Safely eject, install the companion firmware, restart, and read normally.")
    print("Run again after adding EPUBs. Almanac sign-in and history were preserved.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        # Do not include request objects, response bodies, or token contents.
        print(f"Setup stopped: {e}", file=sys.stderr)
        sys.exit(1)
