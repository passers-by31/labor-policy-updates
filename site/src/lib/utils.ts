export function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) {
    return `${match[1]}年${parseInt(match[2])}月${parseInt(match[3])}日`;
  }
  return dateStr;
}

export function truncate(text: string, length: number): string {
  if (!text || text.length <= length) return text || "";
  return text.slice(0, length) + "…";
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    effective: "现行有效",
    amended: "已修改",
    repealed: "已废止",
    draft: "征求意见稿",
  };
  return map[status] || status;
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    effective: "bg-green-100 text-green-800",
    amended: "bg-yellow-100 text-yellow-800",
    repealed: "bg-red-100 text-red-800",
    draft: "bg-blue-100 text-blue-800",
  };
  return map[status] || "bg-gray-100 text-gray-800";
}
