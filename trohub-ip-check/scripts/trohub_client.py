#!/usr/bin/env python3
"""
trohub_client.py — Minimal, dependency-light Python client for the TROHUB IP API.

Covers every endpoint in the TROHUB docs (https://open.trohub.com/):
  - TRO case monitoring        (tro_recent, tro_entries)
  - Word-mark keyword search   (trademark_keyword_search)
  - Design patent citations    (patents_reverse_search, patents_reverse_search_grouped)
  - Image-based infringement search (submit_image_search + wait_for_task), covering
    graphic trademark / design patent / copyright sources, alone or combined
  - Task management            (get_history, delete_task, batch_delete_tasks, retry_task)

Usage
-----
    export TROHUB_API_KEY="your_api_key_here"
    export TROHUB_BASE_URL="https://api.trohub.com/v1"

    python -m scripts.trohub_client tro-recent --days 7 --limit 20
    python -m scripts.trohub_client check-title --title "Ergonomic Chair"
    python -m scripts.trohub_client check-image --image https://example.com/product.jpg \
        --sources trademark,designPatent,copyright --product-name "wireless headphone"

Or import as a library:

    from scripts.trohub_client import TrohubClient

    client = TrohubClient()  # reads TROHUB_API_KEY / TROHUB_BASE_URL from env
    result = client.check_image(
        "https://example.com/product.jpg",
        sources=["designPatent"],
        product_name="wireless headphone",
    )
    print(client.summarize(result))

Only the standard library + `requests` are required (`pip install requests`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

class TrohubAPIError(Exception):
    """Raised for any non-success TROHUB API response."""

    def __init__(self, code: str, message: str, details: Any = None, http_status: Optional[int] = None):
        self.code = code
        self.message = message
        self.details = details
        self.http_status = http_status
        super().__init__(f"[{code}] {message}" + (f" — {details}" if details else ""))


class TrohubTaskTimeout(Exception):
    """Raised when an async task doesn't reach a terminal state within the given timeout."""


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------

class TrohubClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
        max_retries: int = 5,
    ):
        self.api_key = api_key or os.environ.get("TROHUB_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No API key provided. Pass api_key=... or set the TROHUB_API_KEY env var. "
                "Get a key at https://app.trohub.com/account/api-keys"
            )

        self.base_url = (base_url or os.environ.get("TROHUB_BASE_URL", "")).rstrip("/")
        if not self.base_url:
            raise ValueError(
                "No base URL provided. Pass base_url='https://api.trohub.com/v1' or "
                "set the TROHUB_BASE_URL env var."
            )

        self.session = session or requests.Session()
        self.max_retries = max_retries

    # -- low-level request plumbing ---------------------------------------

    def _request(self, method: str, path: str, json_body: Optional[dict] = None,
                 params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = {"X-API-Key": self.api_key}
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        attempt = 0
        while True:
            attempt += 1
            resp = self.session.request(method, url, headers=headers, json=json_body, params=params, timeout=30)

            # Respect rate-limit headers proactively even on success.
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None and remaining.isdigit() and int(remaining) <= 1:
                reset = resp.headers.get("X-RateLimit-Reset")
                if reset and reset.isdigit():
                    sleep_for = max(0, int(reset) - int(time.time())) + 0.5
                    time.sleep(min(sleep_for, 10))

            try:
                data = resp.json()
            except ValueError:
                resp.raise_for_status()
                raise TrohubAPIError("NON_JSON_RESPONSE", "API returned a non-JSON body", resp.text, resp.status_code)

            ok = data.get("ok", data.get("success"))
            if ok:
                return data

            error = data.get("error") or {}
            code = error.get("code") or data.get("code") or "UNKNOWN_ERROR"
            message = data.get("message") or error.get("message") or "Unknown TROHUB API error"
            details = error.get("details")

            if code == "BUSINESS_RATE_LIMIT_EXCEEDED" and attempt <= self.max_retries:
                backoff = min(2 ** attempt, 30)
                time.sleep(backoff)
                continue

            raise TrohubAPIError(code, message, details, resp.status_code)

    # -- TRO case monitoring ------------------------------------------------

    def tro_recent(self, days: int = 7, limit: int = 50) -> dict:
        """List recent TRO cases (max 7 days back, max 100 results)."""
        return self._request("POST", "/tro/recent", json_body={"days": days, "limit": limit})["data"]

    def tro_entries(self, docket_id: str) -> dict:
        """Get all filed entries (documents/evidence) for one TRO case."""
        return self._request("POST", "/tro/entries", json_body={"docketID": docket_id})["data"]

    # -- Word-mark keyword search --------------------------------------------

    def trademark_keyword_search(
        self,
        title: str,
        short_desc: str = "",
        desc: str = "",
        class_codes: Optional[List[str]] = None,
        skip_stop_words: bool = True,
        skip_numbers: bool = True,
        custom_stop_words: Optional[List[str]] = None,
    ) -> dict:
        """Check a listing title/description for registered US word-trademark conflicts. Synchronous."""
        payload = {
            "title": title,
            "shortDesc": short_desc,
            "desc": desc,
            "classCodes": class_codes or [],
            "skipStopWords": skip_stop_words,
            "skipNumbers": skip_numbers,
            "customStopWords": custom_stop_words or [],
        }
        return self._request("POST", "/trademarks/word-mark/keyword-search", json_body=payload)["data"]

    # -- Design patent reverse-citation search -------------------------------

    def patents_reverse_search(self, patent_numbers: List[str]) -> list:
        """Get prior-art citations for up to 50 US design patents. Synchronous."""
        return self._request(
            "POST", "/patents/design/reverse-search", json_body={"patentNumbers": patent_numbers}
        )["data"]

    def patents_reverse_search_grouped(self, patent_numbers: List[str]) -> dict:
        """Same as patents_reverse_search but grouped into {cited, citedBy}."""
        return self._request(
            "POST", "/patents/design/reverse-search/grouped", json_body={"patentNumbers": patent_numbers}
        )["data"]

    # -- Image-based infringement search (async task lifecycle) -------------

    @staticmethod
    def _build_search_scope(
        sources: Iterable[str],
        *,
        product_name: str = "",
        countries_trademark: Optional[List[str]] = None,
        countries_patent: Optional[List[str]] = None,
        auto_segment: bool = False,
        remove_bg: bool = False,
    ) -> dict:
        sources = set(sources)
        scope: Dict[str, Any] = {
            "trademarkEnabled": "trademark" in sources,
            "designPatentEnabled": "designPatent" in sources,
            "copyrightEnabled": "copyright" in sources,
        }
        if "trademark" in sources:
            scope["trademark"] = {
                "autoSegment": auto_segment,
                "minWidth": 60,
                "minHeight": 60,
                "countries": countries_trademark or ["US"],
            }
        if "designPatent" in sources:
            scope["designPatent"] = {
                "productName": product_name,
                "autoSegment": auto_segment,
                "minWidth": 100,
                "minHeight": 100,
                "removeBg": remove_bg,
                "countries": countries_patent or ["US"],
            }
        if "copyright" in sources:
            scope["copyright"] = {
                "autoSegment": auto_segment,
                "minWidth": 80,
                "minHeight": 80,
            }
        return scope

    def submit_image_search(
        self,
        images: List[Dict[str, Any]],
        task_id: Optional[str] = None,
    ) -> str:
        """
        Low-level submit. `images` is a list of dicts like:
            {"imageID": "img-1", "image": "<url or base64>", "searchScope": {...}}
        Build searchScope with _build_search_scope() or by hand per the docs.
        Returns the submitted taskID (uses the first one if multiple are returned).
        """
        payload: Dict[str, Any] = {"images": images}
        if task_id:
            payload["taskID"] = task_id
        # Endpoint path is the same regardless of which sources are enabled.
        data = self._request("POST", "/infringement", json_body=payload)
        task_ids = data["data"]["taskIDs"]
        return task_ids[0]

    def check_image(
        self,
        image: str,
        sources: List[str],
        *,
        product_name: str = "",
        countries_trademark: Optional[List[str]] = None,
        countries_patent: Optional[List[str]] = None,
        auto_segment: bool = False,
        remove_bg: bool = False,
        image_id: str = "img-0",
        task_id: Optional[str] = None,
        poll_interval: float = 4.0,
        timeout: float = 180.0,
    ) -> dict:
        """
        High-level helper: submit ONE image for search across one or more sources
        (any of "trademark", "designPatent", "copyright") and block until the task
        completes or fails. Returns the full status response's `data` dict.
        """
        valid = {"trademark", "designPatent", "copyright"}
        bad = set(sources) - valid
        if bad:
            raise ValueError(f"Unknown source(s): {bad}. Must be a subset of {valid}")
        if not sources:
            raise ValueError("At least one source must be specified")

        scope = self._build_search_scope(
            sources,
            product_name=product_name,
            countries_trademark=countries_trademark,
            countries_patent=countries_patent,
            auto_segment=auto_segment,
            remove_bg=remove_bg,
        )
        images = [{"imageID": image_id, "image": image, "searchScope": scope}]
        tid = self.submit_image_search(images, task_id=task_id)
        return self.wait_for_task(tid, poll_interval=poll_interval, timeout=timeout)

    def get_task_status(self, task_id: str) -> dict:
        return self._request("GET", f"/infringement/status/{task_id}")["data"]

    def wait_for_task(self, task_id: str, poll_interval: float = 4.0, timeout: float = 180.0) -> dict:
        """Poll a task until status is 'completed' or 'failed', or raise TrohubTaskTimeout."""
        start = time.time()
        while True:
            status = self.get_task_status(task_id)
            if status["status"] in ("completed", "failed"):
                return status
            if time.time() - start > timeout:
                raise TrohubTaskTimeout(
                    f"Task {task_id} still '{status['status']}' after {timeout}s — try again later "
                    f"with wait_for_task(task_id, timeout=<bigger>) or check get_history()."
                )
            time.sleep(poll_interval)

    # -- Task management ------------------------------------------------------

    def get_history(self, page: int = 1, page_size: int = 10) -> dict:
        return self._request("GET", "/infringement/history", params={"page": page, "pageSize": page_size})["data"]

    def delete_task(self, task_id: str) -> None:
        self._request("DELETE", f"/infringement/task/{task_id}")

    def batch_delete_tasks(self, task_ids: List[str]) -> None:
        self._request("POST", "/infringement/tasks/batch-delete", json_body={"taskIDs": task_ids})

    def retry_task(self, task_id: str) -> None:
        self._request("POST", f"/infringement/task/{task_id}/retry")

    # -- Human-readable summaries ------------------------------------------

    @staticmethod
    def summarize(status_data: dict) -> str:
        """Turn a get_task_status()/check_image() result into a short, plain-language report."""
        lines = [f"Task {status_data.get('taskID')} — status: {status_data.get('status')}"]
        for img in status_data.get("imageResults", []):
            lines.append(f"\nImage {img.get('imageId')}:")
            results = img.get("searchResults", {}) or {}

            tm_matches = results.get("trademark") or []
            for m in sorted(tm_matches, key=lambda x: -x.get("score", 0))[:5]:
                lines.append(
                    f"  [Trademark] {m.get('similarity')} match — \"{m.get('markText') or '(graphic only)'}\" "
                    f"({m.get('status')}/{m.get('legalStatus')}), reg#{m.get('regNumber') or 'n/a'} — {m.get('reason', '')}"
                )

            dp_matches = results.get("designPatent") or []
            for m in sorted(dp_matches, key=lambda x: -x.get("score", 0))[:5]:
                expired = "expired" if m.get("expired") else "ACTIVE until " + str(m.get("expiryDate"))
                lines.append(
                    f"  [Design patent] {m.get('similarity')} match — {m.get('pn')} \"{m.get('title')}\" "
                    f"({expired}) — {m.get('reason', '')}"
                )

            cr = results.get("copyrightTrace")
            if cr:
                analysis = cr.get("analysis", {}) or {}
                lines.append(
                    f"  [Copyright] risk: {analysis.get('riskLevel', 'unknown').upper()} "
                    f"({analysis.get('riskScore', '?')}/100) — {analysis.get('explanation', '')}"
                )
                for e in (cr.get("entries") or [])[:3]:
                    lines.append(f"      source: {e.get('source')}")

            qa = img.get("queryAssessment")
            if qa:
                lines.append(
                    f"  [Known-IP check] resembles known IP: {qa.get('resemblesKnownIP')} "
                    f"(confidence: {qa.get('confidence')}) — {qa.get('note', '')}"
                )

            if not (tm_matches or dp_matches or cr):
                lines.append("  No matches found for the enabled source(s).")

        return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="TROHUB API command-line helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("tro-recent", help="List recent TRO cases")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("tro-entries", help="Get entries for one TRO case")
    p.add_argument("--docket-id", required=True)

    p = sub.add_parser("check-title", help="Check a listing title/description for trademark conflicts")
    p.add_argument("--title", required=True)
    p.add_argument("--short-desc", default="")
    p.add_argument("--desc", default="")
    p.add_argument("--class-codes", default="", help="comma-separated Nice class codes, e.g. 020,025")

    p = sub.add_parser("patents-reverse", help="Reverse-citation search for US design patents")
    p.add_argument("--patent-numbers", required=True, help="comma-separated, e.g. D905805,D1010755")
    p.add_argument("--grouped", action="store_true")

    p = sub.add_parser("check-image", help="Submit an image for trademark/design-patent/copyright search and wait for results")
    p.add_argument("--image", required=True, help="public image URL (or base64 string)")
    p.add_argument("--sources", required=True, help="comma-separated subset of: trademark,designPatent,copyright")
    p.add_argument("--product-name", default="", help="recommended for designPatent — short product description")
    p.add_argument("--timeout", type=float, default=180.0)

    p = sub.add_parser("history", help="List past search tasks")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--page-size", type=int, default=10)

    p = sub.add_parser("delete-task", help="Delete one task")
    p.add_argument("--task-id", required=True)

    p = sub.add_parser("retry-task", help="Retry a failed/old task")
    p.add_argument("--task-id", required=True)

    args = parser.parse_args(argv)
    client = TrohubClient()

    try:
        if args.command == "tro-recent":
            _print_json(client.tro_recent(days=args.days, limit=args.limit))

        elif args.command == "tro-entries":
            _print_json(client.tro_entries(args.docket_id))

        elif args.command == "check-title":
            codes = [c.strip() for c in args.class_codes.split(",") if c.strip()]
            _print_json(client.trademark_keyword_search(
                title=args.title, short_desc=args.short_desc, desc=args.desc, class_codes=codes
            ))

        elif args.command == "patents-reverse":
            numbers = [n.strip() for n in args.patent_numbers.split(",") if n.strip()]
            if args.grouped:
                _print_json(client.patents_reverse_search_grouped(numbers))
            else:
                _print_json(client.patents_reverse_search(numbers))

        elif args.command == "check-image":
            sources = [s.strip() for s in args.sources.split(",") if s.strip()]
            result = client.check_image(
                args.image, sources, product_name=args.product_name, timeout=args.timeout
            )
            print(client.summarize(result))
            print("\n--- raw JSON ---")
            _print_json(result)

        elif args.command == "history":
            _print_json(client.get_history(page=args.page, page_size=args.page_size))

        elif args.command == "delete-task":
            client.delete_task(args.task_id)
            print(f"Deleted task {args.task_id}")

        elif args.command == "retry-task":
            client.retry_task(args.task_id)
            print(f"Retried task {args.task_id}")

    except TrohubAPIError as e:
        print(f"TROHUB API error: {e}", file=sys.stderr)
        return 1
    except TrohubTaskTimeout as e:
        print(f"Timed out: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
