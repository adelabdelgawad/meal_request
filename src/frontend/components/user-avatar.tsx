'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { User as UserIcon, LogOut, Briefcase } from 'lucide-react';
import { useLanguage, translate } from '@/hooks/use-language';
import type { User } from '@/lib/auth/check-token';

interface UserAvatarProps {
  user: User;
  onLogout: () => void;
}

/**
 * Get initials from a name string.
 * Single word: first two characters
 * Multiple words: first letter of first two words
 */
function getInitials(name: string): string {
  if (!name) return 'U';
  const words = name.trim().split(' ');
  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase();
  }
  return words.slice(0, 2).map(word => word[0]?.toUpperCase() || '').join('');
}

export function UserAvatar({ user, onLogout }: UserAvatarProps) {
  const { t } = useLanguage();

  const displayName = user?.fullName || user?.username || user?.name || 'User';
  const initials = getInitials(displayName);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2">
          <Avatar className="h-8 w-8 cursor-pointer border border-border">
            <AvatarImage alt={displayName} />
            <AvatarFallback className="bg-primary text-primary-foreground text-xs font-medium">
              {initials}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-64" align="end" sideOffset={8}>
        {/* Username at top - uppercase */}
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-bold leading-none uppercase">{user?.username}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Full Name */}
        {user?.fullName && (
          <DropdownMenuItem className="flex items-center gap-2 cursor-default focus:bg-transparent" disabled>
            <UserIcon className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{user.fullName}</span>
          </DropdownMenuItem>
        )}

        {/* Title */}
        {user?.title && (
          <DropdownMenuItem className="flex items-center gap-2 cursor-default focus:bg-transparent" disabled>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{user.title}</span>
          </DropdownMenuItem>
        )}

        {(user?.fullName || user?.title) && <DropdownMenuSeparator />}

        {/* Logout */}
        <DropdownMenuItem
          onClick={onLogout}
          className="flex items-center gap-2 text-destructive focus:text-destructive cursor-pointer"
        >
          <LogOut className="h-4 w-4" />
          <span>{translate(t, 'navbar.logout')}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
