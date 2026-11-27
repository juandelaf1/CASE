import { NextRequest } from "next/server";
import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const limit = Math.min(Math.max(Number(searchParams.get("limit") || 100), 1), 200);
    return Response.json(await caseApiFetch(`/api/v1/hitl/pending?limit=${limit}`));
  } catch (e) { return errorResponse(e); }
}
