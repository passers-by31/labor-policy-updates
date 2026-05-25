export interface Policy {
  id: string;
  title: string;
  url: string;
  sourceId: string;
  sourceName: string;
  documentNumber: string;
  publishDate: string;
  effectiveDate: string | null;
  crawlDate: string;
  updatedDate: string | null;
  category: string;
  subcategory: string | null;
  tags: string[];
  regions: string[];
  issuingAuthority: string;
  status: "effective" | "amended" | "repealed" | "draft";
  amendmentOf: string | null;
  supersedes: string[];
  summary: string;
  content: string;
  contentHtml: string | null;
  relatedPolicyIds: string[];
  isNew: boolean;
}

export interface Source {
  id: string;
  name: string;
  url: string;
  region: string;
  level: "national" | "province";
}

export interface ChangelogEntry {
  date: string;
  timestamp: string;
  newCount: number;
  updatedCount: number;
  totalCount: number;
  newPolicies: string[];
  summary: string;
}
