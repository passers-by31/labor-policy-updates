import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Policy, ChangelogEntry } from "./types";

const DATA_DIR = join(process.cwd(), "..", "data");
const POLICIES_PATH = join(DATA_DIR, "policies.json");

let _policies: Policy[] | null = null;

function loadPolicies(): Policy[] {
  if (_policies) return _policies;
  try {
    const raw = readFileSync(POLICIES_PATH, "utf-8");
    _policies = JSON.parse(raw) as Policy[];
    _policies.sort(
      (a, b) =>
        new Date(b.publishDate || b.crawlDate).getTime() -
        new Date(a.publishDate || a.crawlDate).getTime()
    );
  } catch {
    _policies = [];
  }
  return _policies;
}

export function getAllPolicies(): Policy[] {
  return loadPolicies();
}

export function getPolicyById(id: string): Policy | undefined {
  return loadPolicies().find((p) => p.id === id);
}

export function getPoliciesBySource(sourceId: string): Policy[] {
  return loadPolicies().filter((p) => p.sourceId === sourceId);
}

export function getRecentPolicies(count = 10): Policy[] {
  return loadPolicies().slice(0, count);
}

export function getPoliciesByRegion(region: string): Policy[] {
  return loadPolicies().filter((p) => p.regions?.includes(region));
}

export function getPolicyStats(): {
  total: number;
  sourceCount: number;
  thisMonthCount: number;
  latestCrawlCount: number;
} {
  const policies = loadPolicies();
  const sources = new Set(policies.map((p) => p.sourceId));
  const now = new Date();
  const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const thisMonthCount = policies.filter((p) =>
    (p.publishDate || "").startsWith(thisMonth)
  ).length;
  const latest = getLatestCrawlInfo();
  return {
    total: policies.length,
    sourceCount: sources.size,
    thisMonthCount,
    latestCrawlCount: latest.newCount,
  };
}

export function getLatestCrawlInfo(): { newCount: number; newPolicies: string[]; date: string } {
  try {
    const path = join(DATA_DIR, "changelog.json");
    const raw = readFileSync(path, "utf-8");
    const entries: ChangelogEntry[] = JSON.parse(raw);
    const latest = entries[0] || { newCount: 0, newPolicies: [], date: "" };
    return { newCount: latest.newCount, newPolicies: latest.newPolicies, date: latest.date };
  } catch {
    return { newCount: 0, newPolicies: [], date: "" };
  }
}
