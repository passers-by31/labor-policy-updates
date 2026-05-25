import FlexSearch from "flexsearch";

export interface SearchDoc {
  id: string;
  title: string;
  summary: string;
  tags: string;
  documentNumber: string;
  content: string;
  publishDate: string;
  sourceId: string;
}

let index: FlexSearch.Document<
  SearchDoc,
  string[]
> | null = null;
let docs: SearchDoc[] = [];

export async function loadSearchIndex(): Promise<void> {
  if (index) return;

  const res = await fetch("/search-index.json");
  if (!res.ok) return;
  docs = await res.json();
  if (docs.length === 0) return;

  index = new FlexSearch.Document({
    tokenize: "forward",
    cache: 100,
    document: {
      id: "id",
      index: [
        { field: "title", tokenize: "forward", resolution: 9 },
        { field: "tags", tokenize: "forward", resolution: 8 },
        { field: "documentNumber", tokenize: "forward", resolution: 8 },
        { field: "summary", tokenize: "forward", resolution: 5 },
        { field: "content", tokenize: "forward", resolution: 1 },
      ],
      store: [
        "title",
        "summary",
        "publishDate",
        "sourceId",
        "tags",
        "documentNumber",
      ],
    },
  });

  for (const doc of docs) {
    index.add(doc);
  }
}

export interface SearchFilters {
  sourceId?: string;
}

export async function search(
  query: string,
  filters?: SearchFilters
): Promise<SearchDoc[]> {
  if (!query.trim()) return [];
  await loadSearchIndex();
  if (!index || docs.length === 0) return [];

  const rawResults = index.search(query, { limit: 100, enrich: true });
  if (!rawResults || rawResults.length === 0) return [];

  const fieldOrder = [
    "title",
    "tags",
    "documentNumber",
    "summary",
    "content",
  ];
  const seen = new Set<string>();
  const merged: SearchDoc[] = [];

  for (const field of fieldOrder) {
    const fr = rawResults.find(
      (r: { field: string; result: { id: string; doc: SearchDoc }[] }) =>
        r.field === field
    );
    if (!fr || !fr.result) continue;
    for (const item of fr.result) {
      if (!seen.has(item.id)) {
        seen.add(item.id);
        merged.push(item.doc);
      }
    }
  }

  let results = merged;

  if (filters?.sourceId) {
    results = results.filter((d) => d.sourceId === filters.sourceId);
  }

  results.sort(
    (a, b) =>
      new Date(b.publishDate).getTime() - new Date(a.publishDate).getTime()
  );

  return results;
}
