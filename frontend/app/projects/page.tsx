"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { api, Project } from "@/lib/api";
import { Plus, Video, Clock, ArrowRight, Trash2 } from "lucide-react";

export default function ProjectsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchProjects = () => {
    setLoading(true);
    api
      .getProjects(1, 50)
      .then((res) => setProjects(res.items || []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      fetchProjects();
    }
  }, [user, authLoading, router]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this project?")) {
      try {
        await api.deleteProject(id);
        fetchProjects();
      } catch (err: any) {
        alert(err.message || "Failed to delete project");
      }
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">My Projects</h1>
            <p className="text-sm text-slate-400 mt-1">Manage your video clipping workflows and assets</p>
          </div>
          <Link
            href="/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-sm shadow-md transition-all hover:scale-[1.02]"
          >
            <Plus className="w-4 h-4" />
            New Project
          </Link>
        </div>

        {loading ? (
          <div className="p-12 text-center text-sm text-slate-400">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="p-16 text-center border border-dashed border-border/80 rounded-2xl bg-card/20 space-y-4">
            <Video className="w-10 h-10 text-muted-foreground mx-auto" />
            <div className="text-sm text-slate-300 font-medium">No projects found</div>
            <Link
              href="/projects/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 text-white text-xs font-semibold"
            >
              Create New Project
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((proj) => (
              <Link
                key={proj.id}
                href={`/projects/${proj.id}`}
                className="p-5 rounded-2xl bg-card/60 hover:bg-card border border-border/60 hover:border-purple-500/40 transition-all group shadow-sm flex flex-col justify-between space-y-4"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-sm group-hover:text-purple-300 transition-colors line-clamp-1">
                      {proj.title}
                    </h3>
                    <button
                      onClick={(e) => handleDelete(e, proj.id)}
                      className="text-slate-500 hover:text-rose-400 p-1 rounded transition-colors"
                      title="Delete Project"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    {proj.description || proj.prompt || "No prompt or description yet"}
                  </p>
                </div>

                <div className="pt-3 border-t border-border/40 flex items-center justify-between text-[11px] text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(proj.created_at).toLocaleDateString()}
                  </span>
                  <span className="text-purple-400 font-medium group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-0.5">
                    Open Project <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
