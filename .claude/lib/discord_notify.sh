#!/usr/bin/env bash
# discord_notify.sh - Send notifications to Discord webhook

# Send a Discord embed notification
# Usage: send_discord_embed WEBHOOK_URL TITLE DESCRIPTION COLOR FIELDS_JSON
send_discord_embed() {
  local webhook_url="$1"
  local title="$2"
  local description="$3"
  local color="$4"
  local fields_json="$5"

  # Build embed payload
  local payload
  payload=$(cat <<EOF
{
  "embeds": [{
    "title": "${title}",
    "description": "${description}",
    "color": ${color},
    "fields": ${fields_json},
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }]
}
EOF
)

  # Send webhook
  curl -X POST "${webhook_url}" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    -s -o /dev/null -w "%{http_code}" || echo "000"
}

# Send a simple Discord message
# Usage: send_discord_message WEBHOOK_URL MESSAGE
send_discord_message() {
  local webhook_url="$1"
  local message="$2"

  local payload
  payload=$(cat <<EOF
{
  "content": "${message}"
}
EOF
)

  curl -X POST "${webhook_url}" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    -s -o /dev/null -w "%{http_code}" || echo "000"
}

# Format PR list for Discord field
# Usage: format_pr_list PR_NUMBERS
format_pr_list() {
  local prs="$1"
  local formatted=""

  for pr in $prs; do
    formatted="${formatted}✅ PR #${pr}\n"
  done

  echo -n "$formatted"
}

# Color codes
DISCORD_COLOR_SUCCESS=5763719     # Green
DISCORD_COLOR_WARNING=16776960    # Yellow
DISCORD_COLOR_ERROR=15158332      # Red
DISCORD_COLOR_INFO=5814783        # Blue
