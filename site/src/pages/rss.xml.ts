import rss from "@astrojs/rss";
import type { APIRoute } from "astro";
import { getAllPolicies } from "../lib/policies";

export const GET: APIRoute = async (context) => {
  const site = context.site ?? new URL("https://labor-policy-updates.pages.dev");
  const policies = getAllPolicies();

  return rss({
    title: "劳动政策更新",
    description: "自动采集国内劳动相关政策法规通知更新",
    site: site.toString(),
    customData: `<language>zh-cn</language>`,
    items: policies.slice(0, 50).map((p) => ({
      title: p.title,
      pubDate: new Date(p.publishDate || p.crawlDate),
      description: p.summary || p.title,
      link: `/policies/${p.id}/`,
      categories: [p.category, ...(p.subcategory ? [p.subcategory] : [])],
    })),
  });
};
