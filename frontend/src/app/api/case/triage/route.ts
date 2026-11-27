import { NextRequest } from "next/server";
import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    // pass-through to real backend; backend validates contract
    return Response.json(await caseApiFetch("/api/v1/triage", { method: "POST", body: JSON.stringify(body), timeoutMs: 60000 }));
  } catch (e) { return errorResponse(e); }
}
