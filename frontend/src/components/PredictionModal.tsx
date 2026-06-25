import { useState } from "react";
import { createPortal } from "react-dom";
import { X, Minus, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Match, Prediction } from "@/types";
import { useSavePrediction, useMatchPlayers } from "@/hooks";
import { Spinner } from "@/components/ui";

interface Props {
  match: Match;
  prediction?: Prediction;
  onClose: () => void;
}

function ScoreInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => onChange(Math.max(0, value - 1))}
        className="w-8 h-8 rounded-full border border-ucl-blue/60 text-ucl-silver hover:border-ucl-gold hover:text-ucl-gold transition-colors flex items-center justify-center"
      >
        <Minus size={14} />
      </button>
      <span className="font-display text-4xl text-ucl-white w-10 text-center">{value}</span>
      <button
        onClick={() => onChange(value + 1)}
        className="w-8 h-8 rounded-full border border-ucl-blue/60 text-ucl-silver hover:border-ucl-gold hover:text-ucl-gold transition-colors flex items-center justify-center"
      >
        <Plus size={14} />
      </button>
    </div>
  );
}

export function PredictionModal({ match, prediction, onClose }: Props) {
  const [homeScore, setHomeScore] = useState(prediction?.predicted_home ?? 0);
  const [awayScore, setAwayScore]  = useState(prediction?.predicted_away ?? 0);
  const [firstGoalPlayerId, setFirstGoalPlayerId] = useState<string>(
    prediction?.first_goal_player_id != null ? String(prediction.first_goal_player_id) : "",
  );
  // Un 0-0 no tiene primer gol: el backend rechaza esa combinación (422). Se oculta
  // la sección y **no se consulta la plantilla** (la query se reactiva sola si el
  // usuario sube el marcador). La selección previa se conserva en estado.
  const isGoalless = homeScore === 0 && awayScore === 0;

  const { mutate: save, isPending, isSuccess, isError } = useSavePrediction();
  const { data: players = [], isLoading: playersLoading } = useMatchPlayers(match.id, !isGoalless);
  const { t } = useTranslation();

  const homePlayers = players.filter((p) => p.team_name === match.home_team);
  const awayPlayers = players.filter((p) => p.team_name === match.away_team);

  const handleSave = () => {
    save({
      match_id:       match.id,
      predicted_home: homeScore,
      predicted_away: awayScore,
      first_goal_player_id: !isGoalless && firstGoalPlayerId ? Number(firstGoalPlayerId) : undefined,
    }, { onSuccess: () => setTimeout(onClose, 800) });
  };

  // Portal a <body>: el modal es `position: fixed`, pero los contenedores de
  // página usan `.animate-in` (que deja un `transform` aplicado y crea un
  // containing block). Sin el portal, el `fixed` se posicionaría respecto a esa
  // página (no al viewport) y obligaría a hacer scroll para ver el modal.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-ucl-navy/80 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-md card border-ucl-gold/25 p-6 shadow-2xl animate-in">
        {/* Close */}
        <button onClick={onClose} className="absolute top-4 right-4 text-ucl-silver/60 hover:text-ucl-white transition-colors">
          <X size={20} />
        </button>

        <h2 className="font-display text-2xl text-ucl-gold mb-1">
          {prediction ? t("predictionModal.titleEdit") : t("predictionModal.titleNew")}
        </h2>
        <p className="text-ucl-silver/60 text-sm mb-6">
          {match.home_team} vs {match.away_team}
        </p>

        {/* Score picker */}
        <div className="flex items-center justify-between gap-4 bg-ucl-navy/60 rounded-xl p-5 mb-5">
          <div className="flex flex-col items-center gap-3">
            {match.home_team_logo && <img src={match.home_team_logo} alt="" className="w-10 h-10 object-contain" />}
            <span className="text-xs text-ucl-silver/70 text-center">{match.home_team}</span>
            <ScoreInput value={homeScore} onChange={setHomeScore} />
          </div>
          <span className="font-display text-2xl text-ucl-silver/30">-</span>
          <div className="flex flex-col items-center gap-3">
            {match.away_team_logo && <img src={match.away_team_logo} alt="" className="w-10 h-10 object-contain" />}
            <span className="text-xs text-ucl-silver/70 text-center">{match.away_team}</span>
            <ScoreInput value={awayScore} onChange={setAwayScore} />
          </div>
        </div>

        {/* Primer goleador oculto en un 0-0. */}
        {!isGoalless && (
          <div className="mb-6">
            <label className="block text-xs text-ucl-silver/70 mb-2 font-mono uppercase tracking-wider">
              ⚽ {t("predictionModal.firstScorerLabel")}
            </label>
            {playersLoading ? (
              <div className="input-base w-full flex items-center gap-2 text-ucl-silver/60">
                <Spinner size="sm" /> {t("predictionModal.loadingSquads")}
              </div>
            ) : players.length === 0 ? (
              <p className="text-xs text-ucl-silver/50 italic">
                {t("predictionModal.squadsUnavailable")}
              </p>
            ) : (
              <select
                value={firstGoalPlayerId}
                onChange={(e) => setFirstGoalPlayerId(e.target.value)}
                className="input-base w-full"
              >
                <option value="">{t("predictionModal.noPrediction")}</option>
                <optgroup label={match.home_team}>
                  {homePlayers.map((p) => (
                    <option key={p.api_player_id} value={p.api_player_id}>{p.name}</option>
                  ))}
                </optgroup>
                <optgroup label={match.away_team}>
                  {awayPlayers.map((p) => (
                    <option key={p.api_player_id} value={p.api_player_id}>{p.name}</option>
                  ))}
                </optgroup>
              </select>
            )}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSave}
          disabled={isPending || isSuccess}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {isPending ? <><Spinner size="sm" /> {t("predictionModal.saving")}</> :
           isSuccess  ? t("predictionModal.saved") :
           t("predictionModal.save")}
        </button>

        {isError && (
          <p className="mt-3 text-red-400 text-sm text-center">
            {t("predictionModal.saveError")}
          </p>
        )}
      </div>
    </div>,
    document.body,
  );
}
