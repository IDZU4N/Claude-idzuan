import sys, json, wave
import numpy as np
from faster_whisper import WhisperModel
w = wave.open(sys.argv[1]); a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, info = m.transcribe(a, language="ms", vad_filter=True, beam_size=5)
out = [dict(s=round(s.start,2), e=round(s.end,2), t=s.text.strip()) for s in segs]
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(info.language, info.duration, len(out))
