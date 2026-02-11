import { Metadata } from "next";
import { redirect as nextRedirect } from "next/navigation";

import { checkToken } from "@/lib/auth/check-token";
import { LoginPageContent } from "./login-page-content";

export const metadata: Metadata = {
  title: "Login | Meal Request System",
  description: "Sign in to your account to manage meal requests",
};

interface LoginPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {

  // Check if user is already authenticated
  const authResult = await checkToken();

  const params = await searchParams;
  const redirectUrl = params.redirect ? String(params.redirect) : undefined;

  // If already logged in, redirect to home or specified redirect
  if (authResult.ok) {
    nextRedirect(redirectUrl || "/");
  }

  const redirect = redirectUrl;
  return <LoginPageContent redirect={redirect} />;
}
