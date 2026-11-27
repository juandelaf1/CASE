import { cn } from "@/lib/utils";
import React from "react";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("case-panel", className)} {...props} />;
}
export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4 border-b border-border", className)} {...props} />;
}
export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-sm font-semibold tracking-wide text-text", className)} {...props} />;
}
export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5", className)} {...props} />;
}
export function Badge({ className, tone="default", ...props }: React.HTMLAttributes<HTMLSpanElement> & {tone?: "default"|"teal"|"warn"|"crit"|"ok"}) {
  const tones = {
    default: "bg-surface-3 text-text-muted border-border",
    teal: "bg-teal-soft text-teal border-teal/20",
    warn: "bg-warning-soft text-warning border-warning/20",
    crit: "bg-critical-soft text-critical border-critical/20",
    ok: "bg-success-soft text-success border-success/20",
  } as const;
  return <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium", tones[tone], className)} {...props} />;
}
export function Button({ className, variant="primary", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & {variant?: "primary"|"secondary"|"danger"|"ghost"}) {
  const v = {
    primary: "bg-teal text-[#0b141d] hover:bg-[#33b8b0]",
    secondary: "bg-surface-2 text-text hover:bg-surface-3 border border-border",
    danger: "bg-critical-soft text-critical border border-critical/20 hover:bg-critical/20",
    ghost: "text-text-muted hover:text-text hover:bg-surface-2",
  }[variant];
  return <button className={cn("inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none", v, className)} {...props} />;
}
export const inputClass = "w-full rounded-lg border border-border bg-[#111a27] px-3 py-2 text-sm text-text placeholder:text-text-dim focus:outline-none focus:ring-2 focus:ring-teal/40";
export const labelClass = "mb-1.5 block text-xs font-medium uppercase tracking-wide text-text-muted";
