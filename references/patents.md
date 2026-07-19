# Design Patent Module

Two different capabilities live here:
1. **Reverse-citation search** (sync) — given known patent numbers, find their prior art and who cites them. Useful for freedom-to-operate research, invalidity arguments, or checking how "crowded"/mature a design space is.
2. **Design patent image search** (async task) — given a product photo, find visually similar US/EU design patents. This is the same task-submit/poll lifecycle as `references/infringement-tasks.md` — read that file for the shared mechanics (status polling, response envelope, etc). This file only covers the design-patent-specific submit payload.

---

## 1. Reverse citation search — `POST /patents/design/reverse-search`

Synchronously returns, for each patent number given, its cited (prior-art) patents.

**Request**

| Param | Type | Required | Notes |
|---|---|---|---|
| `patentNumbers` | array | yes | 1–50 **US design patent numbers only**. Format: `D` or `USD` followed by 6–7 digits, e.g. `D905805`, `USD1084931` |

```bash
curl -X POST "https://*.api.trohub.com/v1/patents/design/reverse-search" \
  -H "X-API-Key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"patentNumbers":["D905805","D1010755","USD1084931"]}'
```

```python
import requests
url = "https://*.api.trohub.com/v1/patents/design/reverse-search"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {"patentNumbers": ["D905805", "D1010755", "USD1084931"]}
print(requests.post(url, headers=headers, json=payload).json())
```

**Response** — `data` is a flat array; each patent's `cited[]` lists what it references:
```json
{
  "ok": true, "message": "success",
  "data": [{
    "title": "Locking unit for pole assembly", "pn": "D0661981",
    "imageUrl": "https://tb-us-design-patents-....png?...(signed, time-limited URL)",
    "loc": "08-08",
    "cited": [
      { "docNumber": "5479836", "kind": "A", "country": "US", "date": 19960100 },
      { "docNumber": "6948878", "kind": "B1", "country": "US", "date": 20050900 }
    ],
    "grantDate": "2012/06/19", "fillingDate": "2010/03/24", "expiryDate": "2026/06/19",
    "expired": false,
    "owners": [{ "name": "ToolLab, Inc.", "country": "US" }]
  }],
  "responseType": "v2"
}
```
Note: `imageUrl` values are signed URLs that expire — don't cache them long-term; re-fetch if needed later.

---

## 2. Reverse citation search (grouped) — `POST /patents/design/reverse-search/grouped`

Same input as above, but the response is split into `cited` (what these patents reference — prior art) and `citedBy` (what references these patents — later patents building on this design). Easier to work with when you want a "who came before / who came after" view for one patent.

Same request format:
```json
{"patentNumbers":["D905805","D1010755","USD1084931"]}
```

**Response:**
```json
{
  "ok": true, "message": "success",
  "data": {
    "cited": [ { "title": "Locking unit for pole assembly", "pn": "D0661981", "...": "same fields as above" } ],
    "citedBy": [ { "title": "Gymnastics apparatus and equipment", "pn": "D0943040", "...": "same fields as above" } ]
  },
  "responseType": "v2"
}
```

---

## 3. Design patent image search (submit task) — `POST /infringement`

Submit a product photo to search for visually similar design patents. This reuses the shared async task lifecycle from `references/infringement-tasks.md` (submit → `GET /infringement/status/:taskID` → optionally delete/retry/history) — only the payload below is specific to design patents.

**Enabling rule:** `designPatentEnabled` must be `true`, and when it is, `designPatent` config object is **required** or you get a 400. You do not need to set `trademarkEnabled`/`copyrightEnabled` at all — omit them.

**Request**

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `taskID` | string | no | auto UUID | |
| `images` | array | yes | — | 1–10 images |
| `images[].imageID` | string | no | `""` | |
| `images[].image` | string | yes | — | Public URL or base64 |
| `images[].searchScope.designPatentEnabled` | boolean | yes | `false` | Set `true` |
| `images[].searchScope.designPatent` | object | yes | — | See below |
| `images[].searchScope.designPatent.productName` | string | no | `""` | **Recommended: always include a short product name/core keyword — meaningfully improves category filtering and match quality** |
| `images[].searchScope.designPatent.autoSegment` | boolean | no | `false` | AI auto-crop detected elements |
| `images[].searchScope.designPatent.minWidth` | number | no | `100` | px, used with autoSegment |
| `images[].searchScope.designPatent.minHeight` | number | no | `100` | px, used with autoSegment |
| `images[].searchScope.designPatent.removeBg` | boolean | no | `false` | Strip background before searching — good for plain product photos |
| `images[].searchScope.designPatent.countries` | array | yes | `["US"]` | e.g. `["US", "EU"]` |

```bash
curl -X POST "https://*.api.trohub.com/v1/infringement" \
  -H "X-API-Key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"taskID":"patent-demo-uuid","images":[{"imageID":"img-dp-001","image":"https://example.com/images/product.jpg","searchScope":{"designPatentEnabled":true,"designPatent":{"autoSegment":false,"removeBg":false,"countries":["US"],"productName":"wireless headphone"}}}]}'
```

```python
import requests
url = "https://*.api.trohub.com/v1/infringement"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {
    "taskID": "patent-demo-uuid",
    "images": [{
        "imageID": "img-dp-001",
        "image": "https://example.com/images/product.jpg",
        "searchScope": {
            "designPatentEnabled": True,
            "designPatent": {
                "autoSegment": False, "removeBg": False,
                "countries": ["US"], "productName": "wireless headphone"  # recommended
            }
        }
    }]
}
print(requests.post(url, headers=headers, json=payload).json())
```

**Response:**
```json
{ "success": true, "message": "Element search tasks submitted successfully", "data": { "taskIDs": ["h0d0a0b3-f09c-4824-a745-0d29759c253h"] } }
```
Then poll `GET /infringement/status/:taskID` — see `references/infringement-tasks.md` for the full result schema (`searchResults.designPatent[]` fields, risk fields, etc).
