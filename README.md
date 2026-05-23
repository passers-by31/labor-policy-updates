# 劳动政策更新采集站

自动采集国内劳动相关政策法规通知更新的静态网站。

## 功能

- **自动采集**：每日自动从人社部、国务院等政府网站抓取最新劳动政策
- **分类浏览**：12 大分类体系（工资薪酬、社会保险、住房公积金、劳动合同等）
- **全文搜索**：客户端实时搜索，支持中文连续字符匹配
- **RSS 订阅**：标准 RSS 源，支持主流阅读器
- **筛选过滤**：按分类、来源、地区、日期等多维度筛选

## 技术栈

- **前端**：Astro + Tailwind CSS
- **搜索**：FlexSearch（客户端，带中文优化）
- **爬虫**：Python (requests + BeautifulSoup4)
- **托管**：Cloudflare Pages
- **CI/CD**：GitHub Actions

## 项目结构

```
labor-policy-updates/
├── crawler/          # Python 爬虫
│   ├── spiders/      # 各目标站爬虫
│   ├── parsers/      # 内容解析器
│   ├── filters/      # 相关性过滤 + 去重
│   ├── middleware/    # 限速/UA/重试
│   └── main.py       # 爬虫入口
├── site/             # Astro 前端站点
│   └── src/
│       ├── pages/    # 页面
│       ├── components/  # UI 组件
│       └── lib/      # 工具函数
├── data/             # 爬虫输出数据（版本管理）
└── .github/workflows/  # CI/CD 流水线
```

## 本地开发

### 前端站点

```bash
cd site
npm install
npm run dev
```

### 爬虫

```bash
cd crawler
pip install -r requirements.txt
python main.py --config config.yaml --output ../data
```

## 免责声明

本网站政策信息仅供参考，具体以政府官方发布的原文为准。数据来源于政府公开信息，如有疑问请访问原始出处核实。

## License

MIT
