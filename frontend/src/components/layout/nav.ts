import { LayoutDashboard, FlaskConical, ShieldCheck, FolderOpen, ScrollText, Globe, Radar, Activity, Settings, type LucideIcon } from "lucide-react";

export type NavItem = { href?: string; label: string; icon: LucideIcon; available: boolean; note?: string };
export type NavGroup = { title: string; items: NavItem[] };

export const navGroups: NavGroup[] = [
  { title: "Operate", items: [
    { href: "/overview", label: "Overview", icon: LayoutDashboard, available: true },
    { href: "/decision-workspace", label: "Decision Workspace", icon: FlaskConical, available: true },
    { href: "/human-review", label: "Human Review", icon: ShieldCheck, available: true },
  ]},
  { title: "Investigate", items: [
    { href: "/cases", label: "Cases", icon: FolderOpen, available: false, note: "Phase 2" },
    { href: "/audit", label: "Audit Trail", icon: ScrollText, available: false, note: "Phase 2" },
  ]},
  { title: "Intelligence", items: [
    { href: "/domains", label: "Domain Intelligence", icon: Globe, available: false, note: "Phase 2" },
    { href: "/seismic", label: "Seismic Intelligence", icon: Radar, available: false, note: "Phase 2" },
  ]},
  { title: "System", items: [
    { href: "/reliability", label: "Reliability & Providers", icon: Activity, available: false, note: "Phase 2" },
    { href: "/settings", label: "Settings", icon: Settings, available: false, note: "Phase 2" },
  ]},
];
