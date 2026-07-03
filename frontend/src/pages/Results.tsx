import { useMemo } from "react";
import { useMatches, useMyPredictions } from "@/hooks";
import { MatchDayGrid } from "@/components/MatchDayGrid";
import { PageLoader, EmptyState } from "@/components/ui";
import { groupMatchesByDay } from "@/types";
import { useTranslation } from "react-i18next";

export default function ResultsPage() {
  const { data: matches, isLoading } = useMatches();
  const { data: predictions } = useMyPredictions();
  const { t } = useTranslation();

  // Partidos con resultado (en vivo o finalizados), por día y con la jornada
  // más reciente primero. Reutiliza el mismo agrupado que la vista de Partidos.
  // Dentro de cada jornada, un partido EN VIVO se muestra primero hasta que
  // finaliza, al terminar vuelve a su posición cronológica.
  const days = useMemo(() => {
    const played = (matches ?? []).filter(
      (m) => m.status === "finished" || m.status === "live"
    );
    return groupMatchesByDay(played).reverse().map((day) => ({
      ...day,
      matches: [...day.matches].sort(
        (a, b) => Number(b.status === "live") - Number(a.status === "live")
      ),
    }));
  }, [matches]);

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("results.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("results.subtitle")}</p>
      </div>

      {isLoading ? (
        <PageLoader />
      ) : !days.length ? (
        <EmptyState icon="📊" title={t("results.emptyTitle")} description={t("results.emptyDescription")} />
      ) : (
        <MatchDayGrid days={days} predictions={predictions} />
      )}
    </div>
  );
}
