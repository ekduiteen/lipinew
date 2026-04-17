"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import cookie from "cookie-cutter";

interface AdminUser {
  full_name: string;
  role: string;
}

interface AuthContextType {
  admin: AdminUser | null;
  isLoading: boolean;
  login: (token: string, user: AdminUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = cookie.get("ctrl_token");
    const storedUser = localStorage.getItem("ctrl_user");
    
    if (token && storedUser) {
      setAdmin(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = (token: string, user: AdminUser) => {
    // We store token in cookie for the proxy/middleware to use if needed
    cookie.set("ctrl_token", token, { path: "/" });
    localStorage.setItem("ctrl_user", JSON.stringify(user));
    setAdmin(user);
    router.push("/dashboard");
  };

  const logout = () => {
    cookie.set("ctrl_token", "", { expires: new Date(0), path: "/" });
    localStorage.removeItem("ctrl_user");
    setAdmin(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ admin, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
