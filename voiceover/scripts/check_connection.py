"""Non-generating ElevenLabs connection check. Uses NO credits.
Calls: GET /v1/user/subscription (quota) and GET /v2/voices (voices you can use).
The API key is read from the ELEVENLABS_API_KEY environment variable and is never printed.
(In this cloud session the network proxy injects the real key; a placeholder is used locally.)
"""
import os, sys, requests

BASE = "https://api.elevenlabs.io"
key = os.environ.get("ELEVENLABS_API_KEY", "proxy-managed-placeholder")
H = {"xi-api-key": key}

def get(path, **params):
    r = requests.get(BASE + path, headers=H, params=params, timeout=30)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})

code, sub = get("/v1/user/subscription")
if code != 200:
    print(f"Subscription check failed: HTTP {code} -> {str(sub)[:300]}")
else:
    print(f"Plan tier: {sub.get('tier')}")
    print(f"Credits used: {sub.get('character_count')} / {sub.get('character_limit')}")
    print(f"Overage billing allowed: {sub.get('max_credit_limit_extension') not in (0, None)}")

code, v = get("/v2/voices", page_size=100)
if code != 200:
    print(f"Voices check failed: HTTP {code} -> {str(v)[:300]}")
else:
    voices = v.get("voices", [])
    print(f"Voices available to this key: {len(voices)}")
    for x in voices[:100]:
        lab = x.get("labels") or {}
        print(f" - {x.get('name')} | {x.get('category')} | {lab.get('language','?')} | {lab.get('descriptive') or lab.get('use_case','')} | id={x.get('voice_id')}")
sys.exit(0 if code == 200 else 1)
