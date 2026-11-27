"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, Shield, ChevronRight } from "lucide-react";
import { navGroups } from "./nav";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="lg:hidden flex items-center justify-between border-b border-border bg-surface px-4 py-3">
        <div className="flex items-center gap-2"><Shield className="h-5 w-5 text-teal" /><span className="font-semibold tracking-wide">CASE</span></div>
        <button onClick={() => setOpen(v=>!v)} className="rounded-md border border-border p-2 text-text-muted hover:text-text" aria-label="Toggle menu">
          {open ? <X className="h-5 w-5"/> : <Menu className="h-5 w-5"/>}
        </button>
      </div>
      <div className="flex">
        <aside className={cn("fixed inset-y-0 left-0 z-40 w-72 border-r border-border bg-[#111a27] px-4 py-5 transition-transform lg:static lg:translate-x-0", open ? "translate-x-0" : "-translate-x-full")}>
          <div className="mb-8 flex items-center gap-3 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-soft text-teal"><Shield className="h-5 w-5"/></div>
            <div>
              <div className="text-sm font-semibold tracking-[0.18em] text-text">CASE</div>
              <div className="text-[11px] tracking-wide text-text-muted">HYBRID INTELLIGENCE PLATFORM</div>
            </div>
          </div>
          <nav className="space-y-6">
            {navGroups.map(group => (
              <div key={group.title}>
                <div className="px-2 pb-2 text-[11px] font-medium uppercase tracking-[0.14em] text-text-dim">{group.title}</div>
                <div className="space-y-1">
                  {group.items.map(item => {
                    const Icon = item.icon;
                    const active = item.href ? pathname === item.href : false;
                    if (!item.available || !item.href) {
                      return (
                        <div key={item.label} className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-text-dim/60 cursor-not-allowed">
                          <Icon className="h-4 w-4" />
                          <span className="flex-1">{item.label}</span>
                          {item.note && <span className="text-[10px] border border-border rounded px-1.5 py-0.5">{item.note}</span>}
                        </div>
                      );
                    }
                    return (
                      <Link key={item.href} href={item.href} onClick={() => setOpen(false)}
                        className={cn("flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors", active ? "bg-teal-soft text-teal" : "text-text-muted hover:bg-surface hover:text-text")}>
                        <Icon className="h-4 w-4" />
                        <span className="flex-1">{item.label}</span>
                        {active && <ChevronRight className="h-4 w-4 opacity-60" />}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>
          <div className="absolute bottom-4 left-4 right-4 rounded-lg border border-border bg-surface/60 p-3 text-[11px] text-text-muted">
            <div className="font-medium text-text">Operational Decision Support</div>
            <div>LLM propone. CASE valida y gobierna.</div>
          </div>
        </aside>
        {open && <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={()=>setOpen(false)} />}
        <main className="min-h-screen flex-1 lg:ml-0"><div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">{children}</div></main>
      </div>
    </div>
  );
}
