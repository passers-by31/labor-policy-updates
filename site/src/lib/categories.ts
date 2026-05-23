import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Category, SubCategory } from "./types";

const DATA_DIR = join(process.cwd(), "..", "data");
const CATEGORIES_PATH = join(DATA_DIR, "categories.json");

let _categories: Category[] | null = null;

function loadCategories(): Category[] {
  if (_categories) return _categories;
  try {
    const raw = readFileSync(CATEGORIES_PATH, "utf-8");
    _categories = JSON.parse(raw) as Category[];
  } catch {
    _categories = [];
  }
  return _categories;
}

export function getAllCategories(): Category[] {
  return [...loadCategories()].sort((a, b) => a.order - b.order);
}

export function getCategoryById(id: string): Category | undefined {
  return loadCategories().find((c) => c.id === id);
}

export function getSubCategory(
  categoryId: string,
  subId: string
): SubCategory | undefined {
  const cat = getCategoryById(categoryId);
  return cat?.subcategories?.find((s) => s.id === subId);
}

export function getPoliciesByCategory(
  categoryId: string,
  policies: { category: string }[]
): { category: string }[] {
  return policies.filter((p) => p.category === categoryId);
}
