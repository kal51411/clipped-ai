"use client";

import React from "react";
import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  Play,
  Scissors,
  Wand2,
  Subtitles,
  Smartphone,
  Layers,
  Cpu,
  CheckCircle2,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex-1 flex flex-col">
      {/* Hero Section */}
      <section className="relative pt-20 pb-28 px-6 max-w-6xl mx-auto flex flex-col items-center text-center">
        {/* Glow backdrop */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-purple-600/15 blur-[120px] rounded-full pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium bg-purple-500/10 border border-purple-500/20 text-purple-300 mb-8 animate-pulse">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          Powered by Gemini 3.8 & faster-whisper
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight max-w-4xl leading-[1.15] mb-6">
          Turn long-form videos into{" "}
          <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-indigo-400 bg-clip-text text-transparent">
            viral vertical clips
          </span>{" "}
          with natural language
        </h1>

        <p className="text-lg sm:text-xl text-slate-400 max-w-2xl leading-relaxed mb-10">
          Upload any podcast, interview, or video. Just describe what you want, and Clipped-AI pinpoints the best moments, reframes to 9:16, generates animated captions, and delivers production-ready MP4s.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
          <Link
            href="/dashboard"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold shadow-xl shadow-purple-600/25 transition-all hover:scale-[1.02]"
          >
            Launch Studio
            <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="#how-it-works"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-secondary/80 hover:bg-secondary border border-border/60 text-slate-200 font-semibold transition-colors"
          >
            <Play className="w-4 h-4 text-purple-400" />
            See How It Works
          </a>
        </div>

        {/* Interactive Prompt Simulation Card */}
        <div className="mt-16 w-full max-w-3xl rounded-2xl border border-border/80 bg-card/80 backdrop-blur-xl p-6 shadow-2xl text-left relative overflow-hidden">
          <div className="flex items-center justify-between pb-4 border-b border-border/40 text-xs text-slate-400">
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
              Live Prompt-to-Clip Simulation
            </span>
            <span>Target: 30s Short (9:16)</span>
          </div>

          <div className="mt-4 p-4 rounded-xl bg-slate-900/90 border border-purple-500/30 flex items-center gap-3">
            <Wand2 className="w-5 h-5 text-purple-400 shrink-0" />
            <span className="text-sm text-slate-200 font-mono">
              &quot;Find the most interesting part where the speaker discusses artificial intelligence replacing jobs. Make it engaging, 30 seconds, with animated captions.&quot;
            </span>
          </div>

          <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-secondary/40 border border-border/40 text-xs">
              <div className="text-muted-foreground font-medium mb-1">Hook Score</div>
              <div className="text-emerald-400 font-bold text-sm">94/100 (Strong Question)</div>
            </div>
            <div className="p-3 rounded-lg bg-secondary/40 border border-border/40 text-xs">
              <div className="text-muted-foreground font-medium mb-1">Duration Range</div>
              <div className="text-purple-300 font-bold text-sm">00:14:20 → 00:14:51 (31s)</div>
            </div>
            <div className="p-3 rounded-lg bg-secondary/40 border border-border/40 text-xs">
              <div className="text-muted-foreground font-medium mb-1">Format Output</div>
              <div className="text-indigo-400 font-bold text-sm">1080x1920 (9:16 Vertical)</div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section id="how-it-works" className="py-20 px-6 border-t border-border/40 bg-card/20">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight mb-4">Complete AI Production Pipeline</h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Engineered with real speech-to-text models, deterministic transcript boundary scoring, and lossless FFmpeg rendering.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-card/60 border border-border/60 space-y-4">
              <div className="w-10 h-10 rounded-xl bg-purple-600/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold">1. Whisper Audio Ingestion</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Extracts clean 16kHz mono audio and runs local faster-whisper inference to generate word-level timestamps without uploading audio to third parties.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-card/60 border border-border/60 space-y-4">
              <div className="w-10 h-10 rounded-xl bg-pink-600/10 border border-pink-500/20 flex items-center justify-center text-pink-400">
                <Wand2 className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold">2. Gemini Semantic Reasoning</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Interprets user prompts using Google Gemini to extract intent, search keywords, hook strengths, and rank candidate windows based on context completeness.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-card/60 border border-border/60 space-y-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Smartphone className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold">3. 9:16 Video & Caption Engine</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Accurately trims segments with FFmpeg, centre-crops to vertical 9:16, generates stylized ASS/SRT subtitles, and burns in word-level highlights.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Built-in Video Editor Feature */}
      <section className="py-20 px-6 border-t border-border/40">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center gap-12">
          <div className="flex-1 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              Interactive Editor
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight leading-snug">
              Fine-tune every cut with our built-in video editor
            </h2>
            <p className="text-slate-400 leading-relaxed">
              Don&apos;t settle for rigid AI outputs. Clipped-AI gives you a full multi-track timeline to tweak trim points, customize caption typography and colors, adjust zoom and filters, and export in custom bitrates.
            </p>
            <ul className="space-y-3 text-sm text-slate-300">
              <li className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                Live timeline scrubbing with synchronized video preview
              </li>
              <li className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                Word-level caption highlighter with font and positioning controls
              </li>
              <li className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                Versioned editing state with reset, undo, and direct MP4 export
              </li>
            </ul>
          </div>

          <div className="flex-1 w-full rounded-2xl border border-border/80 bg-card p-6 shadow-2xl space-y-4">
            <div className="aspect-[9/16] max-h-[380px] mx-auto rounded-xl bg-slate-900 border border-border/40 relative overflow-hidden flex flex-col items-center justify-center text-center p-4">
              <div className="w-14 h-14 rounded-full bg-purple-600/30 border border-purple-500/50 flex items-center justify-center text-purple-300 mb-3">
                <Play className="w-6 h-6 ml-0.5" />
              </div>
              <span className="text-xs font-semibold text-slate-300">9:16 Canvas Preview</span>
              <div className="absolute bottom-6 left-4 right-4 bg-black/75 backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-bold text-yellow-400 border border-yellow-400/20">
                &quot;AI tools will transform how we code...&quot;
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 px-6 border-t border-border/40 text-center text-xs text-muted-foreground">
        Clipped-AI © 2026 — AI-Powered Short-Form Video Automation. All rights reserved.
      </footer>
    </div>
  );
}
