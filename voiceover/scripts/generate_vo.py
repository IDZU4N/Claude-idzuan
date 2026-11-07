"""Generate ONE voice-over file with ElevenLabs text-to-speech (uses credits).

Safety rules built in:
  * Does nothing unless --confirm is passed (dry run otherwise: shows text, voice, model, chars).
  * Never overwrites: output is output/<prefix>_vNN.mp3 with the next free number.
  * NO automatic retries. On timeout/unclear result it stops and tells you to check
    your ElevenLabs history/credits first, to avoid paying twice.
  * The API key is read from ELEVENLABS_API_KEY and never printed. (In the cloud session the
    network proxy injects the real key; use ELEVENLABS_API_KEY=proxy-injected as a placeholder.)

Example (dry run, free):
  ELEVENLABS_API_KEY=proxy-injected python3 -I scripts/generate_vo.py \
      --text-file script/preview_excerpt_v1.txt --prefix preview
Example (real generation, uses credits):
  ... same command plus --confirm
"""
import argparse, os, re, subprocess, sys, json
import requests

BASE = "https://api.elevenlabs.io"
DEFAULT_VOICE_ID = "T2pTFYGMhHg1r1W2eqA1"        # IDZUAN MORNING VOICE (your own cloned voice)
DEFAULT_MODEL = "eleven_multilingual_v2"          # supports Malay (ms); 10,000 char limit
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


def next_path(prefix):
    os.makedirs(OUT_DIR, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(OUT_DIR, f"{prefix}_v{n:02d}.mp3")):
        n += 1
    return os.path.join(OUT_DIR, f"{prefix}_v{n:02d}.mp3")


def credits(headers):
    r = requests.get(BASE + "/v1/user/subscription", headers=headers, timeout=30)
    if r.ok:
        j = r.json()
        return j.get("character_count"), j.get("character_limit")
    return None, None


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name",
                          "-of", "json", path], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--prefix", required=True, help="output name prefix, e.g. preview or vo_intro")
    ap.add_argument("--voice-id", default=DEFAULT_VOICE_ID)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--output-format", default="mp3_44100_128")
    ap.add_argument("--confirm", action="store_true", help="actually send the text and spend credits")
    a = ap.parse_args()

    text = open(a.text_file, encoding="utf-8").read().strip()
    chars = len(text)
    print(f"Text file : {a.text_file}\nCharacters: {chars}\nVoice ID  : {a.voice_id}\nModel     : {a.model}\nFormat    : {a.output_format}")
    print("---- exact text that will be sent ----\n" + text + "\n--------------------------------------")
    if not a.confirm:
        print("DRY RUN: nothing was sent and no credits were used. Add --confirm to generate.")
        return 0

    headers = {"xi-api-key": os.environ.get("ELEVENLABS_API_KEY", "proxy-injected"), "Content-Type": "application/json"}
    before = credits(headers)
    out = next_path(a.prefix)
    body = {"text": text, "model_id": a.model}          # voice's own saved settings are used
    try:
        r = requests.post(f"{BASE}/v1/text-to-speech/{a.voice_id}", headers=headers,
                          params={"output_format": a.output_format}, json=body, timeout=180)
    except requests.RequestException as e:
        print(f"UNCLEAR RESULT ({type(e).__name__}). DO NOT retry yet: check your ElevenLabs history and credits first.")
        return 2
    if r.status_code != 200:
        print(f"FAILED: HTTP {r.status_code} -> {r.text[:300]}")
        return 1
    with open(out, "wb") as f:
        f.write(r.content)
    after = credits(headers)
    info = probe(out)
    size = os.path.getsize(out)
    print(f"Saved: {out} ({size} bytes)")
    if info:
        print(f"Decodes OK | codec={info['streams'][0]['codec_name']} | duration={float(info['format']['duration']):.2f}s")
    else:
        print("WARNING: ffprobe could not decode the file")
    if before[0] is not None and after[0] is not None:
        print(f"Credits used (measured): {after[0]-before[0]}  | now {after[0]}/{after[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
