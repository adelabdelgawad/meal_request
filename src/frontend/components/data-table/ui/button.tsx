import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'success' | 'danger' | 'warning';
  size?: 'sm' | 'default' | 'lg';
  icon?: React.ReactNode;
  children: React.ReactNode;
  tooltip?: string;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'default',
  size = 'default',
  icon,
  children,
  className = '',
  tooltip,
  title,
  ...props
}) => {
  // Base styles with consistent height, alignment, and focus states
  const baseStyles = "inline-flex items-center justify-center gap-2 font-medium transition-colors text-sm leading-none select-none outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1";

  // Height-based sizing for consistent button heights
  const sizeStyles = {
    sm: "h-8 px-3",
    default: "h-9 px-4",
    lg: "h-10 px-6",
  };

  const variantStyles = {
    default: "bg-card border border-border hover:bg-muted text-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-card",
    primary: "bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary",
    success: "bg-green-600 text-white hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed",
    danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed",
    warning: "bg-yellow-600 text-white hover:bg-yellow-700 dark:bg-yellow-700 dark:hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed"
  };

  // Use custom className if provided, otherwise use variant styles
  const buttonStyles = className
    ? `${baseStyles} ${sizeStyles[size]} ${className}`
    : `${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]}`;

  return (
    <button
      className={buttonStyles}
      title={tooltip || title}
      {...props}
    >
      {icon && (
        <span className="shrink-0 w-4 h-4 flex items-center justify-center">
          {icon}
        </span>
      )}
      <span>{children}</span>
    </button>
  );
};