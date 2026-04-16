"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

export default function RootPage() {
  const { admin, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (admin) {
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    }
  }, [admin, isLoading, router]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <Loader2 className="animate-spin text-indigo-500" size={32} />
    </div>
  );
}
