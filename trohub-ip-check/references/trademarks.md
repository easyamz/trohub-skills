# Trademark Module

Two different capabilities:
1. **Word-mark keyword search** (sync) — checks the *text* of your listing title/description against registered US word trademarks. Great for a pre-publish listing check.
2. **Graphic trademark image search** (async task) — checks a *logo/graphic image* against registered US graphic trademarks. Same async task lifecycle as `references/infringement-tasks.md` — read that file for the shared mechanics; this file only covers the trademark-specific submit payload.

---

## 1. Word-mark keyword search — `POST /trademarks/word-mark/keyword-search`

Synchronously extracts n-grams/keywords from your listing title, short description, and long description, and checks them against registered word trademarks. Use this **before publishing a listing** to catch an accidental trademark term in the title (a very common cause of Amazon takedowns).

**Request**

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `title` | string | yes | `""` | Product title (auto-tokenized + n-gram extracted) |
| `shortDesc` | string | no | `""` | Short description text |
| `desc` | string | no | `""` | Long description text |
| `classCodes` | array | no | `[]` | Nice classification codes to filter by (e.g. `["020"]` for furniture) |
| `skipStopWords` | boolean | no | `true` | Filter out pure stop-words during n-gram extraction |
| `skipNumbers` | boolean | no | `true` | Filter out pure numbers |
| `customStopWords` | string[] | no | `[]` | Extra words to exclude from analysis (e.g. generic terms specific to your niche) |

```bash
curl -X POST "https://api.trohub.com/v1/trademarks/word-mark/keyword-search" \
  -H "X-API-Key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"title":"Ergonomic Chair","shortDesc":"Comfortable design for office work","desc":"A mesh back ergonomic office chair featuring dynamic lumbar support.","classCodes":["020"],"skipStopWords":true,"skipNumbers":true,"customStopWords":["chair","desk"]}'
```

```python
import requests
url = "https://api.trohub.com/v1/trademarks/word-mark/keyword-search"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {
    "title": "Ergonomic Chair",
    "shortDesc": "Comfortable design for office work",
    "desc": "A mesh back ergonomic office chair featuring dynamic lumbar support.",
    "classCodes": ["020"],
    "skipStopWords": True, "skipNumbers": True,
    "customStopWords": ["chair", "desk"]
}
print(requests.post(url, headers=headers, json=payload).json())
```

**Response** — `data` is split by which field the match came from (`title` / `shortDesc` / `desc`), each an array of matching word-mark records:
```json
{
  "ok": true, "message": "success",
  "data": {
    "title": [{
      "id": "4bc01932f2724e7d924c5d3ed610d304",
      "tmClass": [{ "code": "009", "text": "" }],
      "drawingCode": "3",
      "filingDate": "20081215",
      "markText": "CHAIR",
      "owners": [
        { "address": "620 CROSSROADS BOULEVARD\nCARY, NC 27518", "country": "US", "name": "EPIC GAMES, INC." }
      ],
      "regDate": "20111213", "regNumber": "4068973", "serialNumber": "77633411",
      "status": "LIVE", "legalStatus": "REGISTERED"
    }],
    "desc": [ "...same shape..." ],
    "shortDesc": [ "...same shape..." ]
  },
  "responseType": "v2"
}
```

Field notes: `status` is `LIVE` (active) or `DEAD` (abandoned/cancelled); `legalStatus` is `REGISTERED` or `PENDING`; `regDate: "0"` means not yet formally registered. `tmClass[]` gives Nice classification codes + descriptions — cross-check whether the matched mark's class actually overlaps with your product category before flagging it as a real risk (a word trademarked for pharmaceuticals is not necessarily a risk for a furniture listing).

**Tip:** run this on every new listing title before publishing — it's cheap (synchronous, one call) and catches one of the most common and easily-avoidable takedown triggers.

---

## 2. Graphic trademark image search (submit task) — `POST /infringement/image-search`

Submit a logo/graphic image to search for visually similar registered graphic trademarks. Reuses the shared async task lifecycle in `references/infringement-tasks.md` (submit → poll `GET /infringement/status/:taskID` → optionally delete/retry/history) — only the payload below is trademark-specific.

**Enabling rule:** `trademarkEnabled` must be `true`, and when it is, the `trademark` config object is **required** or you get a 400. You don't need to set `designPatentEnabled`/`copyrightEnabled` — omit them.

**Request**

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `taskID` | string | no | auto UUID | |
| `images` | array | yes | — | 1–10 images |
| `images[].imageID` | string | no | `""` | |
| `images[].image` | string | yes | — | Public URL or base64 |
| `images[].searchScope.trademarkEnabled` | boolean | yes | `false` | Set `true` |
| `images[].searchScope.trademark` | object | yes | — | See below |
| `images[].searchScope.trademark.autoSegment` | boolean | no | `false` | AI auto-crop detected elements (useful if the logo is embedded in a bigger product photo) |
| `images[].searchScope.trademark.minWidth` | number | no | `60` | px |
| `images[].searchScope.trademark.minHeight` | number | no | `60` | px |
| `images[].searchScope.trademark.countries` | array | yes | `["US"]` | **Currently only `["US"]` is supported** |

```bash
curl -X POST "https://api.trohub.com/v1/infringement/image-search" \
  -H "X-API-Key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"taskID":"trademark-demo-uuid","images":[{"imageID":"img-tm-001","image":"https://example.com/images/logo.png","searchScope":{"trademarkEnabled":true,"trademark":{"autoSegment":false,"countries":["US"]}}}]}'
```

```python
import requests
url = "https://api.trohub.com/v1/infringement/image-search"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {
    "taskID": "trademark-demo-uuid",
    "images": [{
        "imageID": "img-tm-001",
        "image": "https://example.com/images/logo.png",
        "searchScope": { "trademarkEnabled": True, "trademark": {"autoSegment": False, "countries": ["US"]} }
    }]
}
print(requests.post(url, headers=headers, json=payload).json())
```

**Response:**
```json
{ "success": true, "message": "Element search tasks submitted successfully", "data": { "taskIDs": ["h0d0a0b3-f09c-4824-a745-0d29759c253h"] } }
```
Then poll `GET /infringement/status/:taskID` — see `references/infringement-tasks.md` for `searchResults.trademark[]` field details (`markText`, `similarity`, `score`, `reason`, `status` LIVE/DEAD, `legalStatus`, etc) and the `queryAssessment` (known-IP) fields, which **are** returned for trademark checks.
