import sys,json,glob,os
S=sys.argv[1]; sz=os.environ.get("SZ","small")
for n in sys.argv[2:]:
    p=f"{S}/tr/{n}.{sz}.json"
    if not os.path.exists(p): print(n,"(belum)"); continue
    d=json.load(open(p)); print(f"== {n} dur={d['dur']:.1f}s segs={len(d['segs'])}")
    for s in d["segs"]: print(f"  [{s['s']:.1f}-{s['e']:.1f}] {s['t']}")
