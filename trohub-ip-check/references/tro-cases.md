# TRO Case Monitoring

TRO = Temporary Restraining Order. These are the emergency lawsuits many US brand owners file against "the individuals, partnerships, and unincorporated associations" selling counterfeit/infringing goods online — the thing cross-border sellers most want early warning about.

Both endpoints below are **synchronous** — no task/polling involved.

---

## 1. Recent TRO cases — `POST /tro/recent`

Get a list of recently filed TRO cases (up to the last 7 days).

**Request body**

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `days` | number | no | `7` | How many days back to look, range 1–7 |
| `limit` | number | no | `50` | Max results to return, range 1–100 |

```json
{ "days": 7, "limit": 50 }
```

**curl**
```bash
curl -X POST "https://api.trohub.com/v1/tro/recent" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"days":7,"limit":50}'
```

**Python**
```python
import requests

url = "https://api.trohub.com/v1/tro/recent"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {"days": 7, "limit": 50}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

**Response** — `data` is an array of case summaries:
```json
{
  "ok": true,
  "message": "success",
  "responseType": "v2",
  "data": [
    {
      "title": "Brandowner LLC et al v. The Individuals et al",
      "caseDate": "2026-07-10",
      "caseNumber": "1:26-cv-00245",
      "docketID": "fdb41b2e-8e56-4eb8-96ef-042d919c5e01",
      "plaintiff": "Brandowner LLC",
      "court": "N.D. Ill."
    }
  ]
}
```

Save `docketID` — you need it for the entries lookup below.

---

## 2. Case entries — `POST /tro/entries`

Get all filed documents ("entries") for one specific case, including complaint PDFs, and any copyright/trademark/patent evidence images attached to the filing.

**Request body**

| Param | Type | Required | Notes |
|---|---|---|---|
| `docketID` | string | yes | Comes from the `docketID` field returned by `/tro/recent` |

```json
{ "docketID": "fdb41b2e-8e56-4eb8-96ef-042d919c5e01" }
```

**curl**
```bash
curl -X POST "https://api.trohub.com/v1/tro/entries" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"docketID":"fdb41b2e-8e56-4eb8-96ef-042d919c5e01"}'
```

**Python**
```python
import requests

url = "https://api.trohub.com/v1/tro/entries"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {"docketID": "fdb41b2e-8e56-4eb8-96ef-042d919c5e01"}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

**Response** — `data` is an array of entries. Each entry can carry three kinds of attachments:

```json
{
  "ok": true,
  "message": "success",
  "responseType": "v2",
  "data": [
    {
      "entryID": "entry-001",
      "title": "COMPLAINT",
      "entryDate": "2026-07-01",
      "docNumber": 1,
      "fileSize": 1024000,
      "attachments": [
        { "id": 1, "title": "Complaint.pdf", "attachmentNumber": 1, "fileSize": 1024000, "downloadable": true, "restricted": false }
      ],
      "copyrightImages": [
        { "id": "img-001", "imageUrl": "https://images.trohub.com/xxx.jpg", "imageKey": "ilnd/xxx.jpg", "displaySort": 0, "public": true }
      ],
      "trademarkPatentImages": [
        { "id": "tm-img-001", "imageUrl": "https://patent-trademark-images.trohub.com/xxx.jpg", "imageKey": "tm/xxx.jpg", "displaySort": 0, "public": true }
      ]
    }
  ]
}
```

- `attachments[]` — the actual filed documents (complaint, exhibits, orders). `downloadable`/`restricted` tell you if the PDF can actually be fetched.
- `copyrightImages[]` — copyright evidence images attached to the case (e.g. the artwork the plaintiff claims was copied).
- `trademarkPatentImages[]` — trademark/patent evidence images attached to the case.

**Common use case:** after finding a case in `/tro/recent` that matches a brand/product category the seller cares about, pull `/tro/entries` and show the seller the plaintiff's actual evidence images, so they can visually compare against their own product.
