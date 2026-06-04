#!/bin/bash
# Industrial Deep Diagnostic — Hermes Skill Setup
# 
# 用法: bash setup_skills.sh
# 
# 此脚本将项目 skill 目录通过 symlink 链接到 ~/.hermes/skills/，让 Hermes 能够自动发现它们。
# 无需在 config.yaml 中写死外部路径 — symlink 是零配置、零依赖的方案。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_SKILLS="$SCRIPT_DIR/skills"
HERMES_SKILLS="$HOME/.hermes/skills"

echo "=== Industrial Deep Diagnostic — Skill Setup ==="
echo ""

if [ ! -d "$PROJECT_SKILLS" ]; then
    echo "ERROR: Project skills directory not found: $PROJECT_SKILLS"
    exit 1
fi

if [ ! -d "$HERMES_SKILLS" ]; then
    echo "Creating $HERMES_SKILLS ..."
    mkdir -p "$HERMES_SKILLS"
fi

linked=0
skipped=0

for skill_dir in "$PROJECT_SKILLS"/*/; do
    skill_name=$(basename "$skill_dir")
    
    # Skip non-skill dirs (no SKILL.md)
    if [ ! -f "$skill_dir/SKILL.md" ]; then
        continue
    fi
    
    target="$HERMES_SKILLS/$skill_name"
    
    if [ -L "$target" ]; then
        # Already a symlink — check if it points to the right place
        current_target=$(readlink "$target")
        if [ "$current_target" = "$skill_dir" ]; then
            echo "  [SKIP] $skill_name — already linked correctly"
            skipped=$((skipped + 1))
            continue
        else
            echo "  [FIX]  $skill_name — updating symlink"
            rm "$target"
        fi
    elif [ -e "$target" ]; then
        echo "  [SKIP] $skill_name — target exists (not a symlink), manual check needed"
        skipped=$((skipped + 1))
        continue
    fi
    
    ln -sf "$skill_dir" "$target"
    echo "  [LINK] $skill_name -> $skill_dir"
    linked=$((linked + 1))
done

echo ""
echo "=== Done: $linked linked, $skipped skipped ==="
echo ""
echo "Verify with: hermes skills list | grep -E 'industrial-deep-diagnostic|rag-knowledge-builder'"
