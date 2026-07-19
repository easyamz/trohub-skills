# Error Codes

All endpoints return errors as:
```json
{ "ok": false, "message": "...", "responseType": "v2", "error": { "code": "...", "details": "..." } }
```
(Task-submit endpoints may use the `success: false` envelope instead — see `references/infringement-tasks.md`.)

| Error code | Meaning | What to do |
|---|---|---|
| `UNAUTHORIZED_AUTH_REQUIRED` | Auth failed | Check the `X-API-Key` header is present and correct |
| `BUSINESS_RATE_LIMIT_EXCEEDED` | Too many requests | Stay within 60 requests/minute; add backoff/retry |
| `BUSINESS_QUOTA_EXCEEDED` | Account balance/quota used up | User needs to top up their quota in their TROHUB account |
| `VALIDATION_BAD_REQUEST` | Invalid JSON body | Check field names and nesting match the docs exactly |
| `VALIDATION_PATENT_NUMBER_INVALID` | Bad patent number format | Must be `D` or `USD` followed by 6–7 digits |
| `VALIDATION_PATENT_NUMBERS_EXCEEDED` | Too many patent numbers in one call | Max 50 per request |
| `VALIDATION_PATENT_IMAGE_REQUIRED` | Missing image | Confirm `image` field is populated (URL or base64) |
| `VALIDATION_PATENT_IMAGE_FORMAT_INVALID` | Bad/unsupported image | Only JPG/PNG/WEBP are supported |
| `INTERNAL_PATENT_ELASTICSEARCH_ERROR` | Backend/server error | Transient — retry later, or tell the user to contact TROHUB support if persistent |

## Practical error-handling pattern

```python
resp = requests.post(url, headers=headers, json=payload)
data = resp.json()

if not (data.get("ok") or data.get("success")):
    err = data.get("error", {})
    code = err.get("code", "UNKNOWN")
    if code == "BUSINESS_RATE_LIMIT_EXCEEDED":
        # back off and retry
        ...
    elif code == "BUSINESS_QUOTA_EXCEEDED":
        # stop and tell the user to top up
        ...
    else:
        raise RuntimeError(f"TROHUB API error {code}: {err.get('details')}")
```

Also inspect the rate-limit response headers on every call so you can self-throttle proactively rather than waiting to hit `BUSINESS_RATE_LIMIT_EXCEEDED`:

| Header | Meaning |
|---|---|
| `X-RateLimit-Limit` | Max requests allowed per minute (`60`) |
| `X-RateLimit-Remaining` | Requests left in the current window |
| `X-RateLimit-Reset` | Unix timestamp (seconds) when the window resets |
