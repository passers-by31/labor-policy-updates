import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataPath = join(__dirname, "..", "..", "data", "policies.json");
const outputDir = join(__dirname, "..", "public");

mkdirSync(outputDir, { recursive: true });

const index = { version: "0.7", doc: [], index: [] };

if (existsSync(dataPath)) {
  const raw = readFileSync(dataPath, "utf-8");
  const policies = JSON.parse(raw);

  index.doc = policies.map((p) => ({
    id: p.id,
    title: p.title || "",
    summary: p.summary || "",
    tags: Array.isArray(p.tags) ? p.tags.join(" ") : (p.tags || ""),
    documentNumber: p.documentNumber || "",
    content: (p.content || "")
      .replace(/<[^>]*>/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .substring(0, 3000),
    publishDate: p.publishDate || "",
    category: p.category || "",
    sourceId: p.sourceId || "",
  }));
}

writeFileSync(join(outputDir, "search-index.json"), JSON.stringify(index.doc));
console.log(`搜索索引已生成: ${index.doc.length} 条政策`);
