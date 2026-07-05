import type { ReactNode } from "react";
import { useStats } from "@/hooks";
import { Card, PageLoader, EmptyState, RankingList } from "@/components/ui";
import { Goal } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";

// Fila de "acierto por partido": partido + fecha, y debajo el detalle (goleador o
// marcador) con los equipos que acertaron. Compartida por las dos secciones.
function HitMatch({ home, away, date, detail, hitters }: {
  home: string; away: string; date: string; detail: ReactNode; hitters: string[];
}) {
  const { t } = useTranslation();
  return (
    <div className="px-3 py-2 rounded-lg hover:bg-ucl-blue/20">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium truncate">
          {home} <span className="text-ucl-silver/40">{t("common.vs")}</span> {away}
        </span>
        <span className="text-xs text-ucl-silver/50 font-mono shrink-0">
          {format(new Date(date), "d MMM", { locale: es })}
        </span>
      </div>
      <div className="text-xs text-ucl-silver/60 mt-1">
        {detail}<span className="text-ucl-gold"> · {hitters.join(" · ")}</span>
      </div>
    </div>
  );
}

export default function AciertosPage() {
  const { data, isLoading } = useStats();
  const { t } = useTranslation();

  if (isLoading) return <PageLoader />;

  const fgRanking = data?.first_goal_ranking ?? [];
  const exactRanking = data?.exact_ranking ?? [];
  const fgMatches = data?.first_goal_matches ?? [];
  const exactMatches = data?.exact_matches ?? [];
  const topScores = data?.top_scores ?? [];

  const hasData = topScores.length || fgRanking.length || exactRanking.length
    || fgMatches.length || exactMatches.length;

  // Número de aciertos en dorado, común a ambos rankings.
  const count = (n: number) => <span className="font-mono text-sm font-bold text-ucl-gold">{n}</span>;

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("stats.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("stats.subtitle")}</p>
      </div>

      {!hasData ? (
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
            {fgMatches.length ? (
              <div className="space-y-2">
                {fgMatches.map((m) => (
                  <HitMatch
                    key={m.match_id} home={m.home_team} away={m.away_team} date={m.match_date}
                    detail={<span>⚽ {m.scorer}</span>} hitters={m.hitters}
                  />
                ))}
              </div>
            ) : <p className="text-sm text-ucl-silver/50">{t("stats.noHits")}</p>}
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

          <Card>
            <h2 className="font-display text-2xl mb-4">{t("stats.exactByMatch")}</h2>
            {exactMatches.length ? (
              <div className="space-y-2">
                {exactMatches.map((m) => (
                  <HitMatch
                    key={m.match_id} home={m.home_team} away={m.away_team} date={m.match_date}
                    detail={<span className="font-mono text-ucl-white">{m.score}</span>} hitters={m.hitters}
                  />
                ))}
              </div>
            ) : <p className="text-sm text-ucl-silver/50">{t("stats.noHits")}</p>}
          </Card>
        </>
      )}
    </div>
  );
}
