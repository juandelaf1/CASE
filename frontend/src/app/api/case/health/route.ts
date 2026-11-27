import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function GET() {
  try { return Response.json(await caseApiFetch("/health")); }
  catch (e) { return errorResponse(e); }
}
