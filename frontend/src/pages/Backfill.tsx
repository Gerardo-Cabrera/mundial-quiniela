import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Plus, Trash2, Upload } from "lucide-react";
import { useTeamsConfig, useBackfill } from "@/hooks";
import { useAuthStore } from "@/store/authStore";
import { Card } from "@/components/ui";
import { PredictionCard } from "@/components/PredictionCard";
import { apiErrorMessage } from "@/api/client";
import { useTranslation } from "react-i18next";

interface Row {
  home_team: string;
  away_team: string;
  predicted_home: number;
  predicted_away: number;
  first_goal_player: string;
}
const emptyRow = (): Row => ({ home_team: "", away_team: "", predicted_home: 0, predicted_away: 0, first_goal_player: "" });
const clampScore = (v: string) => Math.max(0, Math.min(20, Number(v) || 0));

/**
 * Vista exclusiva de admin para cargar pronósticos retroactivos (backfill). Identifica
 * el partido por el par de selecciones y el goleador por nombre; el backend resuelve
 * ids y orienta el marcador. El resultado se muestra con `PredictionCard`.
 */
export default function BackfillPage() {
  const { user } = useAuthStore();
  const { t } = useTranslation();
  const { data: config } = useTeamsConfig();
  const { mutate: backfill, isPending, data: result, error, reset } = useBackfill();
  const [teamName, setTeamName] = useState("");
  const [rows, setRows] = useState<Row[]>([emptyRow()]);

  if (!user?.is_admin) return <Navigate to="/" replace />;

  const participants = config?.allowed_teams ?? [];
  const teams = config?.wc_teams ?? [];

  const validRows = rows.filter((r) => r.home_team && r.away_team && r.home_team !== r.away_team);
  const canSubmit = !!teamName && validRows.length > 0 && !isPending;

  const setRow = (i: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const submit = () => {
    reset();
    backfill({
      team_name: teamName,
      predictions: validRows.map((r) => ({
        home_team: r.home_team,
        away_team: r.away_team,
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
        <div>
          <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("backfill.participant")}</label>
          <select value={teamName} onChange={(e) => setTeamName(e.target.value)} className="input-base w-full">
            <option value="">{t("backfill.selectParticipant")}</option>
            {participants.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        <div className="space-y-3">
          {rows.map((r, i) => (
            <div key={i} className="border border-ucl-blue/30 rounded-lg p-3 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <select value={r.home_team} onChange={(e) => setRow(i, { home_team: e.target.value })} className="input-base flex-1 min-w-[110px]">
                  <option value="">{t("backfill.home")}</option>
                  {teams.map((tm) => <option key={tm} value={tm}>{tm}</option>)}
                </select>
                <input type="number" min={0} max={20} value={r.predicted_home}
                  onChange={(e) => setRow(i, { predicted_home: clampScore(e.target.value) })}
                  className="input-base w-14 text-center" aria-label={t("backfill.home")} />
                <span className="text-ucl-silver/40">-</span>
                <input type="number" min={0} max={20} value={r.predicted_away}
                  onChange={(e) => setRow(i, { predicted_away: clampScore(e.target.value) })}
                  className="input-base w-14 text-center" aria-label={t("backfill.away")} />
                <select value={r.away_team} onChange={(e) => setRow(i, { away_team: e.target.value })} className="input-base flex-1 min-w-[110px]">
                  <option value="">{t("backfill.away")}</option>
                  {teams.map((tm) => <option key={tm} value={tm}>{tm}</option>)}
                </select>
                {rows.length > 1 && (
                  <button onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}
                    className="text-ucl-silver/40 hover:text-red-400 transition-colors p-1" title={t("backfill.removeRow")}>
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
              <input type="text" value={r.first_goal_player}
                onChange={(e) => setRow(i, { first_goal_player: e.target.value })}
                placeholder={t("backfill.scorerPlaceholder")} className="input-base w-full text-sm" />
            </div>
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
