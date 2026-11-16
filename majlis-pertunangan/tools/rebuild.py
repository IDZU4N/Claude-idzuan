import sys, os
sys.path.insert(0, "/tmp/claude-0/-home-user-Claude-idzuan/40cc26e7-f05a-5110-a3e3-f8b3e013b2fd/scratchpad/tools")
import timeline, vrender
from engine import *
sc = timeline.build(); total = layout(sc)
shots = [s for x in sc for s in x.shots]
frames, lines = vrender.build_video(shots, f"{S}/out/concat.txt", tag="main")
print("bingkai", frames, "jangkaan", total * FPS)
