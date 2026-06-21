import { useMemo, useState } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useMatches, useMyPredictions } from "@/hooks";
import { MatchCard } from "@/components/MatchCard";
import { PredictionModal } from "@/components/PredictionModal";
import { Spinner, EmptyState } from "@/components/ui";
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

  // Solo partidos pronosticables: programados (la jornada cerrada se filtra abajo).
  const { data: matches, isLoading } = useMatches({
    status: "scheduled",
    phase:  phase !== "all" ? phase : undefined,
  });

  const { data: predictions } = useMyPredictions();

  const predictionByMatch = Object.fromEntries(
    (predictions ?? []).map((p) => [p.match_id, p])
  );

  // Agrupa por día y deja solo las jornadas aún abiertas (las cerradas no se
  // pueden pronosticar; sus resultados se ven en la sección "Resultados").
  const openDays = useMemo(
    () => groupMatchesByDay(matches ?? []).filter((d) => d.open),
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

      {/* Jornadas abiertas (un bloque por día, partidos en filas de 4) */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : !openDays.length ? (
        <EmptyState icon="✅" title={t("matches.emptyTitle")} description={t("matches.emptyDescription")} />
      ) : (
        <div className="space-y-8">
          {openDays.map(({ day, matches: dayMatches }) => (
            <section key={day} className="space-y-3">
              <h2 className="font-display text-xl text-ucl-silver capitalize">
                {format(new Date(`${day}T12:00:00`), "EEEE d 'de' MMMM", { locale: es })}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {dayMatches.map((match) => (
                  <MatchCard
                    key={match.id}
                    match={match}
                    prediction={predictionByMatch[match.id]}
                    onPredict={setSelected}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {selected && (
        <PredictionModal
          match={selected}
          prediction={predictionByMatch[selected.id]}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
