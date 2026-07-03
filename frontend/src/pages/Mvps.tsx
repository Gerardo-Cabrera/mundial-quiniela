import { useMatchdays } from "@/hooks";
import { Card, PageLoader, EmptyState } from "@/components/ui";
import { Crown } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { isoDayToDate } from "@/types";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";

const RANK_MEDAL = ["🥇", "🥈", "🥉"];

export default function MvpsPage() {
  const { data, isLoading } = useMatchdays();
  const { t } = useTranslation();

  if (isLoading) {
    return <PageLoader />;
  }

  // El backend envía los días en orden ascendente; se muestran de la jornada más
  // reciente a la más antigua.
  const mvpDays = [...(data?.days ?? [])].reverse().filter((d) => d.mvps.length > 0);
  const ranking = data?.mvp_ranking ?? [];

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("mvps.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("mvps.subtitle")}</p>
      </div>

      {!mvpDays.length ? (
        <EmptyState icon="👑" title={t("mvps.emptyTitle")} description={t("mvps.emptyDescription")} />
      ) : (
        <>
          {/* MVP de cada jornada */}
          <Card>
            <h2 className="font-display text-2xl mb-4 flex items-center gap-2">
              <Crown size={18} className="text-ucl-gold" /> {t("mvps.chronoTitle")}
            </h2>
            <div className="space-y-2">
              {mvpDays.map((d) => (
                <div key={d.date} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-ucl-blue/20">
                  <span className="text-xs text-ucl-silver/60 font-mono capitalize shrink-0 w-20">
                    {format(isoDayToDate(d.date), "d MMM", { locale: es })}
                  </span>
                  <span className="flex-1 min-w-0 text-sm font-medium text-ucl-gold truncate flex items-center gap-1.5">
                    <Crown size={13} className="shrink-0" /> {d.mvps.join(" · ")}
                  </span>
                  <span className="font-display text-lg text-ucl-gold shrink-0">
                    {d.mvp_points}<span className="text-xs text-ucl-silver/50 font-mono ml-1">{t("common.pts")}</span>
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Ranking de MVPs (veces como MVP) */}
          <Card>
            <h2 className="font-display text-2xl mb-4">{t("mvps.rankingTitle")}</h2>
            <div className="space-y-2">
              {ranking.map((r, i) => (
                <div key={r.team_name} className="flex items-center gap-4 px-3 py-2 rounded-lg hover:bg-ucl-blue/20">
                  <span className={clsx(
                    "font-display text-xl w-8 text-center shrink-0",
                    i >= 3 && "text-ucl-silver/50"
                  )}>
                    {i < 3 ? RANK_MEDAL[i] : i + 1}
                  </span>
                  <span className="flex-1 text-sm font-medium text-ucl-white truncate">{r.team_name}</span>
                  <span className="inline-flex items-center gap-1 text-ucl-gold font-mono text-sm font-bold shrink-0">
                    <Crown size={13} /> {t("mvps.rankingCount", { n: r.count })}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
