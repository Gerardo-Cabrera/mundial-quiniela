import { useMatchdays } from "@/hooks";
import { Card, PageLoader, EmptyState, PointsChip } from "@/components/ui";
import { Crown } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { isoDayToDate } from "@/types";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";

export default function JornadaPage() {
  const { data, isLoading } = useMatchdays();
  const { t } = useTranslation();

  if (isLoading) {
    return <PageLoader />;
  }

  // El backend las envía cronológicas ascendentes; se muestran de la más reciente.
  const days = [...(data?.days ?? [])].reverse();

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("jornada.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("jornada.subtitle")}</p>
      </div>

      {!days.length ? (
        <EmptyState icon="📅" title={t("jornada.emptyTitle")} description={t("jornada.emptyDescription")} />
      ) : (
        days.map((day) => (
          <Card key={day.date}>
            {/* Cabecera: fecha + MVP del día. Apila en móvil. */}
            <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between mb-4">
              <h2 className="font-display text-lg sm:text-xl capitalize">
                {format(isoDayToDate(day.date), "EEEE d 'de' MMMM", { locale: es })}
              </h2>
              {day.mvps.length > 0 && (
                <span className="inline-flex items-center gap-1.5 text-ucl-gold text-xs font-semibold border border-ucl-gold/40 bg-ucl-gold/10 rounded-full px-2.5 py-1 shrink-0 max-w-full">
                  <Crown size={13} className="shrink-0" /> {t("jornada.mvpLabel")}: {day.mvps.join(" · ")}
                </span>
              )}
            </div>

            {/* Puntos por participante ese día */}
            <div className="space-y-1.5">
              {day.entries.map((e) => {
                const isMvp = day.mvp_points > 0 && e.points === day.mvp_points;
                return (
                  <div
                    key={e.user_id}
                    className={clsx(
                      "flex items-center justify-between gap-3 px-3 py-2 rounded-lg",
                      isMvp ? "bg-ucl-gold/10 border border-ucl-gold/20" : "hover:bg-ucl-blue/20"
                    )}
                  >
                    <span className={clsx(
                      "flex-1 min-w-0 text-sm font-medium truncate flex items-center gap-1.5",
                      isMvp ? "text-ucl-gold" : "text-ucl-white"
                    )}>
                      {isMvp && <Crown size={13} className="shrink-0" />}
                      {e.team_name}
                    </span>
                    <PointsChip points={e.points} />
                  </div>
                );
              })}
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
