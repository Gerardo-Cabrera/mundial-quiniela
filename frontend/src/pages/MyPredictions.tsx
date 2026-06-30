import { useMyPredictions, useDeletePrediction } from "@/hooks";
import { Spinner, EmptyState, PointsChip, Badge } from "@/components/ui";
import { Trash2 } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { isFirstGoalHit } from "@/types";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";

export default function MyPredictionsPage() {
  const { data: predictions, isLoading } = useMyPredictions();
  const { mutate: deletePred }           = useDeletePrediction();
  const { t } = useTranslation();

  const totalPoints = predictions?.reduce((s, p) => s + p.points_earned, 0) ?? 0;
  const calculated  = predictions?.filter((p) => p.is_calculated).length ?? 0;

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("myPredictions.title")}</h1>
          <p className="text-ucl-silver/60 text-sm mt-1">{t("myPredictions.registered", { n: predictions?.length ?? 0 })}</p>
        </div>
        {calculated > 0 && (
          <div className="text-right">
            <p className="font-display text-4xl text-ucl-gold">{totalPoints}</p>
            <p className="text-xs text-ucl-silver/60 font-mono">{t("myPredictions.matchPoints")}</p>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : !predictions?.length ? (
        <EmptyState
          icon="🎯"
          title={t("myPredictions.emptyTitle")}
          description={t("myPredictions.emptyDescription")}
        />
      ) : (
        <div className="space-y-3">
          {predictions.map((pred) => {
            const match = pred.match;
            const isExact =
              pred.is_calculated &&
              pred.predicted_home === match.home_score &&
              pred.predicted_away === match.away_score;
            const goalResolved = match.status === "finished" && match.first_goal_player_id != null;
            const goalHit      = isFirstGoalHit(pred, match);

            return (
              <div
                key={pred.id}
                className={clsx(
                  "card px-4 sm:px-5 py-4",
                  isExact && "border-ucl-gold/30 shadow-[0_0_16px_rgba(201,168,76,0.08)]"
                )}
              >
                {/* Cabecera: fase (encima del partido) + fecha */}
                <div className="flex items-center justify-between gap-2 mb-3">
                  <Badge variant={match.phase === "group_stage" ? "blue" : "gold"}>
                    {t(`phase.${match.phase}`)}
                  </Badge>
                  <span className="text-xs text-ucl-silver/50 font-mono shrink-0">
                    {format(new Date(match.match_date), "d MMM", { locale: es })}
                  </span>
                </div>

                {/* Cuerpo: logos · partido · marcador · puntos */}
                <div className="flex items-center gap-3 sm:gap-4">
                  {/* Teams logos */}
                  <div className="flex items-center gap-2 shrink-0">
                    {match.home_team_logo ? (
                      <img src={match.home_team_logo} alt="" className="w-7 h-7 object-contain" />
                    ) : <span>⚽</span>}
                    {match.away_team_logo ? (
                      <img src={match.away_team_logo} alt="" className="w-7 h-7 object-contain" />
                    ) : <span>⚽</span>}
                  </div>

                  {/* Match info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {match.home_team} <span className="text-ucl-silver/40">{t("common.vs")}</span> {match.away_team}
                    </p>
                    {(pred.first_goal_player || (match.status === "finished" && match.first_goal_player)) && (
                      <p className="text-xs text-ucl-silver/50 mt-1 truncate">
                        <span>⚽ </span>
                        {pred.first_goal_player ? (
                          <span className={goalResolved && goalHit ? "text-ucl-gold" : "text-ucl-silver/70"}>
                            {pred.first_goal_player}
                          </span>
                        ) : (
                          <span className="italic">{t("myPredictions.noScorer")}</span>
                        )}
                        {match.status === "finished" && match.first_goal_player && (
                          <span className="text-ucl-silver/40">{t("myPredictions.realScorer", { name: match.first_goal_player })}</span>
                        )}
                        {goalResolved && pred.first_goal_player_id != null && (
                          <span className={goalHit ? "text-ucl-gold" : "text-ucl-silver/40"}> {goalHit ? "✓" : "✗"}</span>
                        )}
                      </p>
                    )}
                  </div>

                  {/* Prediction */}
                  <div className="text-center shrink-0">
                    <p className={clsx(
                      "font-mono font-bold text-lg",
                      isExact ? "text-ucl-gold" : "text-ucl-white"
                    )}>
                      {pred.predicted_home} - {pred.predicted_away}
                    </p>
                    {match.status === "finished" && (
                      <p className="text-xs text-ucl-silver/50 font-mono">
                        {t("common.realScore", { home: match.home_score, away: match.away_score })}
                      </p>
                    )}
                  </div>

                  {/* Points / Delete */}
                  <div className="shrink-0 flex items-center gap-2">
                    {pred.is_calculated ? (
                      <PointsChip points={pred.points_earned} />
                    ) : !pred.is_calculated && match.status === "scheduled" ? (
                      <button
                        onClick={() => deletePred(pred.id)}
                        className="text-ucl-silver/30 hover:text-red-400 transition-colors p-1"
                        title={t("myPredictions.deleteTooltip")}
                      >
                        <Trash2 size={15} />
                      </button>
                    ) : (
                      <span className="text-xs text-ucl-silver/40 font-mono">—</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
