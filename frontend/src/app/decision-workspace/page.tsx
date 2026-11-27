"use client";
import { useState } from "react";
import { useForm, useFieldArray, type Resolver } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api/client";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button, inputClass, labelClass } from "@/components/ui/primitives";
import { AlertCircle, CheckCircle2, Loader2, Plus, Trash2 } from "lucide-react";
import type { DomainsResponse, TriageDecisionResponse } from "@/types/case";

const evidenceSchema = z.object({
  id: z.string().min(1, "ID requerido"),
  type: z.enum(["text","image","file","metric","rule"]),
  content: z.string().min(1, "Contenido requerido"),
  source: z.string().min(1, "Fuente requerida"),
  confidence: z.coerce.number().min(0).max(1),
  extracted_at: z.string().min(1, "Fecha requerida"),
});
const schema = z.object({
  case_id: z.string().optional(),
  report_text: z.string().min(1, "El reporte es requerido").max(50000),
  domain: z.string().min(1, "Selecciona un dominio"),
  urgency: z.enum(["LOW","MEDIUM","HIGH","CRITICAL"]),
  external_reference: z.string().optional(),
  evidence: z.array(evidenceSchema),
});
type FormValues = z.infer<typeof schema>;

function toneForLifecycle(l: string) { if (l==="approved"||l==="AUTO_APPROVED") return "ok"; if (l.includes("review")||l.includes("pending")||l==="escalated") return "warn"; if (l==="rejected") return "crit"; return "teal"; }

export default function DecisionWorkspacePage() {
  const [result, setResult] = useState<TriageDecisionResponse | null>(null);
  const [submitError, setSubmitError] = useState<any>(null);
  const domains = useQuery({ queryKey:["domains"], queryFn: () => apiGet<DomainsResponse>("/api/case/domains") });
  const { register, control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema) as Resolver<FormValues>,
    defaultValues: { report_text: "", domain: "", urgency: "MEDIUM", case_id: "", external_reference: "", evidence: [] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "evidence" });

  const onSubmit = async (values: FormValues) => {
    setSubmitError(null); setResult(null);
    try {
      const payload = { ...values, case_id: values.case_id || undefined, external_reference: values.external_reference || undefined };
      const data = await apiPost<TriageDecisionResponse>("/api/case/triage", payload);
      setResult(data);
    } catch (e:any) { setSubmitError(e); }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-teal">Operate</div>
        <h1 className="mt-2 text-2xl font-semibold">Decision Workspace</h1>
        <p className="mt-1 text-sm text-text-muted">Evaluación real mediante <span className="case-mono">/api/v1/triage</span>. El LLM propone; CASE valida y gobierna.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card>
          <CardHeader><CardTitle>Entrada del caso</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div><label className={labelClass}>Case ID (opcional)</label><input className={inputClass} {...register("case_id")} placeholder="case-001" /></div>
                <div><label className={labelClass}>External reference (opcional)</label><input className={inputClass} {...register("external_reference")} placeholder="ticket/ref" /></div>
              </div>
              <div>
                <label className={labelClass}>Domain *</label>
                <select className={inputClass} {...register("domain")}>
                  <option value="">Seleccionar dominio...</option>
                  {(domains.data?.domains || []).map(d => <option key={d} value={d}>{d}</option>)}
                </select>
                {errors.domain && <p className="mt-1 text-xs text-critical">{errors.domain.message}</p>}
              </div>
              <div>
                <label className={labelClass}>Urgency *</label>
                <select className={inputClass} {...register("urgency")}>
                  {["LOW","MEDIUM","HIGH","CRITICAL"].map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Report text *</label>
                <textarea className={inputClass + " min-h-36"} {...register("report_text")} placeholder="Describe el caso operativo..." />
                {errors.report_text && <p className="mt-1 text-xs text-critical">{errors.report_text.message}</p>}
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className={labelClass + " mb-0"}>Evidence</label>
                  <Button type="button" variant="secondary" onClick={() => append({ id: `ev-${fields.length+1}`, type: "text", content: "", source: "", confidence: 0.8, extracted_at: new Date().toISOString() })}><Plus className="h-4 w-4"/>Agregar</Button>
                </div>
                <div className="space-y-3">
                  {fields.map((f, i) => (
                    <div key={f.id} className="rounded-lg border border-border bg-surface-2 p-3 space-y-3">
                      <div className="flex justify-between items-center"><span className="text-xs text-text-muted">Evidence {i+1}</span><button type="button" onClick={()=>remove(i)} className="text-text-dim hover:text-critical"><Trash2 className="h-4 w-4"/></button></div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <input className={inputClass} placeholder="ID" {...register(`evidence.${i}.id`)} />
                        <select className={inputClass} {...register(`evidence.${i}.type`)}>{["text","image","file","metric","rule"].map(t=><option key={t} value={t}>{t}</option>)}</select>
                        <input className={inputClass} placeholder="Source" {...register(`evidence.${i}.source`)} />
                        <input className={inputClass} placeholder="Confidence 0-1" type="number" step="0.01" min="0" max="1" {...register(`evidence.${i}.confidence`)} />
                      </div>
                      <textarea className={inputClass} placeholder="Content" {...register(`evidence.${i}.content`)} />
                      <input className={inputClass} placeholder="Extracted at ISO" {...register(`evidence.${i}.extracted_at`)} />
                    </div>
                  ))}
                </div>
              </div>

              {submitError && <div className="rounded-lg border border-critical/30 bg-critical-soft p-3 text-sm text-critical flex gap-2"><AlertCircle className="h-4 w-4 mt-0.5"/><div><div className="font-medium">{submitError.code || "Error"}</div><div>{submitError.message}</div></div></div>}

              <div className="flex gap-3">
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? <><Loader2 className="h-4 w-4 animate-spin"/>Evaluando...</> : "Evaluar caso"}</Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Resultado gobernado</CardTitle></CardHeader>
            <CardContent>
              {!result && !submitError && <div className="text-sm text-text-muted">Envía un caso para ver la decisión validada por CASE.</div>}
              {result && (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge tone={result.action === "approve" ? "ok" : result.action === "reject" ? "crit" : "warn"}>Action: {result.action}</Badge>
                    <Badge tone="default">Urgency: {result.urgency}</Badge>
                    <Badge tone={toneForLifecycle(result.lifecycle) as any}>Lifecycle: {result.lifecycle}</Badge>
                    <Badge tone="teal">Confidence: {(result.confidence*100).toFixed(0)}%</Badge>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 text-sm">
                    <div><div className="text-text-muted text-xs uppercase">Decision ID</div><div className="case-mono text-xs mt-1">{result.decision_id}</div></div>
                    <div><div className="text-text-muted text-xs uppercase">Case ID</div><div className="case-mono text-xs mt-1">{result.case_id}</div></div>
                    <div><div className="text-text-muted text-xs uppercase">Processing</div><div className="mt-1">{result.processing_time_ms.toFixed(0)} ms</div></div>
                    <div><div className="text-text-muted text-xs uppercase">Domain</div><div className="mt-1">{result.domain}</div></div>
                  </div>
                  <div><div className="text-text-muted text-xs uppercase mb-1">Reason</div><p className="text-sm text-text">{result.reason}</p></div>
                  {result.summary && <div><div className="text-text-muted text-xs uppercase mb-1">Summary</div><p className="text-sm text-text">{result.summary}</p></div>}
                  {result.evidence_summary && <div><div className="text-text-muted text-xs uppercase mb-1">Evidence summary</div><p className="text-sm text-text-muted">{result.evidence_summary}</p></div>}
                  {Array.isArray(result.decision_factors) && result.decision_factors.length > 0 && (
                    <div><div className="text-text-muted text-xs uppercase mb-1">Decision factors</div><ul className="list-disc pl-5 text-sm text-text-muted space-y-1">{result.decision_factors.map((f,i)=><li key={i}>{f}</li>)}</ul></div>
                  )}
                  {result.provider_info && <div><div className="text-text-muted text-xs uppercase mb-1">Provider info</div><pre className="text-xs bg-[#111a27] border border-border rounded-lg p-3 overflow-auto">{JSON.stringify(result.provider_info, null, 2)}</pre></div>}
                  <div className="rounded-lg border border-teal/20 bg-teal-soft p-3 text-xs text-text-muted flex gap-2"><CheckCircle2 className="h-4 w-4 text-teal mt-0.5"/>Resultado devuelto por CASE. El frontend no recalcula la decisión.</div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
