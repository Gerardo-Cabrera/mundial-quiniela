import { useMemo, useState } from "react";
import { ToggleLeft, ToggleRight } from "lucide-react";
import { useMatches, useMyPredictions, useSettings, useSetLatePredictions } from "@/hooks";
import { useAuthStore } from "@/store/authStore";
import { MatchDayGrid } from "@/components/MatchDayGrid";
import { PredictionModal } from "@/components/PredictionModal";
import { PageLoader, EmptyState } from "@/components/ui";
import type { Match, MatchPhase } from "@/types";
import { groupMatchesByDay, MATCH_PHASES } from "@/types";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";

// Las etiquetas se traducen en render (claves `phaseShort.*` en i18n).
const PHASE_VALUES: (MatchPhase | "all")[] = ["all", ...MATCH_PHASES];

export default function MatchesPage() {
  const [phase, setPhase]   = useState<MatchPhase | "all">("all");
  const [selected, setSelected] = useState<Match | null>(null);
  const { t } = useTranslation();
  const { user } = useAuthStore();

  // Se piden TODOS los partidos del filtro (no solo "scheduled") para que
  // groupMatchesByDay calcule `open`/`firstKickoff` con el PRIMER partido real del
  // día (agrupar solo scheduled daría una jornada falsamente "abierta", regresión §22).
  const { data: matches, isLoading } = useMatches({
    phase: phase !== "all" ? phase : undefined,
  });

  const { data: predictions } = useMyPredictions();

  // Interruptor de pronósticos tardíos: extiende la edición hasta el inicio del
  // primer partido del día. El admin lo controla; afecta a todos los usuarios.
  const { data: appSettings } = useSettings();
  const lateEnabled = appSettings?.late_predictions_enabled ?? false;
  const { mutate: setLate, isPending } = useSetLatePredictions();

  // Muestra los partidos aún por jugar (scheduled) agrupados por día, incluidas las
  // jornadas ya cerradas/iniciadas: siguen visibles pero NO editables (MatchDayGrid
  // solo pasa `onPredict` a las abiertas). Los ya jugados viven en "Resultados".
  const days = useMemo(
    () =>
      groupMatchesByDay(matches ?? [], lateEnabled)
        .map((d) => ({ ...d, matches: d.matches.filter((m) => m.status === "scheduled") }))
        .filter((d) => d.matches.length > 0),
    [matches, lateEnabled]
  );

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("matches.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("matches.subtitle")}</p>
      </div>

      {/* Interruptor admin: pronósticos tardíos (hasta el inicio del primer partido) */}
      {user?.is_admin && (
        <button
          type="button"
          onClick={() => setLate(!lateEnabled)}
          disabled={isPending}
          title={t("matches.latePredictionsHint")}
          className={clsx(
            "inline-flex items-center gap-2 text-xs rounded-full border px-3 py-1.5 transition-colors disabled:opacity-50",
            lateEnabled
              ? "border-ucl-gold/50 text-ucl-gold bg-ucl-gold/10"
              : "border-ucl-blue/50 text-ucl-silver hover:text-ucl-gold hover:border-ucl-gold"
          )}
        >
          {lateEnabled ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
          {t("matches.latePredictions")}
        </button>
      )}

      {/* Filtro por fase */}
      <div className="flex gap-2 flex-wrap">
        {PHASE_VALUES.map((value) => (
          <button
            key={value}
            onClick={() => setPhase(value)}
            className={clsx(
              "px-3 py-1.5 rounded-full text-xs font-mono transition-all duration-150",
              phase === value
                ? "bg-ucl-gold text-ucl-navy font-bold"
                : "border border-ucl-blue/50 text-ucl-silver hover:border-ucl-gold hover:text-ucl-gold"
            )}
          >
            {t(`phaseShort.${value}`)}
          </button>
        ))}
      </div>

      {/* Un bloque por día; las jornadas cerradas se muestran no editables */}
      {isLoading ? (
        <PageLoader />
      ) : !days.length ? (
        <EmptyState icon="✅" title={t("matches.emptyTitle")} description={t("matches.emptyDescription")} />
      ) : (
        <MatchDayGrid days={days} predictions={predictions} onPredict={setSelected} />
      )}

      {selected && (
        <PredictionModal
          match={selected}
          prediction={predictions?.find((p) => p.match_id === selected.id)}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
