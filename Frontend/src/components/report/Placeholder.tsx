// Tiny placeholder primitives for report pages — used whenever a backend
// field is missing or empty. Keeps the layout intact and visually quiet.

import { CircleOff } from "lucide-react";
import type { ReactNode } from "react";

export function Placeholder({ label = "Not available" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-muted-foreground/60 text-sm">
      <CircleOff className="h-3 w-3" />
      {label}
    </span>
  );
}

export function EmptyBlock({
  title = "Not available",
  hint,
  children,
}: {
  title?: string;
  hint?: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-border/60 bg-card/30 px-4 py-6 text-center">
      <CircleOff className="h-4 w-4 text-muted-foreground/60 mx-auto" />
      <p className="mt-2 text-sm text-muted-foreground">{title}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground/70">{hint}</p>}
      {children}
    </div>
  );
}

/** Render value if present, otherwise a placeholder. */
export function ValueOr({
  value,
  children,
  label,
}: {
  value: unknown;
  children: ReactNode;
  label?: string;
}) {
  const empty =
    value === null ||
    value === undefined ||
    (Array.isArray(value) && value.length === 0) ||
    (typeof value === "string" && value.trim() === "");
  return empty ? <Placeholder label={label} /> : <>{children}</>;
}
