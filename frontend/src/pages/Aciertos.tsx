import { useStats } from "@/hooks";
import { Card, PageLoader, EmptyState, RankingList } from "@/components/ui";
import { Goal } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";

export default function AciertosPage() {
  const { data, isLoading } = useStats();
  const { t } = useTranslation();

  if (isLoading) return <PageLoader />;

  const fgRanking = data?.first_goal_ranking ?? [];
  const exactRanking = data?.exact_ranking ?? [];
  const fgMatches = data?.first_goal_matches ?? [];
  const topScores = data?.top_scores ?? [];

  // Número de aciertos en dorado, común a ambos rankings.
  const count = (n: number) => <span className="font-mono text-sm font-bold text-ucl-gold">{n}</span>;

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("stats.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("stats.subtitle")}</p>
      </div>

      {!fgMatches.length && !exactRanking.length ? (
        <EmptyState icon="🎯" title={t("stats.emptyTitle")} description={t("stats.emptyDescription")} />
      ) : (
        <>
          {/* ── PRIMER GOL ── */}
          <Card>
            <h2 className="font-display text-2xl mb-4 flex items-center gap-2">
              <Goal size={18} className="text-ucl-gold" /> {t("stats.firstGoalRanking")}
            </h2>
            {fgRanking.length
              ? <RankingList entries={fgRanking} renderCount={count} />
              : <p className="text-sm text-ucl-silver/50">{t("stats.noHits")}</p>}
          </Card>

          <Card>
            <h2 className="font-display text-2xl mb-4">{t("stats.firstGoalByMatch")}</h2>
            <div className="space-y-2">
              {fgMatches.map((m) => (
                <div key={m.match_id} className="px-3 py-2 rounded-lg hover:bg-ucl-blue/20">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium truncate">
                      {m.home_team} <span className="text-ucl-silver/40">{t("common.vs")}</span> {m.away_team}
                    </span>
                    <span className="text-xs text-ucl-silver/50 font-mono shrink-0">
                      {format(new Date(m.match_date), "d MMM", { locale: es })}
                    </span>
                  </div>
                  <div className="text-xs text-ucl-silver/60 mt-1">
                    <span>⚽ {m.scorer ?? "—"}</span>
                    {m.hitters.length
                      ? <span className="text-ucl-gold"> · {m.hitters.join(" · ")}</span>
                      : <span className="italic"> · {t("stats.noOneHit")}</span>}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* ── MARCADOR EXACTO ── */}
          <Card>
            <h2 className="font-display text-2xl mb-4">{t("stats.topScore")}</h2>
            {topScores.length ? (
              <div className="flex flex-wrap gap-3">
                {topScores.map((s) => (
                  <div key={s.score} className="inline-flex items-center gap-2 border border-ucl-gold/30 bg-ucl-gold/10 rounded-full px-4 py-1.5">
                    <span className="font-display text-2xl text-ucl-gold">{s.score}</span>
                    <span className="text-xs text-ucl-silver/60 font-mono">{t("stats.timesRepeated", { n: s.count })}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-ucl-silver/50">{t("stats.noHits")}</p>}
          </Card>

          <Card>
            <h2 className="font-display text-2xl mb-4">{t("stats.exactRanking")}</h2>
            {exactRanking.length
              ? <RankingList entries={exactRanking} renderCount={count} />
              : <p className="text-sm text-ucl-silver/50">{t("stats.noHits")}</p>}
          </Card>
        </>
      )}
    </div>
  );
}
