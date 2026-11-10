"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { api, Project, Video, Clip, Job } from "@/lib/api";
import {
  Sparkles,
  Wand2,
  Video as VideoIcon,
  Clock,
  Play,
  Scissors,
  Layers,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sliders,
  FileText,
  Youtube,
  Link as LinkIcon,
} from "lucide-react";

export default function ProjectWorkspacePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [project, setProject] = useState<Project | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [prompt, setPrompt] = useState("");
  const [targetDuration, setTargetDuration] = useState(30);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [importingVideo, setImportingVideo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImportYoutube = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;
    setError(null);
    setImportingVideo(true);
    try {
      await api.importVideoUrl(projectId, youtubeUrl.trim());
      setYoutubeUrl("");
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to import YouTube video");
    } finally {
      setImportingVideo(false);
    }
  };

  const loadData = async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);
      if (proj.prompt) setPrompt(proj.prompt);

      const clipsRes = await api.getClips(projectId);
      setClips(clipsRes.items || []);

      // Check active jobs
      const jobs = await api.getProjectJobs(projectId);
      const running = jobs.find((j) => j.status === "running" || j.status === "pending");
      setActiveJob(running || null);
    } catch (err: any) {
      setError(err.message || "Failed to load project");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      loadData();
    }
  }, [user, authLoading, projectId]);

  // Polling for active jobs
  useEffect(() => {
    if (!activeJob) return;

    const interval = setInterval(async () => {
      try {
        const updated = await api.getJob(activeJob.id);
        setActiveJob(updated);
        if (updated.status === "completed") {
          setActiveJob(null);
          setGenerating(false);
          await loadData();
        } else if (updated.status === "failed") {
          setActiveJob(null);
          setGenerating(false);
          setError(updated.error_message || "Video processing encountered an issue");
          await loadData();
        }
      } catch (err) {
        console.error("Job poll failed", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) {
      setError("Please describe what kind of clip you want.");
      return;
    }
    setError(null);
    setGenerating(true);

    try {
      const job = await api.generateClips({
        project_id: projectId,
        prompt,
        target_duration_seconds: targetDuration,
        num_candidates: 5,
      });
      setActiveJob(job);
    } catch (err: any) {
      setError(err.message || "Failed to start clip generation");
      setGenerating(false);
    }
  };

  if (loading) {
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
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border/40">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{project?.title}</h1>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                  project?.status === "ready"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-purple-500/10 text-purple-300 border border-purple-500/20"
                }`}
              >
                {project?.status}
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              {project?.description || "Source video workspace & AI generation studio"}
            </p>
          </div>

          <button
            onClick={loadData}
            className="p-2.5 rounded-xl border border-border/60 text-slate-300 hover:bg-secondary/60 transition-colors self-start sm:self-auto"
            title="Refresh workspace"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-destructive/15 border border-destructive/30 text-destructive-foreground text-sm flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Import YouTube or Video URL bar */}
        <div className="p-4 rounded-2xl bg-secondary/30 border border-border/50 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 shrink-0">
            <Youtube className="w-4 h-4 text-rose-500" />
            Import from YouTube:
          </div>
          <form onSubmit={handleImportYoutube} className="flex-1 flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1">
              <LinkIcon className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="Paste YouTube or video link (https://www.youtube.com/watch?v=...)"
                className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-card border border-border/60 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500 font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={importingVideo || !youtubeUrl.trim()}
              className="px-4 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50 shrink-0"
            >
              {importingVideo ? "Importing..." : "Import Video"}
            </button>
          </form>
        </div>

        {/* AI Prompt Interface */}
        <div className="p-6 rounded-2xl bg-card/70 border border-border/70 backdrop-blur-xl shadow-xl space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Sparkles className="w-4 h-4 text-purple-400" />
            AI Clip Reasoning & Prompt
          </div>

          <form onSubmit={handleGenerate} className="space-y-4">
            <div className="relative">
              <textarea
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. Find the most interesting part where the speaker discusses artificial intelligence replacing jobs. Make it engaging, 30 seconds, with animated captions."
                className="w-full p-4 rounded-xl bg-secondary/50 border border-border/50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <span className="text-xs font-medium text-slate-400">Target Duration:</span>
                {[15, 30, 60, 90].map((dur) => (
                  <button
                    key={dur}
                    type="button"
                    onClick={() => setTargetDuration(dur)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      targetDuration === dur
                        ? "bg-purple-600 text-white shadow-sm"
                        : "bg-secondary/50 text-slate-400 hover:text-slate-200 border border-border/40"
                    }`}
                  >
                    {dur}s
                  </button>
                ))}
              </div>

              <button
                type="submit"
                disabled={generating || !!activeJob}
                className="px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-sm shadow-lg shadow-purple-600/20 inline-flex items-center justify-center gap-2 disabled:opacity-50 transition-all hover:scale-[1.01]"
              >
                <Wand2 className="w-4 h-4" />
                {generating || activeJob ? "Processing Clip Reasoning..." : "Generate AI Clips"}
              </button>
            </div>
          </form>

          {/* Active Job Progress Banner */}
          {activeJob && (
            <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 space-y-2 animate-pulse">
              <div className="flex items-center justify-between text-xs font-semibold text-purple-300">
                <span>{activeJob.progress_message || "Analyzing transcript and generating clips..."}</span>
                <span>{(activeJob.progress * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-purple-500 transition-all duration-500 rounded-full"
                  style={{ width: `${Math.max(10, activeJob.progress * 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Clip Candidates Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold tracking-tight">
              Generated Clip Candidates ({clips.length})
            </h2>
            <span className="text-xs text-muted-foreground">Ranked by hook & context completeness</span>
          </div>

          {clips.length === 0 ? (
            <div className="p-12 rounded-2xl border border-dashed border-border/60 bg-card/20 text-center space-y-3">
              <VideoIcon className="w-8 h-8 text-muted-foreground mx-auto" />
              <div className="text-sm font-medium text-slate-300">No clips generated yet</div>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Enter your prompt above and click &quot;Generate AI Clips&quot; to extract the best short segments.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {clips.map((clip) => {
                const breakdown = clip.score_breakdown || ({} as any);
                return (
                  <div
                    key={clip.id}
                    className="rounded-2xl border border-border/70 bg-card/60 overflow-hidden shadow-sm flex flex-col justify-between hover:border-purple-500/40 transition-all"
                  >
                    {/* Top thumbnail or preview banner */}
                    <div className="aspect-[16/9] bg-slate-900/90 relative flex items-center justify-center p-4 border-b border-border/40">
                      <div className="text-center space-y-1">
                        <div className="w-10 h-10 rounded-full bg-purple-600/20 text-purple-400 flex items-center justify-center mx-auto mb-2">
                          <Play className="w-5 h-5 ml-0.5" />
                        </div>
                        <div className="text-xs font-bold text-slate-300">
                          {clip.start_time.toFixed(1)}s → {clip.end_time.toFixed(1)}s
                        </div>
                        <div className="text-[10px] text-muted-foreground font-mono">
                          Duration: {clip.duration.toFixed(1)}s
                        </div>
                      </div>

                      <div className="absolute top-3 left-3 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-600 text-white">
                        Rank #{clip.rank}
                      </div>

                      <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        Score: {(clip.score * 100).toFixed(0)}
                      </div>
                    </div>

                    {/* Clip Body */}
                    <div className="p-5 space-y-4 flex-1 flex flex-col justify-between">
                      <div className="space-y-3">
                        <p className="text-xs text-slate-300 italic line-clamp-3 leading-relaxed">
                          &quot;{clip.transcript_text}&quot;
                        </p>

                        {/* Scores Breakdown pill */}
                        <div className="grid grid-cols-3 gap-1.5 text-[10px] bg-secondary/40 p-2 rounded-xl">
                          <div className="text-center">
                            <span className="text-muted-foreground block">Hook</span>
                            <span className="font-semibold text-emerald-400">
                              {((breakdown.hook_strength || 0.8) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="text-center">
                            <span className="text-muted-foreground block">Relevance</span>
                            <span className="font-semibold text-purple-300">
                              {((breakdown.relevance || 0.85) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="text-center">
                            <span className="text-muted-foreground block">Flow</span>
                            <span className="font-semibold text-indigo-400">
                              {((breakdown.context_completeness || 0.8) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="pt-3 border-t border-border/40 flex items-center justify-between gap-2">
                        <Link
                          href={`/editor/${clip.id}`}
                          className="flex-1 py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                        >
                          <Scissors className="w-3.5 h-3.5" />
                          Open in Editor
                        </Link>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
