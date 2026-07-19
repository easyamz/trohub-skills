---
name: trohub-ip-check
description: Use this skill whenever the user wants to check a product, product image, listing title, or logo for intellectual property (IP) risk before selling on Amazon, TikTok Shop, eBay, Shopify, or any other marketplace — including trademark infringement, design patent infringement, copyright/artwork infringement, keyword/listing trademark conflicts, TRO (Temporary Restraining Order) lawsuit monitoring, and patent citation/freedom-to-operate research. Trigger this skill for requests like "check if this product image infringes any patent or trademark", "scan my listing title for trademark risk", "is this logo safe to use", "search recent TRO cases", "check this design patent's prior art / citations", or "build an IP risk-checking script/tool using the TROHUB API". This skill wraps the TROHUB API (open.trohub.com) — a paid, API-key-based IP data service built for cross-border e-commerce sellers, covering US/EU design patents, US word trademarks, graphic trademark image search, and global copyright/artwork tracing. Use this skill to write API calls directly (curl, Python, Node, etc.) — no SDK is required.
---

# TROHUB API — IP Infringement Risk Checking for Cross-Border Sellers

TROHUB is a paid IP (intellectual property) data API aimed at cross-border e-commerce sellers ("铺货卖家") who need to screen products **before** listing them, to avoid trademark/patent/copyright takedowns, account suspensions, or TRO lawsuits (common on Amazon and other US marketplaces).

This skill tells you (the coding agent) how to call the API correctly, and ships a ready-to-run client so you don't have to hand-write `requests` calls from scratch every time.

## Use the bundled script first

`scripts/trohub_client.py` is a complete, tested Python client that already implements every endpoint below, plus async task polling, rate-limit backoff, and unified error handling. **Prefer importing/extending this over writing new HTTP calls from scratch.** See `scripts/README.md` for full CLI + library usage. Quick taste:

```bash
pip install -r scripts/requirements.txt
export TROHUB_API_KEY="..."
export TROHUB_BASE_URL="https://YOUR-SUBDOMAIN.api.trohub.com/v1"

python -m scripts.trohub_client check-image --image https://example.com/product.jpg \
  --sources designPatent --product-name "wireless headphone"
```

```python
from scripts.trohub_client import TrohubClient
client = TrohubClient()
result = client.check_image("https://example.com/product.jpg", sources=["designPatent"], product_name="wireless headphone")
print(client.summarize(result))
```

If the user's task needs something the script doesn't cover (a different language, a custom workflow, a UI), read the relevant `references/*.md` file before writing new code for a specific endpoint — the request/response shapes have important quirks (see "Gotchas" below).

## What this API can do

| Goal | Endpoint group | Reference file |
|---|---|---|
| "Is my product photo copying a US/EU design patent, a graphic trademark, or a copyrighted artwork?" | Combined image search (`/infringement*`) | `references/infringement-tasks.md` |
| "Does my listing title/description contain a word that's a registered trademark?" | Word-mark keyword search | `references/trademarks.md` |
| "Show me prior-art / citation history for a design patent" (freedom-to-operate research) | Patent reverse-citation search | `references/patents.md` |
| "Am I at risk of being named in a new TRO lawsuit? What's in a specific case docket?" | TRO case monitoring | `references/tro-cases.md` |
| "Why did my request fail?" | Error codes | `references/errors.md` |

**Read the matching reference file before implementing.** Each one has exact parameter tables, full request/response JSON, and copy-pasteable curl + Python samples pulled straight from the official docs.

## Before you write any code

1. **Base URL.** The docs show `https://*.api.trohub.com/v1` — the `*` is a placeholder subdomain that is specific to each account/environment. Ask the user for their actual base URL (they'll find it next to the sandbox tester on each doc page, or their account dashboard), or use whatever base URL they've already given you. Don't invent a real hostname to replace the `*`.
2. **API key.** Every request needs a header:
   ```
   X-API-Key: your_api_key_here
   ```
   Get it from the user, or point them to `https://app.trohub.com/account/api-keys` (login required) if they don't have one yet. Never hardcode a placeholder key into a script the user will run — always read it from an environment variable or config file, e.g. `os.environ["TROHUB_API_KEY"]`.
3. **Response envelope.** Nearly every endpoint replies with:
   ```json
   { "ok": true, "message": "...", "responseType": "v2", "data": { ... } }
   ```
   But the **task submission endpoints** (image search) reply with a *different* shape — `success` instead of `ok`, and no `responseType`:
   ```json
   { "success": true, "message": "...", "data": { "taskIDs": ["..."] } }
   ```
   Always check for `ok === true` OR `success === true` depending on the endpoint (see reference files) — don't assume one envelope for every call.
4. **Rate limits.** 60 requests/minute per account (gateway-wide, all endpoints share this bucket), and async image-search tasks are capped at 3 concurrent per user (extra submissions auto-queue with a ~3s retry delay). Build in a small delay/backoff loop rather than firing requests in a tight loop, especially when polling task status.
5. **Async vs sync endpoints — this matters a lot:**
   - **Sync** (answer comes back immediately in the same response): TRO recent/entries, word-mark keyword search, patent reverse-citation search.
   - **Async** (submit → poll): all three image-based searches (trademark image search, design patent image search, copyright image search) and the combined multi-source search. You submit a task and get back a `taskID`, then poll `GET /infringement/status/:taskID` until `status` is `completed` or `failed`. **Never treat the submit response as the final result — it only contains `taskIDs`, not search results.**

## Typical workflows

### A. "Check this product photo for design patent / trademark / copyright risk"
1. Submit the image with `searchScope` enabling the sources you want (see `references/infringement-tasks.md` for the exact payload shape per source — trademark, design patent, and copyright each have their own required sub-object).
2. Poll `/infringement/status/:taskID` every few seconds until `status` is `completed`.
3. Read `imageResults[].searchResults` for matches, and `analysis.riskScore` / `analysis.riskLevel` (copyright) or per-match `score`/`similarity`/`reason` (trademark & patent) to summarize risk to the user in plain language — translate risk levels (`low`/`medium`/`high`/`critical`) rather than dumping raw JSON on the user.

### B. "Check my listing title for trademark risk before I publish it"
Call the word-mark keyword search once with `title` (and optionally `shortDesc`/`desc`) — this is synchronous, no polling needed. See `references/trademarks.md`.

### C. "Research prior art for a design patent before filing / defending"
Call the reverse-citation search (plain or grouped) with up to 50 US design patent numbers. See `references/patents.md`.

### D. "Monitor new TRO lawsuits" / "pull case details"
Use `/tro/recent` to list recent dockets, then `/tro/entries` with a `docketID` from that list to pull filings, attachments, and evidence images for a specific case. See `references/tro-cases.md`.

## Gotchas worth calling out to the user

- **The combined `/infringement` endpoints require matching Enabled flags to config objects.** If `trademarkEnabled: true` but you forget to include the `trademark: {...}` object, the API returns a 400. If a source is disabled, omit or set its config to `null`/leave it out — don't send it anyway.
- **At least one search source must be enabled** in a combined-search request, or you get a 400.
- **`countries` for trademark search currently only supports `["US"]`.** Design patent search supports more (e.g. `["US", "EU"]`).
- **`productName` for design patent search is optional but strongly recommended** — it meaningfully improves match quality (helps filter by product category). Encourage the user to always pass a short product description (e.g. `"wireless headphone"`), not leave it blank.
- **Design patent numbers must match the format** `D` or `USD` followed by 6–7 digits (e.g. `D905805`, `USD1084931`), otherwise you'll get `VALIDATION_PATENT_NUMBER_INVALID`.
- **Images can be a public URL or base64** — no need to host the image yourself if the user already has a public product image URL.
- **`queryAssessment` (whether the image resembles a known/famous IP) is only returned for copyright and trademark checks — never for design patent checks.**

## Building a reusable script for the user

If asked to build a small reusable tool (Python/Node script, CLI, or simple internal dashboard) around this API:
- Centralize the API key + base URL as config/env vars, not hardcoded.
- Wrap the submit → poll loop into one helper function (e.g. `run_image_search(image_url, sources) -> results`) so the user doesn't have to think about async polling every time.
- Add a simple backoff (e.g. poll every 3–5s, timeout after ~2 minutes — design-patent-heavy composite searches can take a bit longer than a single trademark check).
- Translate `riskLevel`/`similarity`/`score` fields into a short human summary (e.g. "⚠️ High risk: 92% visual match to US Design Patent D0935924, filed 2020, still active until 2036") rather than just printing raw JSON — this is the main value sellers want.
- For bulk screening (many SKUs), respect the 60 req/min and 3-concurrent-task limits — queue requests rather than blasting them all at once.

See `references/errors.md` for the full error-code table to handle in your error branches.

## Files in this skill

```
trohub-ip-check/
├── SKILL.md
├── scripts/
│   ├── trohub_client.py   — full Python client + CLI (start here for any new code)
│   ├── requirements.txt
│   └── README.md          — CLI + library usage examples
└── references/
    ├── tro-cases.md
    ├── infringement-tasks.md
    ├── patents.md
    ├── trademarks.md
    ├── copyright.md
    └── errors.md
```
