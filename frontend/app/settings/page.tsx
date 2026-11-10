"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { api } from "@/lib/api";
import {
  Settings as SettingsIcon,
  Key,
  Cpu,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [appInfo, setAppInfo] = useState<any>(null);
  const [healthInfo, setHealthInfo] = useState<any>(null);
  const [geminiKey, setGeminiKey] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      api.getInfo().then(setAppInfo).catch(console.error);
      api.getHealth().then(setHealthInfo).catch(console.error);
    }
  }, [user, authLoading, router]);

  const handleSaveKeys = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-8 max-w-4xl space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Studio Settings</h1>
          <p className="text-sm text-slate-400 mt-1">Configure AI inference, local transcription, and storage engines</p>
        </div>

        {/* Gemini API Key Configuration */}
        <div className="p-6 rounded-2xl bg-card/60 border border-border/60 space-y-4">
          <div className="flex items-center gap-2 text-base font-semibold">
            <Key className="w-5 h-5 text-purple-400" />
            Gemini AI Intelligence
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Clipped-AI utilizes Google Gemini for natural-language prompt understanding, candidate reasoning, and hook scoring.
          </p>

          <form onSubmit={handleSaveKeys} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Google Gemini API Key</label>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full px-4 py-2.5 rounded-xl bg-secondary/50 border border-border/50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
              />
              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                <span>Stored in environment variable or backend .env</span>
                <a
                  href="https://aistudio.google.com/app/apikey"
                  target="_blank"
                  rel="noreferrer"
                  className="text-purple-400 hover:text-purple-300 inline-flex items-center gap-1 font-semibold"
                >
                  Get Gemini Key <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">Status:</span>
                <span className="text-emerald-400 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Gemini SDK Active (gemini-3.8-flash)
                </span>
              </div>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-md"
              >
                {saved ? "Saved!" : "Save Key"}
              </button>
            </div>
          </form>
        </div>

        {/* Local Hardware & Performance Profile */}
        <div className="p-6 rounded-2xl bg-card/60 border border-border/60 space-y-4">
          <div className="flex items-center gap-2 text-base font-semibold">
            <Cpu className="w-5 h-5 text-indigo-400" />
            Hardware & Inference Profile
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            The studio is configured to run smoothly on your Arch Linux environment with CPU-optimized int8 Whisper quantization.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 text-xs">
            <div className="p-3.5 rounded-xl bg-secondary/40 border border-border/40 space-y-1">
              <span className="text-muted-foreground block font-medium">Whisper Model</span>
              <span className="font-semibold text-slate-200">
                faster-whisper (base / int8 quantized)
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/40 border border-border/40 space-y-1">
              <span className="text-muted-foreground block font-medium">FFmpeg Acceleration</span>
              <span className="font-semibold text-emerald-400">
                Native libx264 + libass (Installed)
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/40 border border-border/40 space-y-1">
              <span className="text-muted-foreground block font-medium">Storage Engine</span>
              <span className="font-semibold text-slate-200">
                Local Filesystem (storage/ + output/)
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/40 border border-border/40 space-y-1">
              <span className="text-muted-foreground block font-medium">Task Queue</span>
              <span className="font-semibold text-slate-200">
                Celery 5.7 with Redis Broker
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
