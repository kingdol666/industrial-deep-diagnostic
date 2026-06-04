#!/bin/bash
# Industrial Deep Diagnostic — Hermes Profile Helper
#
# 用法: bash .hermes/setup_skills.sh
#
# 本项目不推荐把 skill 链接到全局 ~/.hermes/skills/。
# 推荐做法是创建一个项目专用 Hermes profile，并通过 skills.external_dirs
# 指向当前仓库的 .hermes/skills/，这样只有在使用该 profile 时这两个 skill 才可见。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE_DIR="$HOME/.hermes/profiles/ind-diag"
PROFILE_FILE="$PROFILE_DIR/config.yaml"

mkdir -p "$PROFILE_DIR"

cat > "$PROFILE_FILE" <<EOF
skills:
  external_dirs:
    - $PROJECT_ROOT/.hermes/skills

delegation:
  orchestrator_enabled: true
  max_spawn_depth: 2
  model: deepseek-v4-flash
  provider: deepseek
  base_url: https://api.deepseek.com
  max_iterations: 80
  reasoning_effort: high

auxiliary:
  vision:
    provider: deepseek
    model: deepseek-v4-flash
    timeout: 300
    download_timeout: 60

  web_extract:
    provider: deepseek
    model: deepseek-v4-flash
    timeout: 360
EOF

echo "Wrote project-local Hermes profile:"
echo "  $PROFILE_FILE"
echo ""
echo "This does NOT register project skills into ~/.hermes/skills/."
echo "Use them only for this project with:"
echo "  hermes -p ind-diag"
