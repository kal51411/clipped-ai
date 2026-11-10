"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Film, User as UserIcon, LogOut, Sparkles } from "lucide-react";

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-border/60 bg-card/60 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg tracking-tight">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-purple-500/20">
            <Film className="w-5 h-5" />
          </div>
          <span className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Clipped<span className="text-purple-400">.AI</span>
          </span>
        </Link>
        <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20">
          <Sparkles className="w-3 h-3 mr-1 text-purple-400" />
          v2.0 Pro
        </span>
      </div>

      <div className="flex items-center gap-4">
        {user ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/50 border border-border/40 text-sm">
              <UserIcon className="w-4 h-4 text-purple-400" />
              <span className="text-slate-200 font-medium">{user.full_name || user.email}</span>
            </div>
            <button
              onClick={logout}
              className="p-2 text-muted-foreground hover:text-white hover:bg-secondary/60 rounded-lg transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-slate-300 hover:text-white px-3 py-2 rounded-lg transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="text-sm font-medium bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg shadow-lg shadow-purple-600/20 transition-all hover:scale-[1.02]"
            >
              Get Started
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
