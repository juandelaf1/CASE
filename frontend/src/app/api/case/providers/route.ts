import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function GET() {
  try { return Response.json(await caseApiFetch("/api/v1/providers")); }
  catch (e) { return errorResponse(e); }
}
