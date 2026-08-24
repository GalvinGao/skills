#!/usr/bin/env bash
# Upload an image with `gh attach` and make it the FIRST line of a PR's description.
#
# Re-running with a new screenshot replaces the existing leading <img> rather than stacking
# another one, so it is safe to call repeatedly while iterating on a shot.
#
#   pr-attach-image.sh --pr 123 --image ./pr-shot.png --alt "New x on the frame tiles"
set -euo pipefail

PR="" IMAGE="" ALT="" WIDTH=900 REPO="" GH=(gh)

while [ $# -gt 0 ]; do
  case "$1" in
    --pr) PR="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --alt) ALT="$2"; shift 2 ;;
    --width) WIDTH="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    # Run gh through a node version manager when the extension needs a pinned node.
    --node) GH=(fnm exec --using="$2" -- gh); shift 2 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

[ -n "$PR" ] && [ -n "$IMAGE" ] || { echo "--pr and --image are required" >&2; exit 2; }
[ -f "$IMAGE" ] || { echo "no such image: $IMAGE" >&2; exit 1; }
[ -n "$ALT" ] || ALT="Screenshot of the change in this PR"

REPO_ARGS=()
[ -n "$REPO" ] && REPO_ARGS=(--repo "$REPO")

# `--release` is the CLI-auth-only upload path (browser mode needs playwright-cli). It targets a
# `gh-attach-assets` release; warn if this run would be the one that creates it.
if ! "${GH[@]}" release view gh-attach-assets "${REPO_ARGS[@]}" >/dev/null 2>&1; then
  echo "note: no gh-attach-assets release yet — this upload creates one in the target repo." >&2
fi

URL=$("${GH[@]}" attach "${REPO_ARGS[@]}" --issue "$PR" --image "$IMAGE" --release --url-only \
  | grep -Eo 'https://[^[:space:]]+' | tail -1)
[ -n "$URL" ] || { echo "gh attach returned no URL" >&2; exit 1; }

BODY=$(mktemp) NEW=$(mktemp)
trap 'rm -f "$BODY" "$NEW"' EXIT
"${GH[@]}" pr view "$PR" "${REPO_ARGS[@]}" --json body --jq .body > "$BODY"

printf '<img width="%s" alt="%s" src="%s" />\n\n' "$WIDTH" "$ALT" "$URL" > "$NEW"
# Drop a leading <img …> (and the blank line after it) so a re-run swaps the image in place.
awk 'NR==1 && /^[[:space:]]*<img /{ skip=1; next } skip && NF==0 { skip=0; next } { skip=0; print }' \
  "$BODY" >> "$NEW"

"${GH[@]}" pr edit "$PR" "${REPO_ARGS[@]}" --body-file "$NEW" >/dev/null
echo "$URL"
echo "attached as the first line of PR #$PR"
