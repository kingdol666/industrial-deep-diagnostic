# 双版本同步说明

本 skill 同时维护两个版本：

- `.claude/skills/industrial-deep-diagnostic/` — Claude Code 使用
- `.agents/skills/industrial-deep-diagnostic/` — Codex / 其他 Agent 使用

## 同步原则

1. **权威来源**：`.claude/skills/industrial-deep-diagnostic/` 是开发主版本。
2. **单向同步**：通常从 `.claude/` 同步到 `.agents/`，除非明确针对 Codex 平台的修改。
3. **全量同步**：使用 `rsync -av --delete` 确保内容一致。
4. **差异审计**：同步后必须运行 `diff` 检查，只允许平台特定差异。

## 同步命令

```bash
# 从 .claude 同步到 .agents（常规）
rsync -av --delete \
  .claude/skills/industrial-deep-diagnostic/ \
  .agents/skills/industrial-deep-diagnostic/

# 验证一致性
diff -r \
  .claude/skills/industrial-deep-diagnostic/ \
  .agents/skills/industrial-deep-diagnostic/
```

## 允许的差异

| 类型 | 说明 | 示例 |
|------|------|------|
| 平台路径 | 不同平台对 skill 根目录的引用 | 无（当前两个版本路径结构一致） |
| 明确标注的平台适配说明 | 在文档中说明仅适用于某平台 | 文件顶部标注 "Codex only" |

**注意**：Agent 协议、schema、脚本、模板等核心文件必须完全一致。

## 禁止的差异

- Agent 协议内容不一致
- schema 定义不一致
- 执行流程不一致
- 红灯动作或治理规则不一致

## 自动化建议

未来可添加 CI 钩子：

```bash
# pre-commit 钩子示例
#!/bin/bash
rsync -av --delete .claude/skills/industrial-deep-diagnostic/ .agents/skills/industrial-deep-diagnostic/
DIFF=$(diff -rq .claude/skills/industrial-deep-diagnostic/ .agents/skills/industrial-deep-diagnostic/)
if [ -n "$DIFF" ]; then
  echo "Sync failed: $DIFF"
  exit 1
fi
```

## 同步记录

每次涉及双版本同步的提交，提交信息应以 `sync(.agents):` 开头，并说明同步范围。
