import { redirect } from "next/navigation";

// This route group page is superseded by app/auth/page.tsx
export default function AuthGroupPage() {
  redirect("/auth");
}
