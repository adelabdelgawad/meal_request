// components/users/view-user-sheet.tsx
"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useLanguage } from "@/hooks/use-language";
import {
  Eye,
  X,
  User,
  Mail,
  Briefcase,
  Shield,
  CheckCircle,
  XCircle,
  Users,
} from "lucide-react";
import type { UserWithRolesResponse } from "@/types/users";
import { useRoles } from "../../context/users-actions-context";

interface ViewUserSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserWithRolesResponse;
}

export function ViewUserSheet({
  open,
  onOpenChange,
  user,
}: ViewUserSheetProps) {
  // Get roles from context
  const roles = useRoles();
  const { t, language, dir } = useLanguage();
  const isRtl = dir === 'rtl';
  const usersT = (t as Record<string, unknown>).users as Record<string, unknown> | undefined;
  const i18n = (usersT?.view as Record<string, unknown>) || {};
  const columnsI18n = (usersT?.columns as Record<string, unknown>) || {};

  const handleClose = () => {
    onOpenChange(false);
  };

  // Get role details with descriptions
  const getUserRoleDetails = () => {
    // If user has roles array (string names), use that
    if (user.roles && Array.isArray(user.roles) && user.roles.length > 0) {
      return user.roles.map((roleName: string, index: number) => {
        const roleDetail = roles.find((role) =>
          role.nameEn === roleName || role.nameAr === roleName
        );

        // Get language-aware role name
        const displayName = roleDetail
          ? (language === "ar" && roleDetail.nameAr
            ? roleDetail.nameAr
            : roleDetail.nameEn || roleName)
          : roleName;

        return {
          id: roleDetail?.id ?? index,
          name: displayName,
          description: roleDetail
            ? (language === "ar" && roleDetail.descriptionAr
              ? roleDetail.descriptionAr
              : roleDetail.descriptionEn)
            : null,
          isActive: roleDetail?.isActive ?? true,
        };
      });
    }

    return [];
  };

  const roleDetails = getUserRoleDetails();

  return (
    <Sheet open={open} onOpenChange={handleClose}>
      <SheetContent className="w-full sm:max-w-3xl flex flex-col" side="right">
        <SheetHeader className="space-y-2 shrink-0">
          <SheetTitle className={`flex items-center gap-2 text-lg ${isRtl ? 'flex-row-reverse' : ''}`}>
            <div className="p-1.5 bg-primary/10">
              <Eye className="h-4 w-4 text-primary" />
            </div>
            {(i18n.title as string) || "View User"}
          </SheetTitle>
          <SheetDescription className="text-sm">
            {(i18n.description as string) || "View user details for"} {user.username}
          </SheetDescription>
        </SheetHeader>

        {/* Scrollable content area */}
        <ScrollArea className="flex-1 py-4">
          <div className="space-y-4 pe-4">
            {/* User Overview Card */}
            <Card className="border">
              <CardHeader className="pb-3">
                <CardTitle className={`flex items-center gap-2 text-base ${isRtl ? 'flex-row-reverse' : ''}`}>
                  <User className="h-4 w-4 text-primary" />
                  {(i18n.userInformation as string) || "User Information"}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Primary Info - Compact */}
                <div className={`flex items-center gap-3 p-3 bg-primary/5 border border-primary/20 ${isRtl ? 'flex-row-reverse' : ''}`}>
                  <div className="w-10 h-10 bg-primary/10 flex items-center justify-center shrink-0">
                    <User className="w-5 h-5 text-primary" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                      <h3 className="text-base font-semibold">
                        {user.fullName || user.username}
                      </h3>
                      <Badge
                        variant={user.isActive ? "default" : "destructive"}
                        className={`flex items-center gap-1 text-xs ${isRtl ? 'flex-row-reverse' : ''}`}
                      >
                        {user.isActive ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        {user.isActive ? ((i18n.active as string) || "Active") : ((i18n.inactive as string) || "Inactive")}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      @{user.username}
                      {user.title && ` • ${user.title}`}
                    </p>
                  </div>
                </div>

                {/* Detailed Information Grid - Compact */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className={`text-muted-foreground flex items-center gap-1 text-xs font-medium ${isRtl ? 'flex-row-reverse' : ''}`}>
                      <User className="h-3 w-3" />
                      {(columnsI18n.username as string) || "Username"}
                    </Label>
                    <div className="font-medium text-sm bg-muted px-2 py-1.5 border">
                      {user.username}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <Label className={`text-muted-foreground flex items-center gap-1 text-xs font-medium ${isRtl ? 'flex-row-reverse' : ''}`}>
                      <User className="h-3 w-3" />
                      {(columnsI18n.fullName as string) || "Full Name"}
                    </Label>
                    <div className="text-sm bg-muted px-2 py-1.5 border">
                      {user.fullName || ((i18n.notProvided as string) || "Not provided")}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <Label className={`text-muted-foreground flex items-center gap-1 text-xs font-medium ${isRtl ? 'flex-row-reverse' : ''}`}>
                      <Briefcase className="h-3 w-3" />
                      {(columnsI18n.title as string) || "Title"}
                    </Label>
                    <div className="text-sm bg-muted px-2 py-1.5 border">
                      {user.title || ((i18n.notProvided as string) || "Not provided")}
                    </div>
                  </div>

                  <div className="space-y-1 md:col-span-2">
                    <Label className={`text-muted-foreground flex items-center gap-1 text-xs font-medium ${isRtl ? 'flex-row-reverse' : ''}`}>
                      <Mail className="h-3 w-3" />
                      {(columnsI18n.email as string) || "Email"}
                    </Label>
                    <div className="font-mono text-sm bg-muted px-2 py-1.5 border break-all">
                      {user.email || ((i18n.notProvided as string) || "Not provided")}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Separator className="my-2" />

            {/* Roles Card - Compact with side-by-side layout */}
            <Card className="border">
              <CardHeader className="pb-3">
                <div className={`flex items-center justify-between ${isRtl ? 'flex-row-reverse' : ''}`}>
                  <CardTitle className={`flex items-center gap-2 text-base ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <Shield className="h-4 w-4 text-primary" />
                    {(i18n.assignedRoles as string) || "Assigned Roles"}
                  </CardTitle>
                  <Badge variant="secondary" className="font-normal text-xs">
                    {roleDetails.length}{" "}
                    {roleDetails.length === 1 ? ((i18n.role as string) || "role") : ((i18n.roles as string) || "roles")}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {roleDetails.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {roleDetails.map((role: { id: string | number; name: string; description: string | null; isActive: boolean }) => (
                      <div
                        key={role.id}
                        className={`flex items-start gap-2 p-3 border hover:bg-muted/50 transition-colors ${isRtl ? 'flex-row-reverse' : ''}`}
                      >
                        <div className="w-6 h-6 bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                          <Shield className="w-3 h-3 text-primary" />
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <h4 className="font-medium text-sm">{role.name}</h4>
                            <Badge
                              variant={role.isActive ? "default" : "secondary"}
                              className="text-xs"
                            >
                              {role.isActive ? ((i18n.active as string) || "Active") : ((i18n.inactive as string) || "Inactive")}
                            </Badge>
                          </div>
                          {role.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {role.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 space-y-2">
                    <div className="w-12 h-12 bg-muted flex items-center justify-center mx-auto">
                      <Users className="w-6 h-6 text-muted-foreground" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-medium text-sm text-muted-foreground">
                        {(i18n.noRoles as string) || "No Roles Assigned"}
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        {(i18n.noRolesDescription as string) || "This user has no roles assigned yet"}
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </ScrollArea>

        {/* Always visible close button */}
        <SheetFooter className="pt-4 border-t shrink-0 bg-background">
          <Button
            variant="outline"
            onClick={handleClose}
            className="w-full sm:w-auto"
          >
            <X className="h-4 w-4 me-2" />
            {(i18n.close as string) || "Close"}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
