"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  UploadCloud,
  Sliders,
  Settings,
  HelpCircle,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "My Projects", href: "/projects", icon: FolderKanban },
    { label: "New Project", href: "/projects/new", icon: UploadCloud },
    { label: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-border/60 bg-card/40 flex flex-col justify-between p-4 shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Workspace
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? "bg-purple-600/15 text-purple-300 border border-purple-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-100 hover:bg-secondary/40"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-purple-400" : "text-slate-400"}`} />
              {item.label}
            </Link>
          );
        })}
      </div>

      <div className="p-3 rounded-xl bg-gradient-to-b from-purple-950/20 to-slate-900/60 border border-purple-500/10 text-xs text-slate-400 space-y-2">
        <div className="font-semibold text-slate-200 flex items-center gap-1.5">
          <HelpCircle className="w-3.5 h-3.5 text-purple-400" />
          Pro Tip
        </div>
        <p className="leading-relaxed">
          Provide specific instructions like <span className="text-purple-300">&quot;highlight the 30-second controversy&quot;</span> for optimal AI reasoning.
        </p>
      </div>
    </aside>
  );
}
