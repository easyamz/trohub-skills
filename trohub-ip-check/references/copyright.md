# Copyright / Artwork Module

Global copyright/artwork trace search (async task) — checks an image (artwork, pattern, character design, print, etc.) against a global database to find where else that image (or something very close to it) appears on the web, and rolls that up into a risk score. This reuses the shared async task lifecycle in `references/infringement-tasks.md` (submit → poll `GET /infringement/status/:taskID` → optionally delete/retry/history) — this file only covers the copyright-specific submit payload and result fields.

**Enabling rule:** `copyrightEnabled` must be `true`, and when it is, the `copyright` config object is **required** or you get a 400. You don't need to set `trademarkEnabled`/`designPatentEnabled` — omit them.

## Submit — `POST /infringement`

**Request**

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `taskID` | string | no | auto UUID | |
| `images` | array | yes | — | 1–10 images |
| `images[].imageID` | string | no | `""` | |
| `images[].image` | string | yes | — | Public URL or base64 |
| `images[].searchScope.copyrightEnabled` | boolean | yes | `false` | Set `true` |
| `images[].searchScope.copyright` | object | yes | — | See below |
| `images[].searchScope.copyright.autoSegment` | boolean | no | `false` | AI auto-crop detected elements — useful for a photo with multiple prints/patterns/characters in one image |
| `images[].searchScope.copyright.minWidth` | number | no | `80` | px |
| `images[].searchScope.copyright.minHeight` | number | no | `80` | px |

```bash
curl -X POST "https://*.api.trohub.com/v1/infringement" \
  -H "X-API-Key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"taskID":"copyright-demo-uuid","images":[{"imageID":"img-cr-001","image":"https://example.com/images/artwork.jpg","searchScope":{"copyrightEnabled":true,"copyright":{"autoSegment":false}}}]}'
```

```python
import requests
url = "https://*.api.trohub.com/v1/infringement"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {
    "taskID": "copyright-demo-uuid",
    "images": [{
        "imageID": "img-cr-001",
        "image": "https://example.com/images/artwork.jpg",
        "searchScope": { "copyrightEnabled": True, "copyright": {"autoSegment": False} }
    }]
}
print(requests.post(url, headers=headers, json=payload).json())
```

**Response:**
```json
{ "success": true, "message": "Element search tasks submitted successfully", "data": { "taskIDs": ["h0d0a0b3-f09c-4824-a745-0d29759c253h"] } }
```

Then poll `GET /infringement/status/:taskID`. The copyright-specific result lives under `searchResults.copyrightTrace`:

| Field | Notes |
|---|---|
| `entries[]` | Matched pages/products: `id`, `imageUrl`/`imageKey` (the matched image), `title` (page/product title), `source` (URL where found) |
| `traceSummary` | AI-written summary describing common characteristics/sources of the matches |
| `analysis` | Risk rollup: `potentialRightsHolders` (string or `null`), `riskScore` (0–100), `riskLevel` (`low` 0–40 / `medium` 41–70 / `high` 71–90 / `critical` 91–100), `explanation` (plain-language reasoning), `matchedEntries[]` (IDs referencing `entries[]`) |

Copyright checks also return `queryAssessment` per image (whether the image resembles a known/famous IP — character, brand art, etc.), same shape as documented in `references/infringement-tasks.md`.

**When presenting results to a seller:** lead with `riskLevel` and `traceSummary` in plain language, then list the top few `entries[]` sources as evidence, rather than dumping the full match list — sellers mainly want a clear go/no-go signal plus enough evidence to make their own call.
