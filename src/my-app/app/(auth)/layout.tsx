/**
 * Auth layout - no navigation, centered content.
 *
 * This layout is used for authentication pages (login, etc.)
 * It doesn't include the main navigation since users aren't authenticated yet.
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
