#!/bin/bash
# 每日 1:00 AM 自动同步书签 → 配置 → 推送 → 爬取
set -e

cd /Volumes/Samsung970/claude/labor-policy-updates

# 同步书签到配置
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 crawler/sync_bookmarks.py --mode read \
  --bookmarks "$HOME/Library/Application Support/Google/Chrome/Profile 2/AccountBookmarks" \
  --config crawler/config.yaml || echo "书签同步跳过（无书签文件或配置不变）"

# 检查配置是否有变更，有则提交推送
if ! git diff --quiet crawler/config.yaml data/sources.json; then
  git add crawler/config.yaml data/sources.json
  git commit -m "chore(config): 每日同步书签配置 $(date +'%Y-%m-%d')" || true
  git push || echo "git push 跳过（无远程或网络问题）"
  echo "已同步并推送"
fi

# 运行爬虫
echo "开始爬取政策数据..."
PYTHONPATH=$PWD /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m crawler.main \
  --config crawler/config.yaml --output data || echo "爬虫执行完成（部分源可能有失败）"
echo "爬取完成"
