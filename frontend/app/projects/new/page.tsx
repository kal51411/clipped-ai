"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { api } from "@/lib/api";
import {
  UploadCloud,
  FileVideo,
  Sparkles,
  AlertCircle,
  ArrowRight,
  Link as LinkIcon,
  Youtube,
} from "lucide-react";

export default function NewProjectPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [ingestMode, setIngestMode] = useState<"upload" | "youtube">("youtube");
  const [videoUrl, setVideoUrl] = useState("");
  const [autoGenerateShorts, setAutoGenerateShorts] = useState(true);
  const [aiPrompt, setAiPrompt] = useState("Find the most viral, engaging, and high-impact moments");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please enter a project title");
      return;
    }
    if (ingestMode === "youtube" && !videoUrl.trim()) {
      setError("Please paste a valid YouTube or video URL");
      return;
    }
    if (ingestMode === "upload" && !file) {
      setError("Please select a video file to upload");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      if (ingestMode === "youtube" && autoGenerateShorts) {
        setUploadProgress("Downloading YouTube video & starting AI pipeline...");
        const res = await api.quickYoutubeToShorts({
          url: videoUrl.trim(),
          title: title.trim(),
          prompt: aiPrompt.trim() || undefined,
          target_duration_seconds: 30,
          num_candidates: 5,
        });
        router.push(`/projects/${res.project.id}`);
        return;
      }

      setUploadProgress("Creating project...");
      const project = await api.createProject({ title, description });

      if (ingestMode === "upload" && file) {
        setUploadProgress(`Uploading video (${(file.size / (1024 * 1024)).toFixed(1)} MB)...`);
        await api.uploadVideo(project.id, file);
      } else if (ingestMode === "youtube" && videoUrl) {
        setUploadProgress("Importing video from YouTube / URL...");
        await api.importVideoUrl(project.id, videoUrl.trim());
      }

      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create project");
      setLoading(false);
      setUploadProgress(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const dropped = e.dataTransfer.files[0];
      if (dropped.type.startsWith("video/") || dropped.name.match(/\.(mp4|mov|avi|mkv|webm)$/i)) {
        setFile(dropped);
      } else {
        setError("Please upload a supported video file (MP4, MOV, MKV, WebM)");
      }
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-8 max-w-4xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Create New Project</h1>
          <p className="text-sm text-slate-400 mt-1">
            Import from YouTube or upload your source video to generate short-form clips
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-destructive/15 border border-destructive/30 text-destructive-foreground text-sm flex items-center gap-3">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="p-6 rounded-2xl bg-card/60 border border-border/60 space-y-4">
            <h2 className="text-base font-semibold">1. Project Details</h2>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Project Title</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. AI Revolution Podcast - Ep. 4"
                className="w-full px-4 py-2.5 rounded-xl bg-secondary/50 border border-border/50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Description (Optional)</label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief notes about the interview, speakers, or topics"
                className="w-full px-4 py-2.5 rounded-xl bg-secondary/50 border border-border/50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-card/60 border border-border/60 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">2. Video Ingestion</h2>
              <div className="flex items-center gap-1 bg-secondary/60 p-1 rounded-xl border border-border/50">
                <button
                  type="button"
                  onClick={() => setIngestMode("youtube")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    ingestMode === "youtube"
                      ? "bg-purple-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Youtube className="w-3.5 h-3.5 text-rose-400" />
                  YouTube / URL
                </button>
                <button
                  type="button"
                  onClick={() => setIngestMode("upload")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    ingestMode === "upload"
                      ? "bg-purple-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <UploadCloud className="w-3.5 h-3.5 text-purple-400" />
                  Upload File
                </button>
              </div>
            </div>

            {ingestMode === "youtube" ? (
              <div className="p-6 rounded-2xl bg-secondary/30 border border-border/50 space-y-3">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                  <Youtube className="w-4 h-4 text-rose-500" />
                  Paste YouTube Video Link
                </label>
                <div className="relative">
                  <LinkIcon className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="url"
                    value={videoUrl}
                    onChange={(e) => setVideoUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-card border border-border/60 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>Supports YouTube podcasts, interviews, and direct video links</span>
                  <span className="text-purple-400 font-medium">Automatic yt-dlp extraction</span>
                </div>

                <div className="pt-2 border-t border-border/40 space-y-3">
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-200">
                    <input
                      type="checkbox"
                      checked={autoGenerateShorts}
                      onChange={(e) => setAutoGenerateShorts(e.target.checked)}
                      className="w-4 h-4 rounded border-border text-purple-600 focus:ring-purple-500 bg-secondary"
                    />
                    <span>⚡ Immediately generate short-form clips after download (Recommended)</span>
                  </label>

                  {autoGenerateShorts && (
                    <div className="space-y-1 pl-6">
                      <label className="text-[11px] font-medium text-slate-400">Clip Prompt / Focus</label>
                      <input
                        type="text"
                        value={aiPrompt}
                        onChange={(e) => setAiPrompt(e.target.value)}
                        placeholder="e.g. Find the most viral, exciting moments with strong takeaways"
                        className="w-full px-3 py-2 rounded-xl bg-card/80 border border-border/50 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500 text-slate-200"
                      />
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                className={`p-8 border-2 border-dashed rounded-2xl text-center transition-all cursor-pointer flex flex-col items-center justify-center gap-3 ${
                  dragOver
                    ? "border-purple-500 bg-purple-500/10"
                    : file
                    ? "border-emerald-500/50 bg-emerald-500/5"
                    : "border-border/80 bg-card/40 hover:bg-card/70"
                }`}
                onClick={() => document.getElementById("file-input")?.click()}
              >
                <input
                  id="file-input"
                  type="file"
                  accept="video/*,.mp4,.mov,.avi,.mkv,.webm"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setFile(e.target.files[0]);
                    }
                  }}
                />

                {file ? (
                  <>
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                      <FileVideo className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="font-semibold text-sm text-slate-200">{file.name}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB • Click or drag to replace
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-12 h-12 rounded-xl bg-purple-600/10 text-purple-400 flex items-center justify-center">
                      <UploadCloud className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="font-semibold text-sm text-slate-200">
                        Click to upload or drag & drop video
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        MP4, MOV, MKV up to 2GB • Local faster-whisper will automatically transcribe.
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-5 py-2.5 rounded-xl border border-border/60 text-sm font-semibold text-slate-300 hover:bg-secondary/60 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-sm shadow-lg shadow-purple-600/20 inline-flex items-center gap-2 disabled:opacity-50 transition-all hover:scale-[1.01]"
            >
              {loading ? uploadProgress || "Processing..." : "Create & Ingest Video"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
