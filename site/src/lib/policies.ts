import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Policy } from "./types";

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
} {
  const policies = loadPolicies();
  const sources = new Set(policies.map((p) => p.sourceId));
  const now = new Date();
  const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const thisMonthCount = policies.filter((p) =>
    (p.publishDate || "").startsWith(thisMonth)
  ).length;
  return {
    total: policies.length,
    sourceCount: sources.size,
    thisMonthCount,
  };
}
