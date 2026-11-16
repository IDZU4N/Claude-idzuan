import subprocess, glob, os, json, re, sys

S = sys.argv[1]
out = {}
files = sorted(glob.glob(S + "/src/*.mov") + glob.glob(S + "/src/*.MOV"))
for f in files:
    n = os.path.basename(f).split(".")[0]
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", f, "-vf",
         "fps=1/4,scale=320:-2,signalstats,metadata=print:file=-", "-an", "-f", "null", "-"],
        capture_output=True, text=True)
    v = {k: [] for k in ("YAVG", "YLOW", "YHIGH", "UAVG", "VAVG", "SATAVG")}
    for line in r.stdout.splitlines():
        m = re.match(r"lavfi.signalstats.(\w+)=([\d.]+)", line)
        if m and m.group(1) in v:
            v[m.group(1)].append(float(m.group(2)))
    out[n] = {k: round(sum(x) / len(x), 1) for k, x in v.items() if x}
    print(n, out[n], flush=True)
json.dump(out, open(S + "/stats.json", "w"), indent=1)
