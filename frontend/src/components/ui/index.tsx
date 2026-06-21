import { type ReactNode } from "react";
import { clsx } from "clsx";
import { useTranslation } from "react-i18next";
import type { MatchStatus } from "@/types";

// ── CARD ──────────────────────────────────────────────────────────────────────

interface CardProps {
  children: ReactNode;
  className?: string;
  gold?: boolean;
}

export function Card({ children, className, gold }: CardProps) {
  return (
    <div
      className={clsx(
        "card p-5 animate-in",
        gold && "border-ucl-gold/40 shadow-[0_0_24px_rgba(201,168,76,0.1)]",
        className
      )}
    >
      {children}
    </div>
  );
}

// ── BADGE ─────────────────────────────────────────────────────────────────────

type BadgeVariant = "gold" | "silver" | "blue" | "green" | "red" | "gray";

const BADGE_STYLES: Record<BadgeVariant, string> = {
  gold:   "border-ucl-gold/60 text-ucl-gold bg-ucl-gold/10",
  silver: "border-ucl-silver/40 text-ucl-silver bg-ucl-silver/10",
  blue:   "border-blue-400/40 text-blue-300 bg-blue-900/20",
  green:  "border-green-400/40 text-green-300 bg-green-900/20",
  red:    "border-red-400/40 text-red-300 bg-red-900/20",
  gray:   "border-gray-600/40 text-gray-400 bg-gray-900/20",
};

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = "blue", className }: BadgeProps) {
  return (
    <span className={clsx("phase-badge", BADGE_STYLES[variant], className)}>
      {children}
    </span>
  );
}

// ── SPINNER ───────────────────────────────────────────────────────────────────

export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizes = { sm: "w-4 h-4", md: "w-8 h-8", lg: "w-12 h-12" };
  return (
    <div
      className={clsx(
        "border-2 border-ucl-blue border-t-ucl-gold rounded-full animate-spin",
        sizes[size]
      )}
    />
  );
}

// ── EMPTY STATE ───────────────────────────────────────────────────────────────

export function EmptyState({ icon, title, description }: {
  icon: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
      <span className="text-5xl">{icon}</span>
      <h3 className="font-display text-2xl text-ucl-silver">{title}</h3>
      {description && <p className="text-ucl-silver/60 text-sm max-w-xs">{description}</p>}
    </div>
  );
}

// ── POINTS CHIP ───────────────────────────────────────────────────────────────

export function PointsChip({ points }: { points: number }) {
  const { t } = useTranslation();
  return (
    <span className={clsx(
      "inline-flex items-center gap-1 font-mono text-sm font-bold px-2.5 py-0.5 rounded-full",
      points > 0
        ? "bg-ucl-gold/20 text-ucl-gold border border-ucl-gold/30"
        : "bg-ucl-silver/10 text-ucl-silver/50 border border-ucl-silver/20"
    )}>
      {points > 0 ? `+${points}` : points} {t("common.pts")}
    </span>
  );
}

// ── STATUS DOT ────────────────────────────────────────────────────────────────

export function StatusDot({ status }: { status: MatchStatus }) {
  const { t } = useTranslation();
  if (status === "live") {
    return (
      <span className="flex items-center gap-1.5 text-red-400 text-xs font-semibold">
        <span className="live-dot" /> {t("status.liveBadge")}
      </span>
    );
  }
  const styles: Record<MatchStatus, string> = {
    live:      "",
    scheduled: "text-ucl-silver/60",
    finished:  "text-green-400/80",
    postponed: "text-yellow-500/70",
  };
  return <span className={clsx("text-xs", styles[status])}>{t(`status.${status}`)}</span>;
}
