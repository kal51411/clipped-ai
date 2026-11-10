"use client";

import React, { useEffect, useState, useRef, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, Clip, EditingProject } from "@/lib/api";
import {
  Play,
  Pause,
  RotateCcw,
  Undo2,
  Redo2,
  Save,
  Download,
  Scissors,
  ZoomIn,
  ZoomOut,
  Type,
  Palette,
  Sparkles,
  Sliders,
  Volume2,
  VolumeX,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Eye,
  Film,
} from "lucide-react";

export default function VideoEditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const clipId = resolvedParams.id;
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [clip, setClip] = useState<Clip | null>(null);
  const [editingProject, setEditingProject] = useState<EditingProject | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30);
  const [isMuted, setIsMuted] = useState(false);
  const [timelineZoom, setTimelineZoom] = useState(1);
  const [activeTab, setActiveTab] = useState<"captions" | "effects" | "export">("captions");

  // Selected caption index for editing
  const [selectedCaptionIdx, setSelectedCaptionIdx] = useState<number>(0);

  // Timeline / Editor State
  const [timeline, setTimeline] = useState<any>({
    total_duration: 30,
    aspect_ratio: "9:16",
    tracks: [],
    captions: [],
    effects: {
      zoom_level: 1.0,
      pan_x: 0,
      pan_y: 0,
      brightness: 1.0,
      contrast: 1.0,
      saturation: 1.0,
      filter_preset: "normal",
      transition_in: "fade",
      transition_out: "none",
    },
  });

  // Undo / Redo stacks
  const [history, setHistory] = useState<any[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Load clip and editor state
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }

    const init = async () => {
      try {
        const c = await api.getClip(clipId);
        setClip(c);
        const dur = c.duration || c.end_time - c.start_time;
        setDuration(dur);

        const ep = await api.getEditingProject(clipId);
        setEditingProject(ep);

        if (ep.timeline_data) {
          setTimeline(ep.timeline_data);
          setHistory([ep.timeline_data]);
          setHistoryIndex(0);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load clip in editor");
      } finally {
        setLoading(false);
      }
    };

    if (user) init();
  }, [user, authLoading, clipId]);

  // Push state to undo stack
  const updateTimelineWithHistory = (newTimeline: any) => {
    const updatedHistory = history.slice(0, historyIndex + 1);
    updatedHistory.push(newTimeline);
    setHistory(updatedHistory);
    setHistoryIndex(updatedHistory.length - 1);
    setTimeline(newTimeline);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      const prev = history[historyIndex - 1];
      setHistoryIndex(historyIndex - 1);
      setTimeline(prev);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const next = history[historyIndex + 1];
      setHistoryIndex(historyIndex + 1);
      setTimeline(next);
    }
  };

  // Current active caption based on playhead
  const currentCaption = timeline.captions?.find(
    (c: any) => currentTime >= c.start_time && currentTime <= c.end_time
  );

  const togglePlayback = async () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      try {
        await video.play();
      } catch (err) {
        setError("The clip could not start playing. Check that the rendered video is available.");
      }
    } else {
      video.pause();
    }
  };

  const seekTo = (time: number) => {
    const nextTime = Math.max(0, Math.min(duration, time));
    if (videoRef.current) videoRef.current.currentTime = nextTime;
    setCurrentTime(nextTime);
  };

  // Save changes to backend
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateEditingProject(clipId, {
        timeline_data: timeline,
      });
      setEditingProject(updated);
    } catch (err: any) {
      setError(err.message || "Failed to save project edits");
    } finally {
      setSaving(false);
    }
  };

  // Reset changes
  const handleReset = async () => {
    if (confirm("Reset all edits to original AI defaults?")) {
      try {
        const resetProj = await api.resetEditingProject(clipId);
        setEditingProject(resetProj);
        setTimeline(resetProj.timeline_data);
        updateTimelineWithHistory(resetProj.timeline_data);
      } catch (err: any) {
        setError(err.message || "Failed to reset project");
      }
    }
  };

  // Export video
  const handleExport = async () => {
    setExporting(true);
    setError(null);
    setExportSuccess(null);
    try {
      await handleSave();
      const exportJob = await api.exportClip(clipId, {
        format: "mp4",
        quality: "high",
        include_captions: true,
      });
      setExportSuccess(`Export job queued successfully! Job ID: ${exportJob.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to export video");
    } finally {
      setExporting(false);
    }
  };

  // Effects Filter Style Generator
  const getFilterStyle = () => {
    const fx = timeline.effects || {};
    const filters: string[] = [
      `brightness(${fx.brightness || 1})`,
      `contrast(${fx.contrast || 1})`,
      `saturate(${fx.saturation || 1})`,
    ];

    if (fx.filter_preset === "cinematic") {
      filters.push("contrast(1.2) saturate(1.1) sepia(0.15)");
    } else if (fx.filter_preset === "vibrant") {
      filters.push("saturate(1.4) contrast(1.1)");
    } else if (fx.filter_preset === "warm") {
      filters.push("sepia(0.3) saturate(1.2)");
    } else if (fx.filter_preset === "cool") {
      filters.push("hue-rotate(180deg) saturate(0.9)");
    } else if (fx.filter_preset === "b&w") {
      filters.push("grayscale(1)");
    }

    return {
      filter: filters.join(" "),
      transform: `scale(${fx.zoom_level || 1}) translate(${fx.pan_x || 0}px, ${fx.pan_y || 0}px)`,
      transition: "transform 0.15s ease-out, filter 0.15s ease-out",
    };
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-background h-screen overflow-hidden">
      {/* Top Action Bar */}
      <div className="h-14 border-b border-border/60 bg-card/70 px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-secondary/60 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm">Clip Studio</span>
              <span className="text-xs px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-300 border border-purple-500/20 font-mono">
                9:16
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleUndo}
            disabled={historyIndex <= 0}
            className="p-2 rounded-lg text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
            title="Undo"
          >
            <Undo2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1}
            className="p-2 rounded-lg text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
            title="Redo"
          >
            <Redo2 className="w-4 h-4" />
          </button>
          <div className="w-px h-4 bg-border/60 mx-1" />
          <button
            onClick={handleReset}
            className="px-3 py-1.5 rounded-lg border border-border/60 text-xs font-medium text-slate-300 hover:bg-secondary/60 transition-colors inline-flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3.5 py-1.5 rounded-lg bg-secondary/80 hover:bg-secondary border border-border/80 text-xs font-semibold text-white inline-flex items-center gap-1.5 transition-all shadow-sm"
          >
            <Save className="w-3.5 h-3.5 text-purple-400" />
            {saving ? "Saving..." : "Save Project"}
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white inline-flex items-center gap-1.5 shadow-md shadow-purple-600/20 transition-all hover:scale-[1.02]"
          >
            <Download className="w-3.5 h-3.5" />
            {exporting ? "Exporting..." : "Export Video"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-destructive/20 border-b border-destructive/40 px-6 py-2 text-xs text-destructive-foreground flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold">×</button>
        </div>
      )}

      {exportSuccess && (
        <div className="bg-emerald-500/15 border-b border-emerald-500/30 px-6 py-2 text-xs text-emerald-400 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {exportSuccess}
          </span>
          <button onClick={() => setExportSuccess(null)} className="font-bold">×</button>
        </div>
      )}

      {/* Main Workspace (Preview + Inspector Panels) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: 9:16 Video Player Preview */}
        <div className="flex-1 bg-slate-950 flex flex-col items-center justify-center p-6 relative select-none">
          {/* Vertical 9:16 Canvas Box */}
          <div className="w-[310px] h-[550px] rounded-2xl bg-slate-900 border-2 border-border/80 shadow-2xl relative overflow-hidden flex flex-col justify-between">
            {clip?.public_url ? (
              <video
                ref={videoRef}
                src={clip.public_url}
                poster={clip.public_url.replace(/\.mp4$/, "_thumb.jpg")}
                className="absolute inset-0 h-full w-full object-cover"
                style={getFilterStyle()}
                preload="metadata"
                onLoadedMetadata={(event) => {
                  const mediaDuration = event.currentTarget.duration;
                  if (Number.isFinite(mediaDuration)) setDuration(mediaDuration);
                }}
                onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onEnded={() => {
                  setIsPlaying(false);
                  seekTo(0);
                }}
              />
            ) : (
              <div className="absolute inset-0 bg-gradient-to-b from-indigo-950 via-slate-900 to-purple-950 flex flex-col items-center justify-center p-6 text-center">
                <Film className="w-16 h-16 text-purple-400/40 mb-3" />
                <div className="text-xs font-bold text-slate-300 max-w-[200px]">
                  {clip?.status === "rendering" ? "Rendering clip..." : "Rendered video is unavailable"}
                </div>
              </div>
            )}

            {/* Live Subtitle Overlay */}
            {currentCaption && (
              <div
                className={`absolute left-4 right-4 z-20 pointer-events-none transition-all ${
                  currentCaption.position === "top"
                    ? "top-10"
                    : currentCaption.position === "center"
                    ? "top-1/2 -translate-y-1/2"
                    : "bottom-12"
                }`}
              >
                <div
                  className="px-3 py-2 rounded-xl text-center shadow-2xl backdrop-blur-sm"
                  style={{
                    fontFamily: currentCaption.font_family || "Inter",
                    fontSize: `${currentCaption.font_size || 24}px`,
                    color: currentCaption.font_color || "#FFFFFF",
                    backgroundColor: currentCaption.background_color || "rgba(0,0,0,0.75)",
                  }}
                >
                  {currentCaption.text}
                </div>
              </div>
            )}

            {/* Bottom Play Overlay Controls */}
            <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between z-30 px-2 py-1 rounded-lg bg-black/60 backdrop-blur-md text-xs">
              <span className="font-mono text-[10px] text-slate-300">
                {Math.floor(currentTime / 60)}:
                {Math.floor(currentTime % 60).toString().padStart(2, "0")}
              </span>
              <span className="text-[10px] font-semibold text-purple-400">9:16 Canvas</span>
            </div>
          </div>

          {/* Transport Controls beneath Preview */}
          <div className="mt-4 flex items-center gap-4 bg-card/60 backdrop-blur-md px-6 py-2 rounded-2xl border border-border/60">
            <button
              onClick={() => seekTo(0)}
              className="p-1.5 text-slate-400 hover:text-white transition-colors"
              title="Return to Start"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={togglePlayback}
              className="w-10 h-10 rounded-full bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center shadow-lg shadow-purple-600/25 transition-transform hover:scale-105"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
            </button>
            <button
              onClick={() => {
                setIsMuted(!isMuted);
                if (videoRef.current) videoRef.current.muted = !isMuted;
              }}
              className="p-1.5 text-slate-400 hover:text-white transition-colors"
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Right: Inspector Sidebar Tabs (Captions, Effects, Export) */}
        <div className="w-80 border-l border-border/60 bg-card/50 flex flex-col shrink-0">
          {/* Tab Switcher */}
          <div className="flex border-b border-border/60">
            <button
              onClick={() => setActiveTab("captions")}
              className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors border-b-2 ${
                activeTab === "captions"
                  ? "border-purple-500 text-purple-300 bg-purple-500/5"
                  : "border-transparent text-slate-400 hover:text-white"
              }`}
            >
              <Type className="w-3.5 h-3.5" />
              Captions
            </button>
            <button
              onClick={() => setActiveTab("effects")}
              className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors border-b-2 ${
                activeTab === "effects"
                  ? "border-purple-500 text-purple-300 bg-purple-500/5"
                  : "border-transparent text-slate-400 hover:text-white"
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              Effects
            </button>
            <button
              onClick={() => setActiveTab("export")}
              className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors border-b-2 ${
                activeTab === "export"
                  ? "border-purple-500 text-purple-300 bg-purple-500/5"
                  : "border-transparent text-slate-400 hover:text-white"
              }`}
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
          </div>

          {/* Tab Contents */}
          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {activeTab === "captions" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Captions Track ({timeline.captions?.length || 0})
                  </span>
                </div>

                {/* Selected Caption Text Editor */}
                {timeline.captions && timeline.captions[selectedCaptionIdx] && (
                  <div className="p-4 rounded-xl bg-secondary/40 border border-border/50 space-y-3">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>Edit Active Caption</span>
                      <span>
                        {timeline.captions[selectedCaptionIdx].start_time.toFixed(1)}s -{" "}
                        {timeline.captions[selectedCaptionIdx].end_time.toFixed(1)}s
                      </span>
                    </div>

                    <textarea
                      rows={2}
                      value={timeline.captions[selectedCaptionIdx].text}
                      onChange={(e) => {
                        const newCaps = [...timeline.captions];
                        newCaps[selectedCaptionIdx].text = e.target.value;
                        updateTimelineWithHistory({ ...timeline, captions: newCaps });
                      }}
                      className="w-full p-2.5 rounded-lg bg-card border border-border/60 text-xs focus:ring-1 focus:ring-purple-500 focus:outline-none"
                    />

                    {/* Font & Style Controls */}
                    <div className="space-y-2 pt-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Font Size:</span>
                        <span className="font-mono text-purple-300">
                          {timeline.captions[selectedCaptionIdx].font_size || 24}px
                        </span>
                      </div>
                      <input
                        type="range"
                        min="16"
                        max="48"
                        value={timeline.captions[selectedCaptionIdx].font_size || 24}
                        onChange={(e) => {
                          const newCaps = [...timeline.captions];
                          newCaps[selectedCaptionIdx].font_size = parseInt(e.target.value);
                          updateTimelineWithHistory({ ...timeline, captions: newCaps });
                        }}
                        className="w-full accent-purple-500"
                      />
                    </div>

                    <div className="space-y-2">
                      <span className="text-xs text-slate-400 block">Position</span>
                      <div className="grid grid-cols-3 gap-1.5">
                        {["top", "center", "bottom"].map((pos) => (
                          <button
                            key={pos}
                            onClick={() => {
                              const newCaps = [...timeline.captions];
                              newCaps[selectedCaptionIdx].position = pos;
                              updateTimelineWithHistory({ ...timeline, captions: newCaps });
                            }}
                            className={`py-1 rounded text-[11px] font-semibold uppercase ${
                              timeline.captions[selectedCaptionIdx].position === pos
                                ? "bg-purple-600 text-white"
                                : "bg-card border border-border/40 text-slate-400"
                            }`}
                          >
                            {pos}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Caption List */}
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {timeline.captions?.map((cap: any, idx: number) => (
                    <div
                      key={cap.id || idx}
                      onClick={() => {
                        setSelectedCaptionIdx(idx);
                        seekTo(cap.start_time);
                      }}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                        selectedCaptionIdx === idx
                          ? "bg-purple-600/15 border-purple-500/50 text-purple-200"
                          : "bg-card/40 border-border/40 text-slate-400 hover:bg-card/80"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                        <span>Segment #{idx + 1}</span>
                        <span>{cap.start_time.toFixed(1)}s</span>
                      </div>
                      <div className="line-clamp-2">{cap.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "effects" && (
              <div className="space-y-5">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                  Video Effects & Canvas
                </span>

                {/* Zoom Level */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Zoom Canvas:</span>
                    <span className="font-mono text-purple-300">
                      {(timeline.effects?.zoom_level || 1).toFixed(1)}x
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="2.5"
                    step="0.1"
                    value={timeline.effects?.zoom_level || 1}
                    onChange={(e) => {
                      const fx = { ...timeline.effects, zoom_level: parseFloat(e.target.value) };
                      updateTimelineWithHistory({ ...timeline, effects: fx });
                    }}
                    className="w-full accent-purple-500"
                  />
                </div>

                {/* Brightness */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Brightness:</span>
                    <span className="font-mono text-purple-300">
                      {(timeline.effects?.brightness || 1).toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="1.5"
                    step="0.05"
                    value={timeline.effects?.brightness || 1}
                    onChange={(e) => {
                      const fx = { ...timeline.effects, brightness: parseFloat(e.target.value) };
                      updateTimelineWithHistory({ ...timeline, effects: fx });
                    }}
                    className="w-full accent-purple-500"
                  />
                </div>

                {/* Filter Presets */}
                <div className="space-y-2">
                  <span className="text-xs text-slate-300 block">Color Filter</span>
                  <div className="grid grid-cols-2 gap-2">
                    {["normal", "cinematic", "vibrant", "warm", "cool", "b&w"].map((f) => (
                      <button
                        key={f}
                        onClick={() => {
                          const fx = { ...timeline.effects, filter_preset: f };
                          updateTimelineWithHistory({ ...timeline, effects: fx });
                        }}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold capitalize border transition-all ${
                          timeline.effects?.filter_preset === f
                            ? "bg-purple-600 text-white border-purple-500"
                            : "bg-secondary/40 border-border/40 text-slate-400 hover:text-white"
                        }`}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "export" && (
              <div className="space-y-5">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                  Export Parameters
                </span>

                <div className="p-4 rounded-xl bg-secondary/40 border border-border/50 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Target Canvas:</span>
                    <span className="font-semibold text-slate-200">1080x1920 (9:16 Vertical)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Duration:</span>
                    <span className="font-semibold text-purple-300">{duration.toFixed(1)}s</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Burned Captions:</span>
                    <span className="font-semibold text-emerald-400">Enabled (ASS styled)</span>
                  </div>
                </div>

                <button
                  onClick={handleExport}
                  disabled={exporting}
                  className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/25 flex items-center justify-center gap-2 transition-all hover:scale-[1.01]"
                >
                  <Download className="w-4 h-4" />
                  {exporting ? "Starting Render Job..." : "Render Final Video"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Timeline Control Panel */}
      <div className="h-48 border-t border-border/60 bg-card/80 backdrop-blur-xl flex flex-col shrink-0 select-none">
        {/* Timeline Toolbar */}
        <div className="h-10 border-b border-border/40 px-6 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-4">
            <span className="font-mono text-purple-300 font-semibold">
              {currentTime.toFixed(2)}s / {duration.toFixed(2)}s
            </span>
            <div className="w-px h-4 bg-border/60" />
            <button
              onClick={() => {
                alert(`Split point created at ${currentTime.toFixed(2)}s`);
              }}
              className="inline-flex items-center gap-1 hover:text-white transition-colors"
            >
              <Scissors className="w-3.5 h-3.5 text-purple-400" />
              Split
            </button>
          </div>

          <div className="flex items-center gap-3">
            <ZoomOut
              className="w-4 h-4 cursor-pointer hover:text-white"
              onClick={() => setTimelineZoom(Math.max(0.5, timelineZoom - 0.25))}
            />
            <span className="font-mono text-[11px]">{timelineZoom}x</span>
            <ZoomIn
              className="w-4 h-4 cursor-pointer hover:text-white"
              onClick={() => setTimelineZoom(Math.min(3, timelineZoom + 0.25))}
            />
          </div>
        </div>

        {/* Tracks Area */}
        <div className="flex-1 p-4 overflow-x-auto relative flex flex-col justify-center space-y-3">
          {/* Scrubber / Playhead Track */}
          <div
            className="relative h-12 bg-secondary/30 rounded-xl border border-border/40 overflow-hidden cursor-pointer"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const clickX = e.clientX - rect.left;
              const ratio = clickX / rect.width;
              seekTo(Math.max(0, Math.min(duration, ratio * duration)));
            }}
          >
            {/* Base Video Bar */}
            <div className="absolute inset-y-1.5 left-2 right-2 rounded-lg bg-indigo-900/60 border border-indigo-500/40 flex items-center px-3 text-[11px] font-semibold text-indigo-200">
              <Film className="w-3.5 h-3.5 mr-2 shrink-0 text-indigo-400" />
              Video Track (9:16 Centre Crop)
            </div>

            {/* Playhead Needle */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-rose-500 shadow-md shadow-rose-500 z-30 pointer-events-none"
              style={{
                left: `${(currentTime / duration) * 100}%`,
              }}
            >
              <div className="w-3 h-3 bg-rose-500 rounded-full -ml-[5px] -mt-0.5 shadow-sm" />
            </div>
          </div>

          {/* Captions Track Blocks */}
          <div className="h-10 bg-secondary/20 rounded-xl border border-border/30 relative flex items-center px-2 overflow-hidden">
            <span className="text-[10px] text-muted-foreground mr-2 font-mono">Captions</span>
            {timeline.captions?.map((cap: any, idx: number) => {
              const startPct = (cap.start_time / duration) * 100;
              const widthPct = Math.max(2, ((cap.end_time - cap.start_time) / duration) * 100);
              const isSelected = selectedCaptionIdx === idx;

              return (
                <div
                  key={cap.id || idx}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedCaptionIdx(idx);
                    seekTo(cap.start_time);
                  }}
                  className={`absolute top-1 bottom-1 rounded-md px-2 flex items-center text-[10px] font-medium truncate cursor-pointer transition-all ${
                    isSelected
                      ? "bg-purple-600 text-white shadow-md z-10 border border-purple-300"
                      : "bg-purple-950/60 text-purple-200 border border-purple-500/30 hover:bg-purple-900/80"
                  }`}
                  style={{
                    left: `${startPct}%`,
                    width: `${widthPct}%`,
                  }}
                  title={cap.text}
                >
                  {cap.text}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
