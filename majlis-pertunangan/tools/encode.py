import sys, os
sys.path.insert(0, "/tmp/claude-0/-home-user-Claude-idzuan/40cc26e7-f05a-5110-a3e3-f8b3e013b2fd/scratchpad/tools")
import timeline, vrender
from engine import *
OUT = f"{S}/out"
sc = timeline.build(); total = layout(sc)
emc = [x for x in sc if x.name == "aluan_1"][0]
fin = [x for x in sc if x.name == "penutup"][0]
ov = [(f"{OUT}/t_title.png", 2.0, 9.5, 1.2, 1.2),
      (f"{OUT}/t_emcee.png", emc.t0 + 2.5, emc.t0 + 9.0, 0.8, 0.8),
      (f"{OUT}/t_end.png", fin.t0 + 1.5, total - 1.0, 1.0, 1.0)]
vrender.encode_final(f"{OUT}/concat.txt", f"{OUT}/audio_mix.wav", f"{OUT}/majlis_pertunangan_1080p.mp4", overlays=ov, total_s=total, crf=18)
print("siap")
