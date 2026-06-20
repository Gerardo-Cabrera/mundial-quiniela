import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Pencil } from "lucide-react";
import type { Match, Prediction } from "@/types";
import { PHASE_LABELS, isFirstGoalHit } from "@/types";
import { Badge, StatusDot, PointsChip } from "@/components/ui";
import { clsx } from "clsx";

interface MatchCardProps {
  match: Match;
  prediction?: Prediction;
  onPredict?: (match: Match) => void;
}

export function MatchCard({ match, prediction, onPredict }: MatchCardProps) {
  const isFinished  = match.status === "finished";
  const isScheduled = match.status === "scheduled";
  const hasExact    = prediction &&
    prediction.predicted_home === match.home_score &&
    prediction.predicted_away === match.away_score;
  const goalResolved = isFinished && match.first_goal_player_id != null;
  const goalHit      = prediction != null && isFirstGoalHit(prediction, match);

  return (
    <div
      className={clsx(
        "card p-4 transition-all duration-200 group flex flex-col h-full",
        prediction && "border-ucl-gold/20",
        match.status === "live" && "border-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.08)]"
      )}
    >
      {/* Header: fase + status */}
      <div className="flex items-center justify-between mb-4">
        <Badge variant={match.phase === "group_stage" ? "blue" : "gold"}>
          {PHASE_LABELS[match.phase]}
        </Badge>
        <StatusDot status={match.status} />
      </div>

      {/* Teams + Score */}
      <div className="flex items-center gap-3">
        {/* Home */}
        <div className="flex-1 flex flex-col items-center gap-2">
          {match.home_team_logo ? (
            <img src={match.home_team_logo} alt={match.home_team} className="w-10 h-10 object-contain" />
          ) : (
            <div className="w-10 h-10 rounded-full bg-ucl-blue/50 flex items-center justify-center text-lg">⚽</div>
          )}
          <span className="text-sm text-center font-medium leading-tight">{match.home_team}</span>
        </div>

        {/* Score / VS */}
        <div className="flex flex-col items-center gap-1 min-w-[64px]">
          {isFinished || match.status === "live" ? (
            <span className="font-display text-3xl text-ucl-white tracking-widest">
              {match.home_score} - {match.away_score}
            </span>
          ) : (
            <span className="font-display text-xl text-ucl-silver/50">VS</span>
          )}
          <span className="text-xs text-ucl-silver/50 font-mono">
            {format(new Date(match.match_date), "d MMM · HH:mm", { locale: es })}
          </span>
        </div>

        {/* Away */}
        <div className="flex-1 flex flex-col items-center gap-2">
          {match.away_team_logo ? (
            <img src={match.away_team_logo} alt={match.away_team} className="w-10 h-10 object-contain" />
          ) : (
            <div className="w-10 h-10 rounded-full bg-ucl-blue/50 flex items-center justify-center text-lg">⚽</div>
          )}
          <span className="text-sm text-center font-medium leading-tight">{match.away_team}</span>
        </div>
      </div>

      {/* Real first goal scorer (finished matches) */}
      {isFinished && match.first_goal_player && (
        <div className="mt-3 flex items-center justify-center gap-1.5 text-xs">
          <span className="text-ucl-silver/50">⚽ Primer gol:</span>
          <span className="font-medium text-ucl-white">{match.first_goal_player}</span>
        </div>
      )}

      {/* Prediction row */}
      {prediction ? (
        <div className="mt-auto pt-3 border-t border-ucl-blue/30 flex items-center justify-between">
          <div className="flex flex-col gap-1 text-sm min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-ucl-silver/60 text-xs">Tu pronóstico:</span>
              <span className={clsx("font-mono font-bold", hasExact ? "text-ucl-gold" : "text-ucl-white")}>
                {prediction.predicted_home} - {prediction.predicted_away}
              </span>
              {hasExact && <span className="text-xs text-ucl-gold">✓ Exacto</span>}
            </div>
            {prediction.first_goal_player && (
              <div className="flex items-center gap-1.5 text-xs min-w-0">
                <span className="text-ucl-silver/60">⚽ Goleador:</span>
                <span className={clsx("truncate", goalHit ? "text-ucl-gold" : "text-ucl-silver/80")}>
                  {prediction.first_goal_player}
                </span>
                {goalResolved && (
                  <span className={goalHit ? "text-ucl-gold" : "text-ucl-silver/40"}>
                    {goalHit ? "✓" : "✗"}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {prediction.is_calculated && <PointsChip points={prediction.points_earned} />}
            {isScheduled && onPredict && (
              <button
                onClick={() => onPredict(match)}
                className="text-ucl-silver/40 hover:text-ucl-gold transition-colors p-1"
                title="Editar pronóstico"
              >
                <Pencil size={14} />
              </button>
            )}
          </div>
        </div>
      ) : isScheduled && onPredict ? (
        <div className="mt-auto pt-3 border-t border-ucl-blue/30">
          <button
            onClick={() => onPredict(match)}
            className="btn-primary w-full text-sm py-2"
          >
            Pronosticar
          </button>
        </div>
      ) : null}
    </div>
  );
}
