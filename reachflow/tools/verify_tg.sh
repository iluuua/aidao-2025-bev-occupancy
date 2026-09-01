#!/usr/bin/env bash
# Verify Telegram handles against t.me. Input: file with one handle/url per line.
# Output: TSV -> handle \t status \t kind \t title \t count \t description
set -u
IN="$1"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

norm() {
  echo "$1" | tr -d '\r' | sed -e 's#^https\?://##' -e 's#^www\.##' -e 's#^t\.me/##' -e 's#^telegram\.me/##' -e 's#^s/##' -e 's/^@//' -e 's#/*$##' -e 's/?.*//'
}

check_one() {
  local h="$1" html title desc extra kind count status
  for attempt in 1 2 3; do
    html=$(curl -sS -m 25 -A "$UA" "https://t.me/$h" 2>/dev/null) && [ -n "$html" ] && break
    sleep 2
  done
  if [ -z "${html:-}" ]; then
    printf '%s\tNETFAIL\t\t\t\t\n' "$h"; return
  fi
  title=$(printf '%s' "$html" | grep -oP '(?<=<meta property="og:title" content=")[^"]*' | head -1)
  desc=$(printf '%s' "$html" | grep -oP '(?<=<meta property="og:description" content=")[^"]*' | head -1 | cut -c1-300)
  extra=$(printf '%s' "$html" | grep -oP '(?<=tgme_page_extra">)[^<]*' | head -1)
  count=$(printf '%s' "$extra" | sed -e 's/\(subscriber\|member\).*//' | tr -cd '0-9')
  kind=UNKNOWN
  case "$extra" in
    *subscriber*) kind=CHANNEL ;;
    *member*) kind=GROUP ;;
    *online*) kind=GROUP ;;
  esac
  if printf '%s' "$html" | grep -q 'tgme_page_action'; then :; fi
  if [ -z "$title" ] || [ "$title" = "Telegram: Contact @$h" ]; then
    status=DEAD_OR_PRIVATE
  elif [ -n "$extra" ]; then
    status=LIVE
  else
    status=LIVE_NOCOUNT
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$h" "$status" "$kind" "${title//$'\t'/ }" "${count:-}" "${desc//$'\t'/ }"
}

export -f check_one norm
export UA

sed -e 's/[[:space:]]*$//' "$IN" | grep -v '^$' | while read -r raw; do norm "$raw"; done \
  | grep -viE '^(proxy|socks|share|iv|s|joinchat)$' | grep -E '^([A-Za-z0-9_]{4,64}|\+[A-Za-z0-9_-]{8,64}|addlist/[A-Za-z0-9_-]{4,64}|joinchat/[A-Za-z0-9_-]{8,64})$' \
  | sort -u > .handles.txt

wc -l < .handles.txt
xargs -a .handles.txt -I{} -P 8 bash -c 'check_one "$@"' _ {}
