#!/bin/bash
# 每日 1:00 AM 自动同步书签 → 配置 → 推送
set -e

cd /Volumes/Samsung970/claude/labor-policy-updates

# 同步书签到配置
/usr/bin/python3 crawler/sync_bookmarks.py --mode read \
  --bookmarks "$HOME/Library/Application Support/Google/Chrome/Profile 2/AccountBookmarks" \
  --config crawler/config.yaml

# 检查是否有变更
if git diff --quiet crawler/config.yaml data/sources.json; then
  echo "配置无变化，跳过提交"
  exit 0
fi

# 提交并推送
git add crawler/config.yaml data/sources.json
git commit -m "chore(config): 每日同步书签配置 $(date +'%Y-%m-%d')"
git push
echo "已同步并推送"
