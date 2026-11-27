import { NextRequest } from "next/server";
import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const limit = Math.min(Math.max(Number(searchParams.get("limit") || 50), 1), 100);
    const offset = Math.max(Number(searchParams.get("offset") || 0), 0);
    return Response.json(await caseApiFetch(`/api/v1/cases?limit=${limit}&offset=${offset}`));
  } catch (e) { return errorResponse(e); }
}
