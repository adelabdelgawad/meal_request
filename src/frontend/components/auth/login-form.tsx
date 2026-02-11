"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, AlertCircle, Eye, EyeOff } from "lucide-react";

import { loginFormSchema, type LoginFormInput } from "@/lib/validation/auth-schema";
import { loginAction } from "@/lib/api/auth.actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useLanguage, translate } from "@/hooks/use-language";

interface LoginFormProps {
  redirect?: string;
}

export function LoginForm({ redirect }: LoginFormProps) {
  const { t } = useLanguage();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormInput>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      username: typeof window !== 'undefined' ? localStorage.getItem('rememberedUsername') || "" : "",
      password: "",
      remember: typeof window !== 'undefined' ? !!localStorage.getItem('rememberedUsername') : false,
    },
  });

  const onSubmit = async (data: LoginFormInput) => {
    setIsLoading(true);
    setApiError(null);

    try {
      // Handle "Remember Me" functionality
      if (data.remember) {
        localStorage.setItem('rememberedUsername', data.username);
      } else {
        localStorage.removeItem('rememberedUsername');
      }

      // Use the centralized auth action
      await loginAction({
        username: data.username,
        password: data.password,
      });

      // Login successful - result contains accessToken and user info
      // Use window.location.href for full page reload to update session
      const redirectUrl = redirect || searchParams.get("redirect") || "/";

      // Keep button disabled - redirect will happen, no need to re-enable
      // Small delay to ensure cookie is set
      setTimeout(() => {
        window.location.href = redirectUrl;
      }, 100);
    } catch (error) {
      console.error("Login error:", error);
      // Extract actual error message from backend
      const errorMessage = error instanceof Error
        ? error.message
        : "An unexpected error occurred. Please try again.";
      setApiError(errorMessage);
      // Only re-enable button on error
      setIsLoading(false);
    }
  };

  return (


    
    <form onSubmit={handleSubmit(onSubmit)} className="w-full space-y-4">
      {/* Username Field */}

      <div className="space-y-2">
        <Label htmlFor="username">{translate(t, "auth.username")}</Label>
        <Input
          id="username"
          type="text"
          placeholder={translate(t, "auth.usernameHint")}
          disabled={isLoading}
          autoComplete="username"
          aria-invalid={!!errors.username}
          aria-describedby={errors.username ? "username-error" : undefined}
          {...register("username")}
        />
        {errors.username && (
          <p id="username-error" className="text-xs text-destructive">
            {errors.username.message}
          </p>
        )}
      </div>

      {/* Password Field */}
      <div className="space-y-2">
        <Label htmlFor="password">{translate(t, "auth.password")}</Label>
        <div className="relative">
          <Input
            id="password"
            type={showPassword ? "text" : "password"}
            placeholder={translate(t, "auth.passwordHint")}
            disabled={isLoading}
            autoComplete="current-password"
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? "password-error" : undefined}
            className="pr-10"
            {...register("password")}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            disabled={isLoading}
            aria-label={showPassword ? translate(t, "auth.hidePassword") : translate(t, "auth.showPassword")}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        </div>
        {errors.password && (
          <p id="password-error" className="text-xs text-destructive">
            {errors.password.message}
          </p>
        )}
      </div>



      {/* Remember Me Checkbox */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="remember"
          disabled={isLoading}
          {...register("remember")}
        />
        <Label
          htmlFor="remember"
          className="font-normal cursor-pointer"
        >
          {translate(t, "auth.rememberMe")}
        </Label>
      </div>

      {/* API Error Alert */}
      {apiError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      {/* Submit Button */}
      <Button
        type="submit"
        className="w-full"
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <Loader2 className="me-2 h-4 w-4 animate-spin" />
            {translate(t, "auth.loggingIn")}
          </>
        ) : (
          translate(t, "auth.loginButton")
        )}
      </Button>
    </form>
  );
}
