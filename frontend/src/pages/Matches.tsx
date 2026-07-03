import { useMemo, useState } from "react";
import { useMatches, useMyPredictions } from "@/hooks";
import { MatchDayGrid } from "@/components/MatchDayGrid";
import { PredictionModal } from "@/components/PredictionModal";
import { PageLoader, EmptyState } from "@/components/ui";
import type { Match, MatchPhase } from "@/types";
import { groupMatchesByDay } from "@/types";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";

// Las etiquetas se traducen en render (claves `phaseShort.*` en i18n).
const PHASE_VALUES: (MatchPhase | "all")[] = [
  "all", "group_stage", "round_of_32", "round_of_16",
  "quarter_finals", "semi_finals", "third_place", "final",
];

export default function MatchesPage() {
  const [phase, setPhase]   = useState<MatchPhase | "all">("all");
  const [selected, setSelected] = useState<Match | null>(null);
  const { t } = useTranslation();

  // Se piden TODOS los partidos del filtro (no solo "scheduled") para que
  // groupMatchesByDay calcule `open`/`firstKickoff` con el PRIMER partido real del
  // día (agrupar solo scheduled daría una jornada falsamente "abierta", regresión §22).
  const { data: matches, isLoading } = useMatches({
    phase: phase !== "all" ? phase : undefined,
  });

  const { data: predictions } = useMyPredictions();

  // Muestra los partidos aún por jugar (scheduled) agrupados por día, incluidas las
  // jornadas ya cerradas/iniciadas: siguen visibles pero NO editables (MatchDayGrid
  // solo pasa `onPredict` a las abiertas). Los ya jugados viven en "Resultados".
  const days = useMemo(
    () =>
      groupMatchesByDay(matches ?? [])
        .map((d) => ({ ...d, matches: d.matches.filter((m) => m.status === "scheduled") }))
        .filter((d) => d.matches.length > 0),
    [matches]
  );

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("matches.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("matches.subtitle")}</p>
      </div>

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
