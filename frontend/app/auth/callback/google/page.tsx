"use client";

export const dynamic = "force-dynamic";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sparkles, AlertCircle } from "lucide-react";

function GoogleCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loginWithGoogle } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code") || undefined;
    const email = searchParams.get("email") || undefined;
    const name = searchParams.get("name") || undefined;
    const avatar_url = searchParams.get("avatar_url") || undefined;

    const processAuth = async () => {
      try {
        await loginWithGoogle({ code, email, name, avatar_url });
        router.push("/dashboard");
      } catch (err: any) {
        setError(err.message || "Google authentication failed");
      }
    };

    processAuth();
  }, [searchParams, loginWithGoogle, router]);

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-md w-full p-6 rounded-2xl bg-card border border-destructive/40 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-destructive/20 text-destructive flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold">Authentication Failed</h2>
          <p className="text-xs text-slate-400">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="px-4 py-2 rounded-xl bg-purple-600 text-white text-xs font-semibold"
          >
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-4 text-center">
      <div className="w-12 h-12 rounded-2xl bg-purple-600/20 text-purple-400 flex items-center justify-center animate-spin">
        <Sparkles className="w-6 h-6" />
      </div>
      <h2 className="text-lg font-bold tracking-tight">Signing in with Google...</h2>
      <p className="text-xs text-slate-400">Verifying your account and preparing your studio.</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <GoogleCallbackContent />
    </Suspense>
  );
}
