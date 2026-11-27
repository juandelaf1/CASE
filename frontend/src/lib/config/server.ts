import "server-only";

export function getServerConfig() {
  const baseUrl = (process.env.CASE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
  const apiKey = process.env.CASE_API_KEY || "";
  return { baseUrl, apiKey };
}
