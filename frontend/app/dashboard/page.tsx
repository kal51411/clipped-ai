"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { api, Project } from "@/lib/api";
import {
  FolderKanban,
  Plus,
  Video as VideoIcon,
  Sparkles,
  Clock,
  ArrowRight,
  TrendingUp,
  SlidersHorizontal,
  Youtube,
  Zap,
  Wand2,
  AlertCircle,
  Link as LinkIcon,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // Quick YouTube to Shorts State
  const [ytUrl, setYtUrl] = useState("");
  const [ytPrompt, setYtPrompt] = useState("Find the most viral, engaging, and high-impact moments");
  const [ytLoading, setYtLoading] = useState(false);
  const [ytError, setYtError] = useState<string | null>(null);

  const promptPresets = [
    { label: "🔥 Viral Moments", prompt: "Find the most viral, engaging, and high-impact moments" },
    { label: "💡 Key Insights", prompt: "Extract the top tips, wisdom, and actionable lessons" },
    { label: "🎙️ Best Q&A", prompt: "Find the best question and answer exchanges with strong punchlines" },
    { label: "😂 Funniest Clips", prompt: "Find the funniest, most entertaining, and lighthearted moments" },
  ];

  const handleQuickYoutube = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ytUrl.trim()) {
      setYtError("Please enter a valid YouTube video link");
      return;
    }
    setYtError(null);
    setYtLoading(true);

    try {
      const res = await api.quickYoutubeToShorts({
        url: ytUrl.trim(),
        prompt: ytPrompt.trim() || undefined,
        target_duration_seconds: 30,
        num_candidates: 5,
      });
      router.push(`/projects/${res.project.id}`);
    } catch (err: any) {
      setYtError(err.message || "Failed to process YouTube link");
      setYtLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }

    if (user) {
      api
        .getProjects(1, 10)
        .then((res) => setProjects(res.items || []))
        .catch((err) => console.error("Failed to load projects", err))
        .finally(() => setLoading(false));
    }
  }, [user, authLoading, router]);

  if (authLoading || (!user && loading)) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-8 space-y-8">
        {/* Welcome Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Welcome, {user?.full_name || user?.email?.split("@")[0]}
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Create and manage AI-generated vertical video projects
            </p>
          </div>
          <Link
            href="/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-sm shadow-lg shadow-purple-600/20 transition-all hover:scale-[1.02]"
          >
            <Plus className="w-4 h-4" />
            New Project
          </Link>
        </div>

        {/* ⚡ Quick YouTube to Shorts Magic Ingestion Card */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-purple-900/40 via-card/90 to-background border border-purple-500/30 p-6 md:p-8 shadow-2xl backdrop-blur-xl space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-rose-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-rose-500/25">
                <Youtube className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold flex items-center gap-2">
                  Paste YouTube Link → Get AI Shorts
                  <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-extrabold bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full">
                    Auto-Cut
                  </span>
                </h2>
                <p className="text-xs text-slate-400">
                  Paste any YouTube interview, podcast, or video URL. We will download, transcribe, detect highlights, and format 9:16 vertical shorts automatically.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground self-start sm:self-auto">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Full Pipeline • Powered by Gemini 3.8</span>
            </div>
          </div>

          {ytError && (
            <div className="p-3.5 rounded-xl bg-destructive/15 border border-destructive/30 text-destructive-foreground text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{ytError}</span>
            </div>
          )}

          <form onSubmit={handleQuickYoutube} className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <LinkIcon className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="url"
                  required
                  value={ytUrl}
                  onChange={(e) => setYtUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
                  className="w-full pl-10 pr-4 py-3 rounded-2xl bg-secondary/60 border border-border/80 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono transition-all"
                />
              </div>
              <button
                type="submit"
                disabled={ytLoading}
                className="px-6 py-3 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-xl shadow-purple-600/30 inline-flex items-center justify-center gap-2 transition-all hover:scale-[1.02] disabled:opacity-50 shrink-0"
              >
                {ytLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Processing YouTube Video...</span>
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" />
                    <span>Generate Shorts Now</span>
                  </>
                )}
              </button>
            </div>

            {/* Prompt presets */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">What clip style or topic should we focus on?</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {promptPresets.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => setYtPrompt(preset.prompt)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                      ytPrompt === preset.prompt
                        ? "bg-purple-600 text-white shadow-sm"
                        : "bg-secondary/40 border border-border/60 text-slate-300 hover:bg-secondary/80 hover:text-white"
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={ytPrompt}
                onChange={(e) => setYtPrompt(e.target.value)}
                placeholder="Custom prompt e.g.: Find the moment where the guest talks about..."
                className="w-full px-4 py-2 rounded-xl bg-secondary/30 border border-border/40 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500 text-slate-200"
              />
            </div>
          </form>
        </div>

        {/* Quick Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="p-5 rounded-2xl bg-card/60 border border-border/60 space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
              <span>Total Projects</span>
              <FolderKanban className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold">{projects.length}</div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-emerald-400" />
              Active creation workspace
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-card/60 border border-border/60 space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
              <span>AI Pipeline Status</span>
              <Sparkles className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400">Ready</div>
            <div className="text-xs text-slate-400">Gemini 3.8 & faster-whisper online</div>
          </div>

          <div className="p-5 rounded-2xl bg-card/60 border border-border/60 space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
              <span>Aspect Ratio</span>
              <VideoIcon className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-2xl font-bold">9:16 Shorts</div>
            <div className="text-xs text-slate-400">Optimized for Reels & TikTok</div>
          </div>
        </div>

        {/* Recent Projects Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold tracking-tight">Recent Projects</h2>
            <Link href="/projects" className="text-xs font-semibold text-purple-400 hover:text-purple-300">
              View all
            </Link>
          </div>

          {loading ? (
            <div className="p-12 text-center text-sm text-slate-400">Loading your projects...</div>
          ) : projects.length === 0 ? (
            <div className="p-12 rounded-2xl border border-dashed border-border/80 bg-card/30 text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-secondary/50 border border-border/40 mx-auto flex items-center justify-center text-purple-400">
                <VideoIcon className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-base">No projects yet</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                  Upload an interview or podcast to generate your first set of AI shorts.
                </p>
              </div>
              <Link
                href="/projects/new"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs shadow-md transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Create First Project
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map((proj) => (
                <Link
                  key={proj.id}
                  href={`/projects/${proj.id}`}
                  className="p-5 rounded-2xl bg-card/60 hover:bg-card border border-border/60 hover:border-purple-500/40 transition-all group shadow-sm hover:shadow-lg hover:shadow-purple-500/5 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-sm group-hover:text-purple-300 transition-colors line-clamp-1">
                      {proj.title}
                    </h3>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide uppercase ${
                        proj.status === "ready"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : proj.status === "processing"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-slate-500/10 text-slate-400 border border-slate-500/20"
                      }`}
                    >
                      {proj.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2">
                    {proj.description || proj.prompt || "No description provided."}
                  </p>

                  <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(proj.created_at).toLocaleDateString()}
                    </span>
                    <span className="text-purple-400 font-medium group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-0.5">
                      Open <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
