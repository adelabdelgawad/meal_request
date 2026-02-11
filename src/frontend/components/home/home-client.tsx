"use client";

import { useSession } from "@/lib/auth/use-session";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import type { User } from "@/lib/auth/check-token";

interface HomeClientProps {
  initialUser: User;
}

/**
 * Home page client component.
 *
 * Receives server-validated user data as prop.
 * Also subscribes to session context for live updates.
 */
export function HomeClient({ initialUser }: HomeClientProps) {
  const { user, refresh, isRefreshing } = useSession();

  // Use session user if available (for live updates), otherwise use initial user
  const currentUser = user || initialUser;

  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Welcome to Meal Request System</h1>
        <p className="text-muted-foreground">
          Manage your meal requests and preferences
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* User Information Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              User Information
              <Button
                variant="outline"
                size="sm"
                onClick={refresh}
                disabled={isRefreshing}
              >
                <RefreshCw className={`h-4 w-4 me-2 ${isRefreshing ? "animate-spin" : ""}`} />
                Refresh Session
              </Button>
            </CardTitle>
            <CardDescription>Your current session details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">Username</div>
              <div className="text-lg font-semibold">{currentUser?.username || currentUser?.name || "N/A"}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">User ID</div>
              <div className="font-mono text-sm">{currentUser?.id || "N/A"}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">Locale</div>
              <div>
                <Badge variant="outline">{currentUser?.locale || "en"}</Badge>
              </div>
            </div>
            {currentUser?.isSuperAdmin && (
              <div>
                <Badge variant="default" className="bg-red-600">Super Admin</Badge>
              </div>
            )}
          </CardContent>
        </Card>

        {/* User Roles & Scopes Card */}
        <Card>
          <CardHeader>
            <CardTitle>Roles & Scopes</CardTitle>
            <CardDescription>Your access permissions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Roles</div>
              <div className="flex flex-wrap gap-2">
                {currentUser?.roles && currentUser.roles.length > 0 ? (
                  currentUser.roles.map((role) => (
                    <Badge key={role} variant="secondary">
                      {role}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-muted-foreground">No roles assigned</span>
                )}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Scopes</div>
              <div className="flex flex-wrap gap-2">
                {currentUser?.scopes && currentUser.scopes.length > 0 ? (
                  currentUser.scopes.map((scope) => (
                    <Badge key={scope} variant="outline">
                      {scope}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-muted-foreground">No scopes assigned</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Accessible Pages Card */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Accessible Pages</CardTitle>
            <CardDescription>
              Pages you have permission to access (updates automatically when session refreshes)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {currentUser?.pages && currentUser.pages.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {currentUser.pages.map((page) => (
                  <Card key={page.id} className="border-2">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">{page.name}</CardTitle>
                      {page.description && (
                        <CardDescription className="text-xs">
                          {page.description}
                        </CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="flex gap-2 text-xs">
                        <Badge variant="outline" className="font-normal">
                          EN: {page.nameEn}
                        </Badge>
                        <Badge variant="outline" className="font-normal">
                          AR: {page.nameAr}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No pages assigned to your account
              </div>
            )}
          </CardContent>
        </Card>

        {/* Navigation Test Card */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Navigation Menu Test</CardTitle>
            <CardDescription>
              The navigation menu at the top automatically displays your accessible pages.
              Click &quot;Refresh Session&quot; above to test that the menu updates when pages change.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border bg-muted/50 p-4">
              <h4 className="font-medium mb-2">How the auto-update works:</h4>
              <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                <li>When you click &quot;Refresh Session&quot;, it calls <code className="bg-background px-1 py-0.5 rounded">GET /api/auth/session</code></li>
                <li>The backend returns updated user data including pages</li>
                <li>The session context updates with new data</li>
                <li>All components using <code className="bg-background px-1 py-0.5 rounded">useSession()</code> re-render automatically</li>
                <li>The navigation menu displays the updated list of pages</li>
              </ol>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
