import sys,glob,json,os,wave
import numpy as np
from faster_whisper import WhisperModel
S=sys.argv[1]; size=sys.argv[2]
m=WhisperModel(size,device="cpu",compute_type="int8",cpu_threads=4)
only=sys.argv[3:]
fs=[S+"/aud/"+n+".wav" for n in only] if only else sorted(glob.glob(S+"/aud/*.wav"),key=os.path.getsize)
for f in fs:
    n=os.path.basename(f)[:-4]; out=f"{S}/tr/{n}.{size}.json"
    if os.path.exists(out): continue
    w=wave.open(f); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768.0
    segs,info=m.transcribe(a,language="ms",word_timestamps=True,vad_filter=True,beam_size=5,condition_on_previous_text=False)
    r=[{"s":round(s.start,2),"e":round(s.end,2),"t":s.text.strip(),"lp":round(s.avg_logprob,2),"w":[(round(w.start,2),round(w.end,2),w.word) for w in s.words]} for s in segs]
    json.dump({"dur":info.duration,"segs":r},open(out,"w"),ensure_ascii=False)
    print(n,len(r),flush=True)
