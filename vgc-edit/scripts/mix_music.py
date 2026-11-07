#!/usr/bin/env python3
"""Mix the generated underscore under the existing voice track (auto-ducking) and re-mux onto finished videos.
Video streams are copied (no re-render). Never overwrites: outputs get the next free version number.
Usage: python3 -I scripts/mix_music.py out/preview_v06.mp4 [out/preview_916_v02.mp4 ...]
"""
import glob, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = f"{ROOT}/build/audio_mix.m4a"                    # verified dialogue + VO mix (-16 LUFS)
MUSIC = sorted(glob.glob(f"{ROOT}/source/music_sad_v*.wav"))[-1]
BED_GAIN_DB = -8.5      # music is ~-12.4 LUFS as generated -> ~-23 LUFS bed when nothing else plays
END_BOOST_DB = 4.0       # a little more music on the silent logo end card
END_T = 114.7            # outro VO ends here (output timeline)


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-1200:]); sys.exit(1)
    return r


def lufs(path, ss=None, to=None, af=""):
    a = (["-ss", str(ss)] if ss is not None else []) + (["-to", str(to)] if to is not None else [])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *a, "-i", path, "-af", af + "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    return float(I[-1]) if I else float("-inf")


DUCK = "sidechaincompress=threshold=0.03:ratio=3.5:attack=40:release=700:makeup=1"
bed = f"[1:a]volume={BED_GAIN_DB}dB,volume=enable='gte(t,{END_T})':volume={END_BOOST_DB}dB[m0]"
fc_mix = f"{bed};[m0][0:a]{DUCK}[md];[0:a][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89:level=disabled[aout]"
fc_stem = f"{bed};[m0][0:a]{DUCK}[aout]"

mix = f"{ROOT}/build/audio_mix_music.m4a"; stem = f"{ROOT}/build/music_stem_ducked.wav"
sh(["ffmpeg", "-y", "-v", "error", "-i", VOICE, "-i", MUSIC, "-filter_complex", fc_mix, "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", mix])
sh(["ffmpeg", "-y", "-v", "error", "-i", VOICE, "-i", MUSIC, "-filter_complex", fc_stem, "-map", "[aout]", "-t", "119.73", stem])

print(f"music file: {os.path.basename(MUSIC)}")
print("level check (LUFS integrated)   voice | music-under-voice | final mix")
for name, a, b in (("hook VO     ", 0.2, 21.9), ("speaker     ", 22, 79.7), ("outro VO    ", 80, 114.7), ("end card    ", 114.8, 119.7)):
    print(f"  {name} {lufs(VOICE, a, b):7.1f} | {lufs(stem, a, b):8.1f}           | {lufs(mix, a, b):7.1f}")
print(f"  whole        {lufs(VOICE):7.1f} | {lufs(stem):8.1f}           | {lufs(mix):7.1f}")

for vid in sys.argv[1:]:
    base = re.sub(r"_v\d+(_720p)?\.mp4$", "", os.path.basename(vid))
    n = 1
    while os.path.exists(f"{ROOT}/out/{base}_v{n:02d}.mp4"): n += 1
    out = f"{ROOT}/out/{base}_v{n:02d}.mp4"
    sh(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
        "-movflags", "+faststart", "-shortest", out])
    print("WROTE", out)
