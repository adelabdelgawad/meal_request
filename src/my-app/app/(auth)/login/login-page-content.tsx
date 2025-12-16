"use client";

import Image from "next/image";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { LoginForm } from "@/components/auth/login-form";
import { useLanguage, translate } from "@/hooks/use-language";

interface LoginPageContentProps {
  redirect?: string;
}

export function LoginPageContent({ redirect }: LoginPageContentProps) {
  const { t } = useLanguage();

  return (
    <div dir="ltr" className="w-full space-y-4">
      <Card className="border-border/50 shadow-lg">
        <CardHeader className="space-y-2">
          <div className="flex justify-center mb-2">
            <Image
              src="/logo.png"
              alt="Logo"
              width={180}
              height={60}
              priority
              className="h-auto w-auto max-h-16"
            />
          </div>
          <CardDescription className="text-center">
            {translate(t, 'auth.cardDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm redirect={redirect} />
        </CardContent>
      </Card>
      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        <p>{translate(t, 'auth.copyright')}</p>
      </div>
    </div>
  );
}
