#!/usr/bin/env bash
# ElCaciqueDeck - download and organize a backup stored on Arweave
#
#   bash ~/elcaciquedeck/tools/arweave-backup.sh <links-file> [destination]
#
# <links-file>  a list of https://arweave.net/... links, either a JSON list
#               ["https://...","https://..."] or one link per line
# [destination] where to save (default: Library drive -> Backups/arweave-<date>)
#
# What it does:
#   - downloads every link (4 at a time), retrying a few times if one fails
#   - figures out what each file is (image, video, document...) and sorts it
#     into a folder for that kind, with the right file ending
#   - writes catalog.csv (one row per file: link, kind, size, status)
#   - can be stopped (Ctrl+C) and run again: finished files are skipped
#
# Keep your links file private - don't upload it to GitHub.

set -u
LIST="${1:-}"
DEST="${2:-/media/$USER/Library/Backups/arweave-$(date +%Y-%m-%d)}"
JOBS="${JOBS:-4}"

if [ -z "$LIST" ] || [ ! -f "$LIST" ]; then
    echo "Usage: bash $0 <links-file> [destination]"; exit 1
fi
command -v curl >/dev/null || { echo "Installing curl..."; sudo apt-get install -y curl >/dev/null; }
command -v file >/dev/null || { echo "Installing file..."; sudo apt-get install -y file >/dev/null; }

mkdir -p "$DEST/.meta" "$DEST/.tmp" || { echo "Can't write to $DEST"; exit 1; }
URLS="$DEST/.meta/urls.txt"
# Accept a JSON list or one link per line; keep only arweave-style links, in order, no duplicates.
grep -oE 'https?://[A-Za-z0-9.-]*arweave[A-Za-z0-9.:-]*/[A-Za-z0-9_-]{20,}[^",[:space:]]*' "$LIST" | awk '!seen[$0]++' > "$URLS"
TOTAL=$(wc -l < "$URLS")
[ "$TOTAL" -gt 0 ] || { echo "No arweave links found in $LIST"; exit 1; }

echo
echo "  ElCaciqueDeck · Arweave backup"
echo "  Links:       $TOTAL"
echo "  Saving to:   $DEST"
echo "  At a time:   $JOBS   (stop any time with Ctrl+C, run again to continue)"
echo

# kind and file ending from the content type
classify() {
    case "$1" in
        image/png) echo "Images png";;           image/jpeg|image/jpg) echo "Images jpg";;
        image/gif) echo "Images gif";;           image/webp) echo "Images webp";;
        image/svg+xml) echo "Images svg";;       image/avif) echo "Images avif";;
        image/*) echo "Images img";;
        video/mp4) echo "Videos mp4";;           video/webm) echo "Videos webm";;
        video/quicktime) echo "Videos mov";;     video/*) echo "Videos video";;
        audio/mpeg) echo "Audio mp3";;           audio/wav|audio/x-wav) echo "Audio wav";;
        audio/ogg) echo "Audio ogg";;            audio/*) echo "Audio audio";;
        application/pdf) echo "Documents pdf";;
        text/plain*) echo "Documents txt";;      text/markdown*) echo "Documents md";;
        text/html*) echo "Web html";;            text/css*) echo "Web css";;
        *javascript*) echo "Web js";;
        application/json*) echo "Data json";;    application/x.arweave-manifest+json*) echo "Data manifest.json";;
        text/csv*) echo "Data csv";;             *xml*) echo "Data xml";;
        application/zip) echo "Archives zip";;   application/x-7z-compressed) echo "Archives 7z";;
        application/gzip|application/x-gzip) echo "Archives gz";;
        application/x-tar) echo "Archives tar";;
        model/gltf-binary) echo "3D glb";;       model/*) echo "3D model";;
        *) echo "Other bin";;
    esac
}
export -f classify

fetch_one() {   # fetch_one <number> <url> <dest>
    n="$1"; url="$2"; dest="$3"
    id="$(basename "${url%%\?*}")"
    meta="$dest/.meta/$id.csv"
    [ -f "$meta" ] && grep -q ',ok$' "$meta" && exit 0          # already done
    tmp="$dest/.tmp/$id"; hdr="$dest/.tmp/$id.h"
    if curl -sfL --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 900 -D "$hdr" -o "$tmp" "$url"; then
        ctype="$(grep -i '^content-type:' "$hdr" | tail -1 | cut -d: -f2- | tr -d ' \r' | tr 'A-Z' 'a-z')"
        [ -z "$ctype" ] || [ "$ctype" = "application/octet-stream" ] && ctype="$(file -b --mime-type "$tmp")"
        read -r kind ext <<< "$(classify "$ctype")"
        mkdir -p "$dest/$kind"
        name="$(printf '%04d' "$n")_$id.$ext"
        mv -f "$tmp" "$dest/$kind/$name"
        size=$(stat -c %s "$dest/$kind/$name")
        echo "$n,$id,$url,$kind,$kind/$name,$size,$ctype,ok" > "$meta"
        echo "  [$n] ok    $kind/$name"
    else
        echo "$n,$id,$url,,,,,failed" > "$meta"
        echo "  [$n] FAIL  $url"
        rm -f "$tmp"
    fi
    rm -f "$hdr"
}
export -f fetch_one

awk '{print NR" "$0}' "$URLS" | xargs -P "$JOBS" -L 1 bash -c 'fetch_one "$0" "$1" "'"$DEST"'"'

# catalog
{
    echo "number,id,link,kind,file,bytes,content_type,status"
    cat "$DEST"/.meta/*.csv 2>/dev/null | sort -t, -k1,1n
} > "$DEST/catalog.csv"
rmdir "$DEST/.tmp" 2>/dev/null

OKN=$(grep -c ',ok$' "$DEST/catalog.csv")
FAILN=$(grep -c ',failed$' "$DEST/catalog.csv")
echo
echo "  =================================================="
echo "  Done: $OKN of $TOTAL downloaded, $FAILN failed"
echo "  Catalog: $DEST/catalog.csv"
echo "  By kind:"
for d in "$DEST"/*/; do [ -d "$d" ] && printf "    %-10s %s files\n" "$(basename "$d")" "$(find "$d" -type f | wc -l)"; done
du -sh "$DEST" 2>/dev/null | awk '{print "  Total size: "$1}'
[ "$FAILN" -gt 0 ] && echo "  Some failed - just run the same command again to retry them."
echo "  =================================================="
