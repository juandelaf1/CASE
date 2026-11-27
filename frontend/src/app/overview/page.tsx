"use client";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api/client";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "@/components/ui/primitives";
import { Activity, Database, Layers, Cpu, FolderOpen, ShieldAlert, AlertCircle } from "lucide-react";
import type { HealthResponse, DomainsResponse, ProvidersResponse, CasesResponse, PendingResponse } from "@/types/case";

function Stat({ label, value, sub, icon: Icon, tone }: { label: string; value: string | number; sub?: string; icon: any; tone?: "default"|"teal"|"warn"|"crit"|"ok" }) {
  const toneClass = tone === "ok" ? "text-success" : tone === "warn" ? "text-warning" : tone === "crit" ? "text-critical" : "text-teal";
  return (
    <Card><CardContent className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-text-muted">{label}</div>
          <div className="mt-2 text-2xl font-semibold text-text">{value}</div>
          {sub && <div className="mt-1 text-xs text-text-muted">{sub}</div>}
        </div>
        <div className={`rounded-lg bg-surface-2 p-2 ${toneClass}`}><Icon className="h-5 w-5" /></div>
      </div>
    </CardContent></Card>
  );
}

function ErrorBox({ message }: { message: string }) {
  return <div className="case-panel border-critical/30 p-4 text-sm text-critical flex items-center gap-2"><AlertCircle className="h-4 w-4"/>{message}</div>;
}

export default function OverviewPage() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => apiGet<HealthResponse>("/api/case/health") });
  const domains = useQuery({ queryKey: ["domains"], queryFn: () => apiGet<DomainsResponse>("/api/case/domains") });
  const providers = useQuery({ queryKey: ["providers"], queryFn: () => apiGet<ProvidersResponse>("/api/case/providers") });
  const cases = useQuery({ queryKey: ["cases-summary"], queryFn: () => apiGet<CasesResponse>("/api/case/cases?limit=1&offset=0") });
  const pending = useQuery({ queryKey: ["hitl-pending-summary"], queryFn: () => apiGet<PendingResponse>("/api/case/hitl/pending?limit=1") });

  const loading = health.isLoading || domains.isLoading || providers.isLoading;
  const err = health.error as any;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-teal">Operate</div>
        <h1 className="mt-2 text-2xl font-semibold text-text">Overview</h1>
        <p className="mt-1 text-sm text-text-muted">Estado real del sistema CASE, dominios, providers, casos y revisiones pendientes.</p>
      </div>

      {err && <ErrorBox message={err.message || "No se pudo cargar el estado del sistema."} />}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="API Status" value={health.data?.status ?? (health.isLoading ? "…" : "No disponible")} sub={health.data ? `v${health.data.version}` : undefined}
          icon={Activity} tone={health.data?.status === "ok" ? "ok" : health.data ? "warn" : "default"} />
        <Stat label="Database" value={health.data?.database ?? (health.isLoading ? "…" : "No disponible")} sub={health.data?.db_path ? "SQLite" : undefined}
          icon={Database} tone={health.data?.database === "ok" ? "ok" : health.data ? "warn" : "default"} />
        <Stat label="Domains" value={health.data?.domain_count ?? domains.data?.domains?.length ?? (loading ? "…" : "N/A")} sub="Registrados en CASE" icon={Layers} tone="teal" />
        <Stat label="Active Provider" value={health.data?.active_provider ?? (loading ? "…" : "N/A")} sub={providers.data ? `${providers.data.providers.length} providers disponibles` : undefined} icon={Cpu} tone="teal" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Total Cases" value={cases.data?.total ?? (cases.isLoading ? "…" : "No disponible")} sub="Devuelto por /api/v1/cases" icon={FolderOpen} />
        <Stat label="HITL Pending" value={pending.data?.count ?? (pending.isLoading ? "…" : "No disponible")} sub="Devuelto por /api/v1/hitl/pending" icon={ShieldAlert}
          tone={(pending.data?.count ?? 0) > 0 ? "warn" : "ok"} />
        <Card className="sm:col-span-2"><CardHeader><CardTitle>Providers disponibles</CardTitle></CardHeader><CardContent>
          {providers.isLoading ? <div className="text-sm text-text-muted">Cargando...</div> :
           providers.data?.providers?.length ? <div className="flex flex-wrap gap-2">{providers.data.providers.map(p => (
             <Badge key={p.name} tone={p.name === providers.data.active_provider ? "teal" : "default"}>
               {p.name}{p.is_mock ? " · mock" : ""} <span className="ml-1 opacity-70">{p.model}</span>
             </Badge>
           ))}</div> : <div className="text-sm text-text-muted">No disponible.</div>}
        </CardContent></Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Dominios registrados</CardTitle></CardHeader><CardContent>
          {domains.isLoading ? <div className="text-sm text-text-muted">Cargando...</div> :
           (domains.data?.domains || health.data?.domains)?.length ? <div className="flex flex-wrap gap-2">{(domains.data?.domains || health.data?.domains || []).map(d => (
             <Badge key={d} tone="default">{d}</Badge>
           ))}</div> : <div className="text-sm text-text-muted">No disponible.</div>}
        </CardContent></Card>

        <Card><CardHeader><CardTitle>Estado operativo</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
          <div className="flex justify-between"><span className="text-text-muted">API</span><span>{health.data?.status ?? "No disponible"}</span></div>
          <div className="flex justify-between"><span className="text-text-muted">Base de datos</span><span>{health.data?.database ?? "No disponible"}</span></div>
          <div className="flex justify-between"><span className="text-text-muted">Provider activo</span><span>{health.data?.active_provider ?? "No disponible"}</span></div>
          <div className="flex justify-between"><span className="text-text-muted">Versión</span><span className="case-mono">{health.data?.version ?? "N/A"}</span></div>
          <div className="pt-2 text-xs text-text-dim">Solo se muestran datos devueltos por endpoints reales. No se inventan métricas históricas ni uptime.</div>
        </CardContent></Card>
      </div>
    </div>
  );
}
