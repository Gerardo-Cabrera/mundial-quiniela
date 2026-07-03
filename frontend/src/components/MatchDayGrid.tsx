import { useMemo } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { clsx } from "clsx";
import { Lock } from "lucide-react";
import { useTranslation } from "react-i18next";
import { MatchCard } from "@/components/MatchCard";
import { isoDayToDate, type Match, type MatchDay, type Prediction } from "@/types";

interface Props {
  days: MatchDay[];
  predictions?: Prediction[];
  onPredict?: (match: Match) => void;
  // Resultados tiene tarjetas más densas (marcador real, goleador, puntos): con
  // `dense` usa menos columnas en escritorio para que no se amontonen.
  dense?: boolean;
}

/**
 * Renderiza partidos agrupados por día: una sección por día con cabecera de fecha
 * y una grilla de `MatchCard`. Fuente única usada por las vistas de Partidos y
 * Resultados (evita duplicar el render del agrupado por día). En Partidos (`onPredict`)
 * la jornada YA cerrada sigue visible pero no editable: se marca "Cerrada" y sus
 * tarjetas no reciben `onPredict`.
 */
export function MatchDayGrid({ days, predictions, onPredict, dense }: Props) {
  const { t } = useTranslation();
  const predictionByMatch = useMemo(
    () => Object.fromEntries((predictions ?? []).map((p) => [p.match_id, p])),
    [predictions],
  );

  return (
    <div className="space-y-8">
      {days.map(({ day, matches, open }) => (
        <section key={day} className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="font-display text-xl text-ucl-silver capitalize">
              {format(isoDayToDate(day), "EEEE d 'de' MMMM", { locale: es })}
            </h2>
            {onPredict && !open && (
              <span className="inline-flex items-center gap-1 text-xs text-ucl-silver/50 border border-ucl-silver/20 rounded-full px-2 py-0.5 shrink-0">
                <Lock size={11} /> {t("matches.closed")}
              </span>
            )}
          </div>
          <div className={clsx(
            "grid grid-cols-1 sm:grid-cols-2 gap-4",
            dense ? "lg:grid-cols-3" : "lg:grid-cols-4",
          )}>
            {matches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                prediction={predictionByMatch[match.id]}
                onPredict={open ? onPredict : undefined}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
