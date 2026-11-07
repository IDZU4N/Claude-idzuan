#!/bin/bash
# Shrink preview to ~10 MB at the SAME 1080x1920 resolution. 2-pass; audio 56k AAC; video 135k.
set -e
cd "$(dirname "$0")/.."
IN=${1:-out/preview_v03.mp4}; V=135k; A=56k
# H.264 (most compatible)
ffmpeg -v error -y -i "$IN" -an -c:v libx264 -preset slow -b:v $V -pass 1 -passlogfile build/x264 -pix_fmt yuv420p -f null /dev/null
ffmpeg -v error -y -i "$IN" -c:v libx264 -preset slow -b:v $V -pass 2 -passlogfile build/x264 -pix_fmt yuv420p -c:a aac -b:a $A -movflags +faststart out/final_10mb_h264.mp4
# HEVC (sharper at this bitrate; needs a recent phone/player)
ffmpeg -v error -y -i "$IN" -an -c:v libx265 -preset medium -b:v $V -x265-params "pass=1:log-level=error:stats=build/x265.log" -pix_fmt yuv420p -f null /dev/null
ffmpeg -v error -y -i "$IN" -c:v libx265 -preset medium -b:v $V -x265-params "pass=2:log-level=error:stats=build/x265.log" -pix_fmt yuv420p -tag:v hvc1 -c:a aac -b:a $A -movflags +faststart out/final_10mb_hevc.mp4
echo done
