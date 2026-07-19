# scripts/trohub_client.py

A ready-to-run Python client for the TROHUB API. Covers every endpoint documented in
`../references/*.md`, with async task polling, rate-limit backoff, and unified error handling
already built in — don't hand-roll `requests` calls from scratch, use/extend this.

## Setup

```bash
pip install -r requirements.txt
export TROHUB_API_KEY="your_api_key_here"
export TROHUB_BASE_URL="https://YOUR-SUBDOMAIN.api.trohub.com/v1"   # replace with the real subdomain from the user's account
```

## CLI usage

```bash
# Recent TRO lawsuits
python -m scripts.trohub_client tro-recent --days 7 --limit 20

# Entries/evidence for one case
python -m scripts.trohub_client tro-entries --docket-id fdb41b2e-8e56-4eb8-96ef-042d919c5e01

# Check a listing title for word-trademark conflicts (sync, fast)
python -m scripts.trohub_client check-title --title "Ergonomic Chair" --short-desc "Comfortable design for office work"

# Reverse-citation / prior-art search for design patents
python -m scripts.trohub_client patents-reverse --patent-numbers D905805,D1010755 --grouped

# Submit a product photo for image-based search (async — this command submits AND waits for the result)
python -m scripts.trohub_client check-image \
  --image https://example.com/images/product.jpg \
  --sources designPatent,trademark,copyright \
  --product-name "wireless headphone"

# Task history / cleanup
python -m scripts.trohub_client history --page 1 --page-size 10
python -m scripts.trohub_client delete-task --task-id h0d0a0b3-f09c-4824-a745-0d29759c253h
python -m scripts.trohub_client retry-task --task-id h0d0a0b3-f09c-4824-a745-0d29759c253h
```

## Library usage

```python
from scripts.trohub_client import TrohubClient, TrohubAPIError, TrohubTaskTimeout

client = TrohubClient()  # reads TROHUB_API_KEY / TROHUB_BASE_URL from env
# or: TrohubClient(api_key="...", base_url="https://your-subdomain.api.trohub.com/v1")

# One-shot: submit + poll + get final result, for one image across one or more sources
result = client.check_image(
    "https://example.com/images/product.jpg",
    sources=["designPatent"],          # any subset of: trademark, designPatent, copyright
    product_name="wireless headphone", # strongly recommended for designPatent
    timeout=180,                        # seconds to wait before raising TrohubTaskTimeout
)
print(client.summarize(result))         # plain-language risk summary
# result is also the full parsed JSON `data` object if you need raw fields

# Synchronous listing-title check
matches = client.trademark_keyword_search(title="Ergonomic Chair")

# TRO monitoring
cases = client.tro_recent(days=7, limit=20)
entries = client.tro_entries(cases[0]["docketID"])

# Design patent prior art
citations = client.patents_reverse_search_grouped(["D905805", "D1010755"])
```

### Bulk-screening many SKUs

For screening many product photos, don't call `check_image()` in a tight loop back-to-back —
each call blocks until that task completes. Instead, submit multiple tasks (respecting the
3-concurrent-task limit) and poll them independently:

```python
client = TrohubClient()

task_ids = []
for sku in skus:
    images = [{
        "imageID": sku["id"],
        "image": sku["image_url"],
        "searchScope": client._build_search_scope(["designPatent"], product_name=sku["name"]),
    }]
    task_ids.append(client.submit_image_search(images))
    time.sleep(1)  # small stagger to stay under the 3-concurrent-task limit

for tid in task_ids:
    status = client.wait_for_task(tid, timeout=180)
    print(client.summarize(status))
```

## Error handling

Every failed call raises `TrohubAPIError` with `.code`, `.message`, `.details`, `.http_status`
attributes — match on `.code` against the table in `../references/errors.md`. Rate-limit errors
(`BUSINESS_RATE_LIMIT_EXCEEDED`) are already retried automatically with backoff before the
exception is raised, and the client proactively slows down when `X-RateLimit-Remaining` gets low.

`wait_for_task()` / `check_image()` raise `TrohubTaskTimeout` if a task doesn't finish within
the given `timeout` — this doesn't mean it failed, just that it's still running; call
`get_task_status(task_id)` again later, or check `get_history()`.
