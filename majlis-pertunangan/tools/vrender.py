"""Pemaparan video: bidikan -> mezanin intra -> bahagian solo + campuran dissolve -> MP4 akhir."""
import os, sys, math, json, hashlib, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import cine, photos
from engine import sh, S, MEZ, W, H, FPS, FPSN, FPSD

X264_MEZ = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "13", "-g", "1", "-pix_fmt", "yuv420p"]


def src_path(name):
    for ext in ("mov", "MOV"):
        p = f"{S}/src/{name}.{ext}"
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)


def key(shot, n):
    d = json.dumps([shot.kind, shot.src, round(shot.ss, 3), n, shot.stab, sorted(shot.kw.items(), key=str)], default=str)
    return hashlib.md5(d.encode()).hexdigest()[:12]


def render_shot(shot, n):
    out = f"{MEZ}/{shot.src}_{key(shot, n)}.mp4"
    if os.path.exists(out):
        return out
    dur = n / FPS
    if shot.kind == "photo":
        photos.render_photo(shot.src, out, dur, **shot.kw)
        return out
    grade = cine.grade_filter(shot.src)
    push = shot.kw.get("push")  # (z1, cx, cy) zum digital perlahan
    vf = []
    pre = []
    if shot.stab:
        trf = f"{MEZ}/{shot.src}_{key(shot, n)}.trf"
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{shot.ss:.3f}", "-i", src_path(shot.src), "-t", f"{dur+0.5:.3f}",
            "-vf", "vidstabdetect=shakiness=5:accuracy=9:result=" + trf, "-f", "null", "-"])
        vf.append(f"vidstabtransform=input={trf}:smoothing=14:zoom=3:optzoom=0:interpol=bicubic")
    vf.append(grade)
    vf.append(f"scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=increase,crop={W}:{H}")
    if push:
        z1, cx, cy = push
        vf.append(f"scale=w='trunc({W}*(1+{z1-1:.4f}*t/{dur:.3f})/2)*2':h='trunc({H}*(1+{z1-1:.4f}*t/{dur:.3f})/2)*2':eval=frame:flags=bicubic,"
                  f"crop={W}:{H}:x='(iw-{W})*{cx}':y='(ih-{H})*{cy}'")
    vf.append("setsar=1")
    vf.append(f"fps={FPSN}/{FPSD}")
    vf.append("tpad=stop_mode=clone:stop_duration=2")
    sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{shot.ss:.3f}", "-i", src_path(shot.src), "-an",
        "-vf", ",".join(vf), "-frames:v", str(n), *X264_MEZ, "-r", f"{FPSN}/{FPSD}", out])
    return out


def frame_ranges(shots):
    """Julat bingkai global untuk setiap bidikan, tiada hanyutan (pembundaran pada tahap global)."""
    ranges = []
    for s in shots:
        a = int(round(s.start * FPS))
        b = int(round((s.start + s.dur) * FPS))
        ranges.append([a, b])
    return ranges


def build_video(shots, out_concat, tag="main"):
    rng = frame_ranges(shots)
    for i, s in enumerate(shots):
        s._n = rng[i][1] - rng[i][0]
    # pertindihan (dissolve) dalam bingkai
    ov = [0] * len(shots)
    for i in range(1, len(shots)):
        ov[i] = max(0, rng[i - 1][1] - rng[i][0])
    atoms = []
    files = {}
    for i, s in enumerate(shots):
        files[i] = render_shot(s, s._n)
        print("render", i, s.src, s._n, flush=True)
    fd = 1001 / 30000
    lines = []
    total_frames = 0
    for i, s in enumerate(shots):
        lo = ov[i]
        hi = s._n - (ov[i + 1] if i + 1 < len(shots) else 0)
        if hi > lo:
            lines.append((files[i], lo, hi))
            total_frames += hi - lo
        if i + 1 < len(shots) and ov[i + 1] > 0:
            k = ov[i + 1]
            bl = f"{MEZ}/blend_{tag}_{i}_{k}.mp4"
            if not os.path.exists(bl):
                sh(["ffmpeg", "-v", "error", "-y", "-i", files[i], "-i", files[i + 1], "-filter_complex",
                    f"[0:v]trim=start_frame={s._n-k}:end_frame={s._n},setpts=PTS-STARTPTS[a];"
                    f"[1:v]trim=start_frame=0:end_frame={k},setpts=PTS-STARTPTS[b];"
                    f"[a][b]blend=all_expr='A*(1-pow((N+1)/{k+1},2)*(3-2*(N+1)/{k+1}))+B*pow((N+1)/{k+1},2)*(3-2*(N+1)/{k+1})',"
                    f"setsar=1,fps={FPSN}/{FPSD},tpad=stop_mode=clone:stop=3", "-an", "-frames:v", str(k), *X264_MEZ, "-r", f"{FPSN}/{FPSD}", bl])
            lines.append((bl, 0, k))
            total_frames += k
    final = []
    for j, (p, lo, hi) in enumerate(lines):
        nfile = int(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames",
                        "-of", "csv=p=0", p]).stdout.strip())
        if lo == 0 and hi == nfile:
            final.append(p)
            continue
        at = f"{MEZ}/atom_{tag}_{j}_{lo}_{hi}.mp4"
        if not os.path.exists(at):
            sh(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf",
                f"trim=start_frame={lo}:end_frame={hi},setpts=PTS-STARTPTS,fps={FPSN}/{FPSD}",
                "-an", "-frames:v", str(hi - lo), *X264_MEZ, "-r", f"{FPSN}/{FPSD}", at])
        final.append(at)
    with open(out_concat, "w") as f:
        f.write("ffconcat version 1.0\n")
        for p in final:
            f.write(f"file '{p}'\n")
    return total_frames, lines


def encode_final(concat, wav, out, overlays=(), total_s=None, crf=17):
    inputs = ["-f", "concat", "-safe", "0", "-i", concat, "-i", wav]
    fc = []
    last = "[0:v]"
    idx = 2
    for k, ov in enumerate(overlays):
        png, t0, t1, fin, fout = ov
        d = t1 - t0
        inputs += ["-loop", "1", "-framerate", f"{FPSN}/{FPSD}", "-t", f"{d:.3f}", "-i", png]
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st=0:d={fin}:alpha=1,fade=t=out:st={d-fout:.3f}:d={fout}:alpha=1,"
                  f"setpts=PTS+{t0}/TB[o{k}]")
        fc.append(f"{last}[o{k}]overlay=eof_action=pass:repeatlast=0[v{k}]")
        last = f"[v{k}]"
        idx += 1
    args = ["ffmpeg", "-v", "error", "-y", *inputs]
    if fc:
        args += ["-filter_complex", ";".join(fc), "-map", last]
    else:
        args += ["-map", "0:v"]
    args += ["-map", "1:a", "-fps_mode", "passthrough", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-maxrate", "18M", "-bufsize", "36M",
             "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
             "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
             "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart"]
    if total_s:
        args += ["-t", f"{total_s:.3f}"]
    args += [out]
    sh(args)
    return out
