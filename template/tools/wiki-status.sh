#!/usr/bin/env bash
set -euo pipefail
{
  printf '# Status\n\n_generated %s from `.beads/` — do not edit_\n\n' "$(date '+%Y-%m-%d %H:%M')"
  printf '## Backlog (p4)\n\n```\n';    bd list --priority 4 | head -20;     printf '```\n\n'
  printf '## Ready\n\n```\n';           bd ready;                            printf '```\n\n'
  printf '## In flight\n\n```\n';       bd list --status in_progress;        printf '```\n\n'
  printf '## Recently closed\n\n```\n'; bd list --status closed | head -20;  printf '```\n'
} > wiki/status.md
