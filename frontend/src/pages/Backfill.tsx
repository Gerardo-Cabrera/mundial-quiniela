import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Plus, Trash2, Upload } from "lucide-react";
import { useTeamsConfig, useBackfill, useMatches, useMatchPlayers } from "@/hooks";
import { useAuthStore } from "@/store/authStore";
import { Card } from "@/components/ui";
import { PredictionCard } from "@/components/PredictionCard";
import { apiErrorMessage } from "@/api/client";
import { useTranslation } from "react-i18next";
import type { Match, MatchPhase } from "@/types";
import { MATCH_PHASES } from "@/types";

interface Row {
  id: number;
  match_id: number | "";
  predicted_home: number;
  predicted_away: number;
  first_goal_player: string;
}
let rowSeq = 0;
const emptyRow = (): Row => ({ id: ++rowSeq, match_id: "", predicted_home: 0, predicted_away: 0, first_goal_player: "" });
const clampScore = (v: string) => Math.max(0, Math.min(20, Number(v) || 0));

// Input de gol: ancho y centrado, sin las flechas del number (casi ocultaban el dígito).
const SCORE_CLS = "input-base w-16 text-center px-1 font-mono text-lg " +
  "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none";

// Una fila = un pronóstico. Elige el partido de la fase y, ya con él, sugiere el
// goleador entre los jugadores de ESE partido (datalist; también se puede escribir).
function BackfillRow({ row, matches, onChange, onRemove, removable }: {
  row: Row;
  matches: Match[];
  onChange: (r: Row) => void;
  onRemove: () => void;
  removable: boolean;
}) {
  const { t } = useTranslation();
  const { data: players = [] } = useMatchPlayers(row.match_id || 0, row.match_id !== "");
  const listId = `bf-players-${row.id}`;

  return (
    <div className="border border-ucl-blue/30 rounded-lg p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={row.match_id}
          onChange={(e) => onChange({ ...row, match_id: e.target.value ? Number(e.target.value) : "", first_goal_player: "" })}
          className="input-base flex-1 min-w-[200px]"
        >
          <option value="">{t("backfill.selectMatch")}</option>
          {matches.map((m) => (
            <option key={m.id} value={m.id}>{m.home_team} vs {m.away_team}</option>
          ))}
        </select>
        <input type="number" min={0} max={20} value={row.predicted_home} aria-label={t("backfill.home")}
          onChange={(e) => onChange({ ...row, predicted_home: clampScore(e.target.value) })} className={SCORE_CLS} />
        <span className="text-ucl-silver/40">-</span>
        <input type="number" min={0} max={20} value={row.predicted_away} aria-label={t("backfill.away")}
          onChange={(e) => onChange({ ...row, predicted_away: clampScore(e.target.value) })} className={SCORE_CLS} />
        {removable && (
          <button onClick={onRemove} className="text-ucl-silver/40 hover:text-red-400 transition-colors p-1" title={t("backfill.removeRow")}>
            <Trash2 size={15} />
          </button>
        )}
      </div>
      <input
        type="text" list={listId} value={row.first_goal_player}
        onChange={(e) => onChange({ ...row, first_goal_player: e.target.value })}
        placeholder={t("backfill.scorerPlaceholder")} disabled={row.match_id === ""}
        className="input-base w-full text-sm disabled:opacity-50"
      />
      <datalist id={listId}>
        {players.map((p) => <option key={p.api_player_id} value={p.name} />)}
      </datalist>
    </div>
  );
}

/**
 * Vista exclusiva de admin para cargar pronósticos retroactivos (backfill). Se elige la
 * fase y el partido (fixture real → `match_id`), el marcador y el goleador entre los
 * jugadores del partido. El resultado se muestra con `PredictionCard`.
 */
export default function BackfillPage() {
  const { user } = useAuthStore();
  const { t } = useTranslation();
  const { data: config } = useTeamsConfig();
  const { data: matches } = useMatches();
  const { mutate: backfill, isPending, data: result, error, reset } = useBackfill();
  const [teamName, setTeamName] = useState("");
  const [phase, setPhase] = useState<MatchPhase>("group_stage");
  const [rows, setRows] = useState<Row[]>([emptyRow()]);

  if (!user?.is_admin) return <Navigate to="/" replace />;

  const participants = config?.allowed_teams ?? [];
  const phaseMatches = (matches ?? []).filter((m) => m.phase === phase);
  const validRows = rows.filter((r) => r.match_id !== "");
  const canSubmit = !!teamName && validRows.length > 0 && !isPending;

  // Al cambiar de fase, los partidos elegidos ya no aplican: se reinician las filas.
  const changePhase = (p: MatchPhase) => { setPhase(p); setRows([emptyRow()]); };
  const setRow = (i: number, r: Row) => setRows((rs) => rs.map((x, j) => (j === i ? r : x)));

  const submit = () => {
    reset();
    backfill({
      team_name: teamName,
      predictions: validRows.map((r) => ({
        match_id: r.match_id as number,
        predicted_home: r.predicted_home,
        predicted_away: r.predicted_away,
        first_goal_player: r.first_goal_player.trim() || undefined,
      })),
    });
  };

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("backfill.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("backfill.subtitle")}</p>
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("backfill.participant")}</label>
            <select value={teamName} onChange={(e) => setTeamName(e.target.value)} className="input-base w-full">
              <option value="">{t("backfill.selectParticipant")}</option>
              {participants.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("backfill.phase")}</label>
            <select value={phase} onChange={(e) => changePhase(e.target.value as MatchPhase)} className="input-base w-full">
              {MATCH_PHASES.map((p) => <option key={p} value={p}>{t(`phase.${p}`)}</option>)}
            </select>
          </div>
        </div>

        <div className="space-y-3">
          {rows.map((r, i) => (
            <BackfillRow
              key={r.id}
              row={r}
              matches={phaseMatches}
              onChange={(next) => setRow(i, next)}
              onRemove={() => setRows((rs) => rs.filter((_, j) => j !== i))}
              removable={rows.length > 1}
            />
          ))}
        </div>

        <div className="flex items-center justify-between gap-3">
          <button onClick={() => setRows((rs) => [...rs, emptyRow()])}
            className="inline-flex items-center gap-1.5 text-sm text-ucl-silver hover:text-ucl-gold transition-colors">
            <Plus size={16} /> {t("backfill.addRow")}
          </button>
          <button onClick={submit} disabled={!canSubmit}
            className="btn-primary inline-flex items-center gap-2 disabled:opacity-50">
            <Upload size={16} /> {isPending ? t("backfill.loading") : t("backfill.submit")}
          </button>
        </div>

        {error && (
          <p role="alert" className="text-red-400 text-sm">{apiErrorMessage(error, t("backfill.error"))}</p>
        )}
      </Card>

      {result && result.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-display text-2xl text-ucl-gold">{t("backfill.loaded", { n: result.length })}</h2>
          {result.map((p) => <PredictionCard key={p.id} pred={p} />)}
        </div>
      )}
    </div>
  );
}
