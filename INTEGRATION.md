# Facebook Profile Scraper — External Integration Guide

This document is intended for AI agents and external applications that want to integrate with the Facebook Profile Scraper API. Read it fully before making any API calls.

---

## Overview

This system accepts a Facebook profile URL, scrapes publicly visible profile data using a real browser (Selenium + Chrome), and returns structured results including the person's location.

**Key facts:**
- Scraping is **asynchronous** — you submit a URL and poll for results
- A single scrape takes **1 to 3 minutes** on average
- Only **one scrape runs at a time** (single Celery worker)
- If a profile was already scraped and finished, results are returned **instantly** without re-scraping
- The system is accessible at `http://100.64.132.90:9000`

---

## Base URL

```
http://100.64.132.90:9000
```

All external integration endpoints are prefixed with `/api/external`.

---

## Status Lifecycle

A profile moves through these statuses in order:

```
queued → processing → finished
                   ↘ failed
```

| Status | Meaning |
|--------|---------|
| `queued` | URL submitted, waiting for the scraper to start |
| `processing` | Scraper is actively running Chrome and collecting data |
| `finished` | Scrape completed successfully, location data is available |
| `failed` | Scrape failed (login issue, private profile, network error, etc.) |

When a profile is `failed`, you can re-submit the same URL and it will be re-queued automatically.

---

## Endpoint 1 — Submit a Profile URL

### `POST /api/external/scrape`

Submit a Facebook profile URL to be scraped.

**Request:**
```http
POST http://100.64.132.90:9000/api/external/scrape
Content-Type: application/json

{
  "url": "https://www.facebook.com/ankela.skenderi.3"
}
```

The `url` field must be a valid Facebook profile URL. Accepted formats:
- `https://www.facebook.com/username`
- `https://facebook.com/username`
- `https://www.facebook.com/profile.php?id=123456789`
- Bare username: `ankela.skenderi.3` (will be auto-prefixed)

**Behavior:**

| Situation | What happens |
|-----------|-------------|
| New URL never seen before | Creates profile, queues scrape, returns `"queued"` |
| URL already queued or processing | Returns current status, does NOT queue again |
| URL already finished | Returns `"finished"` + location data immediately (no re-scrape) |
| URL previously failed | Re-queues the scrape, returns `"queued"` |

---

### Response — Status: `queued` or `processing`

```json
{
  "profile_id": "69b2d1fb92c11cd38fd34a66",
  "url": "https://www.facebook.com/ankela.skenderi.3",
  "status": "queued",
  "name": null,
  "location": null,
  "error": null
}
```

Use the `profile_id` to poll for results.

---

### Response — Status: `finished`

```json
{
  "profile_id": "69b2d1fb92c11cd38fd34a66",
  "url": "https://www.facebook.com/ankela.skenderi.3",
  "status": "finished",
  "name": "Ankela Skenderi",
  "location": {
    "current_city": {
      "upazila": null,
      "district": "Sliema",
      "division": null,
      "country": "Malta"
    },
    "hometown": null,
    "raw": "Lives in Sliema, Malta"
  },
  "error": null
}
```

---

### Response — Status: `failed`

```json
{
  "profile_id": "69b2d1fb92c11cd38fd34a66",
  "url": "https://www.facebook.com/ankela.skenderi.3",
  "status": "failed",
  "name": null,
  "location": null,
  "error": "Scraper failed (exit 2): Login failed"
}
```

---

## Endpoint 2 — Get Result by Profile ID

### `GET /api/external/result/{profile_id}`

Poll this endpoint with the `profile_id` returned from the scrape endpoint.

**Request:**
```http
GET http://100.64.132.90:9000/api/external/result/69b2d1fb92c11cd38fd34a66
```

No request body. No query parameters.

**Response:** Same shape as the scrape endpoint responses above, depending on current status.

**404 response** (if profile_id doesn't exist):
```json
{
  "detail": "Profile not found"
}
```

---

## Polling Strategy

Since scraping is async, your app must poll until the status is terminal (`finished` or `failed`).

**Recommended polling logic:**

```
1. POST /api/external/scrape  → get profile_id
2. Wait 15 seconds
3. GET /api/external/result/{profile_id}
4. If status == "queued" or "processing" → wait 10 seconds, repeat step 3
5. If status == "finished" → read location, done
6. If status == "failed" → handle error (optionally retry by re-submitting the URL)
```

**Recommended poll interval:** 10 seconds
**Recommended timeout:** 5 minutes (30 polls × 10 seconds)
**If timeout reached:** The profile may still be processing. Check again later or re-submit.

---

## The Location Object

The `location` field is the primary data this system returns. It is `null` when status is not `finished`.

```json
{
  "current_city": {
    "upazila": null,
    "district": "Sliema",
    "division": null,
    "country": "Malta"
  },
  "hometown": {
    "upazila": "Purbadhala",
    "district": "Netrokona",
    "division": "Mymensingh",
    "country": "Bangladesh"
  },
  "raw": "Lives in Sliema, Malta"
}
```

### Field explanations

| Field | Description |
|-------|-------------|
| `current_city` | Where the person currently lives (parsed from "Lives in ...") |
| `hometown` | Where they are originally from (parsed from "From ...") |
| `raw` | The original unmodified text string from the profile intro |

### Location sub-fields

| Field | Description | Example |
|-------|-------------|---------|
| `country` | Country name | `"Malta"`, `"Bangladesh"`, `"United States"` |
| `district` | City, district, or municipality | `"Sliema"`, `"Dhaka"` |
| `division` | State, region, or division (if available) | `"Mymensingh"`, `"California"` |
| `upazila` | Sub-district or neighborhood (if available) | `"Purbadhala"` |

**All four fields can be `null`** if Facebook did not provide enough location detail or the profile has restricted location visibility.

**When `location` itself is `null`:**
- Status is `queued` or `processing` (not done yet)
- Status is `failed`
- Status is `finished` but the profile has no location data visible (private or not set)

---

## Complete Code Examples

### JavaScript / fetch

```javascript
const BASE = "http://100.64.132.90:9000";

async function scrapeAndGetLocation(facebookUrl) {
  // Step 1: Submit
  const submitRes = await fetch(`${BASE}/api/external/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: facebookUrl }),
  });
  const submitted = await submitRes.json();

  if (submitted.status === "finished") {
    return submitted.location; // Already done
  }

  const profileId = submitted.profile_id;

  // Step 2: Poll
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 10000)); // wait 10s

    const pollRes = await fetch(`${BASE}/api/external/result/${profileId}`);
    const result = await pollRes.json();

    if (result.status === "finished") {
      return result.location;
    }
    if (result.status === "failed") {
      throw new Error(`Scrape failed: ${result.error}`);
    }
  }

  throw new Error("Timeout: scrape did not finish within 5 minutes");
}

// Usage
scrapeAndGetLocation("https://www.facebook.com/ankela.skenderi.3")
  .then((location) => console.log("Location:", location))
  .catch(console.error);
```

### Python / requests

```python
import requests
import time

BASE = "http://100.64.132.90:9000"

def scrape_and_get_location(facebook_url: str) -> dict | None:
    # Step 1: Submit
    res = requests.post(f"{BASE}/api/external/scrape", json={"url": facebook_url})
    res.raise_for_status()
    submitted = res.json()

    if submitted["status"] == "finished":
        return submitted["location"]

    profile_id = submitted["profile_id"]

    # Step 2: Poll
    for _ in range(30):
        time.sleep(10)
        poll = requests.get(f"{BASE}/api/external/result/{profile_id}")
        poll.raise_for_status()
        result = poll.json()

        if result["status"] == "finished":
            return result["location"]
        if result["status"] == "failed":
            raise Exception(f"Scrape failed: {result['error']}")

    raise TimeoutError("Scrape did not finish within 5 minutes")

# Usage
location = scrape_and_get_location("https://www.facebook.com/ankela.skenderi.3")
print(location)
# {
#   "current_city": {"upazila": null, "district": "Sliema", "division": null, "country": "Malta"},
#   "hometown": null,
#   "raw": "Lives in Sliema, Malta"
# }
```

### curl

```bash
# Submit
curl -s -X POST http://100.64.132.90:9000/api/external/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.facebook.com/ankela.skenderi.3"}'

# Poll (replace PROFILE_ID with the id from above)
curl -s http://100.64.132.90:9000/api/external/result/PROFILE_ID
```

---

## Error Handling Reference

| HTTP Status | Meaning | What to do |
|-------------|---------|------------|
| `200` | Success | Read `status` field |
| `404` | `profile_id` not found | Check the ID is correct |
| `422` | Invalid request body | Check that `url` field is present and is a string |
| `500` | Server error | Retry after a delay |

| `status` value | Meaning | What to do |
|----------------|---------|------------|
| `queued` | Waiting to start | Keep polling |
| `processing` | Scraping in progress | Keep polling |
| `finished` | Done | Read `location` |
| `failed` | Error occurred | Read `error` field; re-submit URL to retry |

---

## Rate & Concurrency Notes

- The scraper runs **one job at a time**. If multiple URLs are submitted simultaneously, they will be queued and processed in order.
- There is no authentication required on the external API endpoints.
- Submitting the same URL multiple times while it is `queued` or `processing` is safe — it will not create duplicate jobs.
- Submitting the same URL after it is `finished` is safe — it returns the cached result instantly without re-scraping.
- To force a re-scrape of a finished profile, it must first be deleted from the system (not available via the external API).

---

## Health Check

To verify the API is reachable:

```http
GET http://100.64.132.90:9000/health
```

Response:
```json
{"status": "ok"}
```

---

## Interactive API Docs

FastAPI provides auto-generated interactive docs at:

```
http://100.64.132.90:9000/docs
```

You can test all endpoints directly from the browser there.

---

## Summary for AI Agents

If you are an AI agent integrating with this API, here is a concise decision tree:

1. **User wants location of a Facebook profile?**
   - Call `POST /api/external/scrape` with `{"url": "<facebook_url>"}`
   - Save the returned `profile_id`

2. **Result came back with `status: "finished"`?**
   - Use `location.current_city` and/or `location.hometown` directly
   - Display `location.raw` as human-readable text

3. **Result came back with `status: "queued"` or `"processing"`?**
   - Wait 10 seconds, call `GET /api/external/result/{profile_id}`
   - Repeat until `finished` or `failed`
   - Inform the user that scraping is in progress

4. **Result came back with `status: "failed"`?**
   - Inform the user that scraping failed
   - Optionally re-submit the URL (same `POST /api/external/scrape` call)
   - The profile might be private, deleted, or the login may have been blocked

5. **`location` is `null` even though `status` is `"finished"`?**
   - The profile exists and was scraped, but has no visible location
   - The person has not set a location on their Facebook profile, or it is private
