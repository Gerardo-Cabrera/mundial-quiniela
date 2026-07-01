import { useState } from "react";
import { Trophy, Target } from "lucide-react";
import { useLeaderboard } from "@/hooks";
import { Card, Spinner, EmptyState } from "@/components/ui";
import { UserPredictionsModal } from "@/components/UserPredictionsModal";
import { useAuthStore } from "@/store/authStore";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";
import type { LeaderboardEntry } from "@/types";

const RANK_STYLES = [
  "text-yellow-400",  // 1st
  "text-gray-300",    // 2nd
  "text-amber-600",   // 3rd
];

export default function Dashboard() {
  const { data: leaderboard, isLoading } = useLeaderboard();
  const { user } = useAuthStore();
  const { t } = useTranslation();
  const [selected, setSelected] = useState<LeaderboardEntry | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!leaderboard?.length) {
    return <EmptyState icon="🏆" title={t("dashboard.emptyTitle")} description={t("dashboard.emptyDescription")} />;
  }

  const myEntry = leaderboard.find((e) => e.team_name === user?.team_name);

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("dashboard.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("brand.edition")}</p>
      </div>

      {/* My summary */}
      {myEntry && (
        <Card gold className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs text-ucl-silver/60 font-mono uppercase mb-1">{t("dashboard.yourPosition")}</p>
            <div className="flex items-center gap-3 min-w-0">
              <span className="font-display text-4xl sm:text-5xl text-ucl-gold shrink-0">#{myEntry.rank}</span>
              <div className="min-w-0">
                <p className="font-medium text-ucl-white truncate">{myEntry.team_name}</p>
                <p className="text-xs text-ucl-silver/60">{t("dashboard.predictionsCount", { n: myEntry.predictions_count })}</p>
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <p className="font-display text-4xl sm:text-5xl text-ucl-gold">{myEntry.total_points}</p>
            <p className="text-xs text-ucl-silver/60 font-mono">{t("dashboard.points")}</p>
          </div>
        </Card>
      )}

      {/* Leaderboard table */}
      <Card>
        <div className="flex items-center gap-2 mb-5">
          <Trophy size={18} className="text-ucl-gold" />
          <h2 className="font-display text-2xl">{t("dashboard.ranking")}</h2>
        </div>

        <div className="space-y-2">
          {leaderboard.map((entry, i) => {
            const isMe = entry.team_name === user?.team_name;
            return (
              <button
                key={entry.team_name}
                type="button"
                onClick={() => setSelected(entry)}
                title={t("dashboard.viewPredictions", { team: entry.team_name })}
                className={clsx(
                  "w-full text-left flex items-center gap-4 px-4 py-3 rounded-lg transition-colors",
                  isMe
                    ? "bg-ucl-gold/10 border border-ucl-gold/20 hover:bg-ucl-gold/15"
                    : "hover:bg-ucl-blue/20"
                )}
              >
                {/* Rank */}
                <span className={clsx(
                  "font-display text-xl w-8 text-center shrink-0",
                  i < 3 ? RANK_STYLES[i] : "text-ucl-silver/50"
                )}>
                  {i < 3 ? ["🥇","🥈","🥉"][i] : entry.rank}
                </span>

                {/* Team name */}
                <span className={clsx(
                  "flex-1 text-sm font-medium truncate",
                  isMe ? "text-ucl-gold" : "text-ucl-white"
                )}>
                  {entry.team_name}
                  {isMe && <span className="ml-2 text-xs text-ucl-gold/60">{t("dashboard.you")}</span>}
                </span>

                {/* Predicciones realizadas */}
                <div className="hidden sm:flex items-center gap-3 text-xs text-ucl-silver/60 font-mono">
                  <span title={t("dashboard.predictionsTooltip")}><Target size={11} className="inline mr-0.5" />{entry.predictions_count}</span>
                </div>

                {/* Total */}
                <span className={clsx(
                  "font-display text-2xl w-14 text-right shrink-0",
                  isMe ? "text-ucl-gold" : "text-ucl-white"
                )}>
                  {entry.total_points}
                </span>
              </button>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 pt-4 border-t border-ucl-blue/30 flex items-center gap-4 text-xs text-ucl-silver/50 font-mono">
          <span><Target size={11} className="inline mr-1" />{t("dashboard.predictionsMade")}</span>
        </div>
      </Card>

      {selected && (
        <UserPredictionsModal
          userId={selected.user_id}
          teamName={selected.team_name}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
