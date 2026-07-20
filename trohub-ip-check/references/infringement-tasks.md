# Combined Infringement Image Search (async task lifecycle)

This is the core "upload a product photo, find out if it copies someone else's trademark/patent/copyright" workflow. It's **asynchronous**: submit → poll status → (optionally) delete/retry/list history.

There's one shared submission endpoint that can search **one, two, or all three** sources per image (trademark + design patent + copyright) in a single call. The single-source endpoints described in `references/trademarks.md`, `references/patents.md` (design patent search), and `references/copyright.md` are the *same underlying mechanism* with only one source enabled — read this file first for the shared task lifecycle, then the single-source file for that source's specific config fields.

---

## 1. Submit a task — `POST /infringement/image-search` (trademark-only calls) or `POST /infringement` (design patent / copyright / combined calls)

> Note: the docs show trademark-only examples hitting `/infringement/image-search` and design-patent/copyright/combined examples hitting `/infringement`. Use whichever path the user's account docs/sandbox show for the source(s) you're enabling — the request/response shape is identical either way.

**Enabling rules (important):**
- `trademarkEnabled` / `designPatentEnabled` / `copyrightEnabled` (booleans) turn each source on/off, per image.
- The matching detail object (`trademark` / `designPatent` / `copyright`) is **required** when its `Enabled` flag is `true` — sending `true` without the object returns a `400`.
- When a source's `Enabled` flag is `false`, omit its detail object (or leave it out entirely).
- **At least one source must be enabled**, or the request returns `400`.

**Request body**

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `taskID` | string | no | auto UUID | Your own task ID if you want one; otherwise the server generates it |
| `images` | array | yes | — | 1–10 images |
| `images[].imageID` | string | no | `""` | Your own per-image identifier |
| `images[].image` | string | yes | — | Publicly reachable image URL, **or** base64 image data |
| `images[].searchScope` | object | yes | — | Per-image search config, described below |
| `images[].searchScope.trademarkEnabled` | boolean | yes | `false` | Enable graphic trademark search |
| `images[].searchScope.designPatentEnabled` | boolean | yes | `false` | Enable design patent search |
| `images[].searchScope.copyrightEnabled` | boolean | yes | `false` | Enable copyright search |
| `images[].searchScope.trademark` | object | conditionally | `null` | Required if `trademarkEnabled=true`. Fields: `autoSegment` (bool, AI auto-crop, default `false`), `minWidth`/`minHeight` (px, default `60`/`60`), `countries` (array, currently only `["US"]` supported) |
| `images[].searchScope.designPatent` | object | conditionally | `null` | Required if `designPatentEnabled=true`. Fields: `productName` (string, **recommend always setting** — improves match quality), `autoSegment` (bool, default `false`), `minWidth`/`minHeight` (px, default `100`/`100`), `removeBg` (bool, strip background before searching, default `false`), `countries` (array, e.g. `["US","EU"]`) |
| `images[].searchScope.copyright` | object | conditionally | `null` | Required if `copyrightEnabled=true`. Fields: `autoSegment` (bool, default `false`), `minWidth`/`minHeight` (px, default `80`/`80`) |

**Example — trademark only**
```bash
curl -X POST "https://api.trohub.com/v1/infringement/image-search" \
  -H "X-API-Key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"taskID":"trademark-demo-uuid","images":[{"imageID":"img-tm-001","image":"https://example.com/images/logo.png","searchScope":{"trademarkEnabled":true,"designPatentEnabled":false,"copyrightEnabled":false,"trademark":{"autoSegment":false,"countries":["US"]}}}]}'
```

**Example — design patent only**
```python
import requests

url = "https://api.trohub.com/v1/infringement"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {
    "taskID": "patent-demo-uuid",
    "images": [{
        "imageID": "img-dp-001",
        "image": "https://example.com/images/product.jpg",
        "searchScope": {
            "trademarkEnabled": False,
            "designPatentEnabled": True,
            "copyrightEnabled": False,
            "designPatent": {
                "autoSegment": False, "removeBg": False,
                "countries": ["US"], "productName": "wireless headphone"  # recommended
            }
        }
    }]
}
response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

**Example — copyright only**
```python
payload = {
    "taskID": "copyright-demo-uuid",
    "images": [{
        "imageID": "img-cr-001",
        "image": "https://example.com/images/artwork.jpg",
        "searchScope": {
            "trademarkEnabled": False, "designPatentEnabled": False, "copyrightEnabled": True,
            "copyright": {"autoSegment": False}
        }
    }]
}
```

**Example — all three sources at once on one image:** just set all three `Enabled` flags `true` and include all three detail objects.

**Response** (note: `success`, not `ok` — different envelope from most other endpoints)
```json
{
  "success": true,
  "message": "Element search tasks submitted successfully",
  "data": { "taskIDs": ["h0d0a0b3-f09c-4824-a745-0d29759c253h"] }
}
```

---

## 2. Poll task status — `GET /infringement/status/:taskID`

**curl**
```bash
curl -X GET "https://api.trohub.com/v1/infringement/status/h0d0a0b3-f09c-4824-a745-0d29759c253h" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Python**
```python
import requests
url = "https://api.trohub.com/v1/infringement/status/h0d0a0b3-f09c-4824-a745-0d29759c253h"
response = requests.get(url, headers={"X-API-Key": "YOUR_API_KEY"})
print(response.json())
```

**Task status values:** `pending` (queued) → `processing` (image preprocessing/detection) → `searching` (cross-referencing external databases) → `completed` / `failed`. Poll every few seconds until you see `completed` or `failed`; don't hammer it every second (respect the 60 req/min rate limit).

**Response shape** (`data`):

| Field | Notes |
|---|---|
| `taskID` | Echoes the task ID |
| `status` | See status values above |
| `imageResults[]` | One entry per submitted image |
| `createdAt` / `updatedAt` | ISO 8601 timestamps |

**`imageResults[]` fields:**

| Field | Notes |
|---|---|
| `imageId` | e.g. `img_{timestamp}_{index}` |
| `imageUrl` / `imageKey` | Where the (temporarily signed) uploaded image lives |
| `segments[]` | Auto-detected sub-element clips when `autoSegment` was enabled — empty array if not used/found. Each segment has its own `searchResults` and `copyrightTrace.ipCheck` |
| `searchResults` | Contains `trademark[]`, `designPatent[]`, and/or `copyrightTrace` depending on which sources were enabled |
| `searchResults.copyrightTrace.ipCheck` | VLM-based brand/IP recognition on the image itself. **Only present for copyright checks.** Fields: `resemblesKnownIP` (bool), `matchedIpName` (string, brand/IP name if found), `note` (string), `confidence` (`low`/`medium`/`high`), `confidenceScore` (0–100) |
| `status` | Per-image status, same values as task status |
| `searchScope` | Echoes back the config used |

**`segments[]` fields** (only populated when `autoSegment` finds sub-elements): `bbox` ([x,y,width,height]), `label` (e.g. `"[copyright] element description"`), `score` (0–1 confidence), `croppedImage`/`croppedKey`, `isOriginal` (bool), `detectType` (`"copyright"`, `"trademark"`, or `"designPatent"`), `searchResults` (same shape as top level, including `copyrightTrace.ipCheck`).

**`searchResults.trademark[]` fields:** `tmClass[]` (nice classification: `code` + `text`), `filingDate`/`regDate` (`YYYYMMDD`, `regDate:"0"` = not yet registered), `owners[]` (`name`+`country`), `regNumber`, `serialNumber`, `status` (`LIVE`/`DEAD`), `legalStatus` (`REGISTERED`/`PENDING`), `similarity` (`"XX.XX%"` string), `score` (0–1 number), `reason` (plain-language similarity/confusion-risk explanation), `imageUrl`, `imageID` (`orig_0` = original image, `seg_X_X` = a AI-segmented sub-element), `markText` (empty for pure graphic marks).

**`searchResults.designPatent[]` fields:** `title`, `pn` (patent number), `imageUrl`/`imageKey`, `score` (0–1), `similarity` (`"XX.XX%"`), `loc` (Locarno classification, e.g. `"10-04"`), `grantDate`/`fillingDate`/`expiryDate` (`"YYYY/MM/DD"`), `imageID`, `countryCode`, `expired` (bool), `owners[]`, `reason`.

**`searchResults.copyrightTrace` fields:** `entries[]` (each: `id`, `imageUrl`/`imageKey`, `title` of the matched page/product, `source` = the URL where it was found), `traceSummary` (AI summary of the matches), `analysis` (risk rollup — see below), `ipCheck` (VLM brand/IP recognition — see below).

**`analysis` fields (copyright risk rollup):** `potentialRightsHolders` (string or `null`), `riskScore` (0–100), `riskLevel` (`low` 0–40 / `medium` 41–70 / `high` 71–90 / `critical` 91–100), `explanation` (plain-language reasoning), `matchedEntries[]` (IDs referencing `entries[]`).

**Full example response (design patent match):**
```json
{
  "ok": true, "message": "success",
  "data": {
    "taskID": "0cd86dbf6378482e86c5b61e09a75017",
    "status": "completed",
    "imageResults": [{
      "imageId": "img_1783862445431_0",
      "imageUrl": "https://...r2.cloudflarestorage.com/.../...png",
      "segments": [],
      "searchResults": {
        "designPatent": [{
          "title": "Scale", "pn": "D0935924",
          "imageUrl": "https://tb-us-design-patents-....png",
          "score": 0.9209, "similarity": "92.09%",
          "loc": "10-04", "grantDate": "2021/11/16",
          "fillingDate": "2020/05/11", "expiryDate": "2036/11/16",
          "countryCode": "US", "expired": false,
          "owners": [{"name": "Tian Dai", "country": "CN"}],
          "reason": "Both are electronic scoop-scale products; overall silhouette, spoon-to-handle joint, and display/button layout are highly similar."
        }]
      },
      "status": "completed",
      "searchScope": { "trademarkEnabled": false, "designPatentEnabled": true, "copyrightEnabled": false,
        "designPatent": { "autoSegment": false, "removeBg": false, "countries": ["US"] } }
    }],
    "createdAt": "2026-07-12T22:20:49+09:00",
    "updatedAt": "2026-07-12T22:22:03+09:00"
  },
  "responseType": "v2"
}
```

---

## 3. History — `GET /infringement/history?page=1&pageSize=10`

Paginated list of the current API key's past search tasks.

| Param | Type | Required | Default |
|---|---|---|---|
| `page` | number | no | `1` |
| `pageSize` | number | no | `10` |

```python
import requests
url = "https://api.trohub.com/v1/infringement/history"
params = {"page": 1, "pageSize": 10}
print(requests.get(url, headers={"X-API-Key": "YOUR_API_KEY"}, params=params).json())
```

Response `data`: `items[]` (each with `taskID`, `status`, `imageCount`, `elementCount`, `createdAt`, `queryImageUrl`), plus `page`, `pageSize`, `total`, `totalPages`.

---

## 4. Delete a task — `DELETE /infringement/task/:taskID`

```bash
curl -X DELETE "https://api.trohub.com/v1/infringement/task/h0d0a0b3-f09c-4824-a745-0d29759c253h" \
  -H "X-API-Key: YOUR_API_KEY"
```
Response: `{ "success": true, "message": "Task deleted successfully", "data": null }`

## 5. Batch delete — `POST /infringement/tasks/batch-delete`

| Param | Type | Required | Notes |
|---|---|---|---|
| `taskIDs` | array | yes | At least 1 task ID |

```python
payload = {"taskIDs": ["h0d0a0b3-f09c-4824-a745-0d29759c253h", "i0e0b0b3-f09c-4824-a745-0d29759c253i"]}
requests.post("https://api.trohub.com/v1/infringement/tasks/batch-delete",
              headers={"X-API-Key": "YOUR_API_KEY"}, json=payload)
```

## 6. Retry a task — `POST /infringement/task/:taskID/retry`

Re-runs a failed (or old completed) task.
```bash
curl -X POST "https://api.trohub.com/v1/infringement/task/h0d0a0b3-f09c-4824-a745-0d29759c253h/retry" \
  -H "X-API-Key: YOUR_API_KEY"
```
Response: `{ "success": true, "message": "Task retried successfully", "data": null }`
