"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api/client";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button, inputClass, labelClass } from "@/components/ui/primitives";
import { AlertCircle, Loader2, RefreshCw, ShieldAlert } from "lucide-react";
import type { PendingResponse } from "@/types/case";

type Decision = any;

function Err({ e }: { e: any }) {
  if (!e) return null;
  return <div className="rounded-lg border border-critical/30 bg-critical-soft p-3 text-sm text-critical flex gap-2"><AlertCircle className="h-4 w-4 mt-0.5"/><div><div className="font-medium">{e.code || "Error"}</div><div>{e.message || String(e)}</div></div></div>;
}

export default function HumanReviewPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actor, setActor] = useState("operator");
  const [justification, setJustification] = useState("");
  const [actionError, setActionError] = useState<any>(null);
  const [confirm, setConfirm] = useState<null | { kind: string; payload?: any }>(null);

  const pending = useQuery({ queryKey: ["hitl-pending"], queryFn: () => apiGet<PendingResponse>("/api/case/hitl/pending?limit=50") });
  const detail = useQuery({
    queryKey: ["hitl-detail", selectedId],
    queryFn: () => apiGet<Decision>(`/api/case/hitl/${selectedId}`),
    enabled: !!selectedId,
  });

  const mutate = useMutation({
    mutationFn: async ({ kind, payload }: { kind: string; payload?: any }) => {
      if (!selectedId) throw { message: "No decision selected" };
      const base = { actor, justification };
      if (kind === "under-review") return apiPost(`/api/case/hitl/${selectedId}/under-review`, base);
      if (kind === "approve") return apiPost(`/api/case/hitl/${selectedId}/approve`, base);
      if (kind === "reject") return apiPost(`/api/case/hitl/${selectedId}/reject`, base);
      if (kind === "escalate") return apiPost(`/api/case/hitl/${selectedId}/escalate`, { ...base, escalate_to: payload?.escalate_to || "supervisor" });
      if (kind === "modify") return apiPost(`/api/case/hitl/${selectedId}/modify`, { ...payload, actor, justification });
      throw { message: "Unknown action" };
    },
    onSuccess: async () => {
      setActionError(null); setConfirm(null); setJustification("");
      await qc.invalidateQueries({ queryKey: ["hitl-pending"] });
      await qc.invalidateQueries({ queryKey: ["hitl-detail", selectedId] });
    },
    onError: (e:any) => setActionError(e),
  });

  const d = detail.data;
  const canAct = !!d && ["ai_proposed","under_review"].includes(String(d.lifecycle));

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-teal">Operate</div>
        <h1 className="mt-2 text-2xl font-semibold">Human Review</h1>
        <p className="mt-1 text-sm text-text-muted">Cola HITL real. Acciones conectadas a endpoints existentes. El actor/justificación son declarados, no identidad verificada.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between"><CardTitle>Pending decisions</CardTitle><Button variant="ghost" onClick={()=>pending.refetch()}><RefreshCw className="h-4 w-4"/></Button></CardHeader>
          <CardContent className="space-y-2">
            {pending.isLoading && <div className="text-sm text-text-muted">Cargando...</div>}
            <Err e={pending.error as any} />
            {pending.data?.decisions?.length === 0 && <div className="text-sm text-text-muted">No hay decisiones pendientes.</div>}
            {pending.data?.decisions?.map((dec: any) => (
              <button key={dec.decision_id} onClick={() => { setSelectedId(dec.decision_id); setActionError(null); }}
                className={`w-full text-left rounded-lg border p-3 transition-colors ${selectedId===dec.decision_id ? "border-teal/40 bg-teal-soft" : "border-border bg-surface-2 hover:bg-surface-3"}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="case-mono text-xs text-text-muted">{dec.decision_id}</div>
                  <Badge tone={dec.lifecycle==="escalated"?"crit":"warn"}>{dec.lifecycle}</Badge>
                </div>
                <div className="mt-1 text-sm text-text">{dec.action} · {dec.domain}</div>
                <div className="mt-1 text-xs text-text-muted">confidence {(Number(dec.confidence||0)*100).toFixed(0)}%</div>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Decision detail</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {!selectedId && <div className="text-sm text-text-muted">Selecciona una decisión pendiente.</div>}
            {selectedId && detail.isLoading && <div className="text-sm text-text-muted">Cargando detalle...</div>}
            <Err e={detail.error as any} />
            {d && (
              <>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={d.action==="approve"?"ok":d.action==="reject"?"crit":"warn"}>{d.action}</Badge>
                  <Badge tone="default">{d.domain}</Badge>
                  <Badge tone={d.lifecycle==="escalated"?"crit":"warn"}>{d.lifecycle}</Badge>
                  <Badge tone="teal">{(Number(d.confidence||0)*100).toFixed(0)}%</Badge>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 text-sm">
                  <div><div className="text-xs uppercase text-text-muted">Decision ID</div><div className="case-mono text-xs mt-1">{d.decision_id}</div></div>
                  <div><div className="text-xs uppercase text-text-muted">Case ID</div><div className="case-mono text-xs mt-1">{d.case_id}</div></div>
                </div>
                <div><div className="text-xs uppercase text-text-muted mb-1">Reason</div><p className="text-sm">{d.reason}</p></div>
                {d.evidence_summary && <div><div className="text-xs uppercase text-text-muted mb-1">Evidence summary</div><p className="text-sm text-text-muted">{d.evidence_summary}</p></div>}

                <div className="border-t border-border pt-4 space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div><label className={labelClass}>Actor (declarado)</label><input className={inputClass} value={actor} onChange={e=>setActor(e.target.value)} /></div>
                    <div><label className={labelClass}>Justification</label><input className={inputClass} value={justification} onChange={e=>setJustification(e.target.value)} placeholder="Motivo de la acción" /></div>
                  </div>
                  <Err e={actionError} />
                  <div className="flex flex-wrap gap-2">
                    <Button variant="secondary" disabled={!canAct || mutate.isPending} onClick={()=>mutate.mutate({kind:"under-review"})}>Under review</Button>
                    <Button disabled={!canAct || mutate.isPending} onClick={()=>setConfirm({kind:"approve"})}>Approve</Button>
                    <Button variant="danger" disabled={!canAct || mutate.isPending} onClick={()=>setConfirm({kind:"reject"})}>Reject</Button>
                    <Button variant="secondary" disabled={!canAct || mutate.isPending} onClick={()=>setConfirm({kind:"escalate", payload:{escalate_to:"supervisor"}})}>Escalate</Button>
                  </div>
                  {!canAct && <div className="text-xs text-text-dim">No hay acciones HITL disponibles para el estado actual ({d.lifecycle}).</div>}
                  {mutate.isPending && <div className="text-xs text-text-muted flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin"/>Aplicando acción...</div>}
                </div>

                {confirm && (
                  <div className="rounded-lg border border-warning/30 bg-warning-soft p-4 space-y-3">
                    <div className="text-sm font-medium text-warning flex items-center gap-2"><ShieldAlert className="h-4 w-4"/>Confirmar acción: {confirm.kind}</div>
                    <p className="text-xs text-text-muted">Esta acción afecta el estado HITL en CASE. Revisa justificación y actor antes de continuar.</p>
                    <div className="flex gap-2">
                      <Button onClick={()=>mutate.mutate(confirm)} disabled={mutate.isPending}>Confirmar</Button>
                      <Button variant="ghost" onClick={()=>setConfirm(null)}>Cancelar</Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
