import { useMemo } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useMatches, useMyPredictions } from "@/hooks";
import { MatchCard } from "@/components/MatchCard";
import { Spinner, EmptyState } from "@/components/ui";
import { groupMatchesByDay } from "@/types";
import { useTranslation } from "react-i18next";

export default function ResultsPage() {
  const { data: matches, isLoading } = useMatches();
  const { data: predictions } = useMyPredictions();
  const { t } = useTranslation();

  const predictionByMatch = Object.fromEntries(
    (predictions ?? []).map((p) => [p.match_id, p])
  );

  // Partidos con resultado (en vivo o finalizados), por día y con la jornada
  // más reciente primero. Reutiliza el mismo agrupado que la vista de Partidos.
  const days = useMemo(() => {
    const played = (matches ?? []).filter(
      (m) => m.status === "finished" || m.status === "live"
    );
    return groupMatchesByDay(played).reverse();
  }, [matches]);

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("results.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("results.subtitle")}</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : !days.length ? (
        <EmptyState icon="📊" title={t("results.emptyTitle")} description={t("results.emptyDescription")} />
      ) : (
        <div className="space-y-8">
          {days.map(({ day, matches: dayMatches }) => (
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
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
