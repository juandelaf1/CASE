export type TriageDecisionResponse = {
  decision_id: string; case_id: string; external_reference?: string | null;
  domain: string; action: string; reason: string; urgency: string; reported_urgency?: string | null;
  confidence: number; evidence_summary: string; decision_rationale?: string; decision_factors?: string[];
  summary?: string; lifecycle: string; processing_time_ms: number;
  original_ai_proposal?: Record<string, unknown> | null;
  human_override?: Record<string, unknown> | null;
  provider_info?: Record<string, unknown> | null;
  react_trace?: Record<string, unknown> | null;
  cost?: Record<string, unknown> | null;
};
export type HealthResponse = { status: string; version: string; database: string; db_path: string; domains: string[]; domain_count: number; active_provider: string; providers: {name:string;model:string}[] };
export type ProvidersResponse = { providers: {name:string;model:string;is_mock:boolean}[]; active_provider: string };
export type DomainsResponse = { domains: string[] };
export type CasesResponse = { decisions: any[]; total: number; limit: number; offset: number };
export type PendingResponse = { decisions: any[]; count: number };
