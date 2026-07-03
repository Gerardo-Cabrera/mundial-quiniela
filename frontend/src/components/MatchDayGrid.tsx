import { useMemo } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { clsx } from "clsx";
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
 * Resultados (evita duplicar el render del agrupado por día). El botón
 * "Pronosticar" solo aparece si se pasa `onPredict`.
 */
export function MatchDayGrid({ days, predictions, onPredict, dense }: Props) {
  const predictionByMatch = useMemo(
    () => Object.fromEntries((predictions ?? []).map((p) => [p.match_id, p])),
    [predictions],
  );

  return (
    <div className="space-y-8">
      {days.map(({ day, matches }) => (
        <section key={day} className="space-y-3">
          <h2 className="font-display text-xl text-ucl-silver capitalize">
            {format(isoDayToDate(day), "EEEE d 'de' MMMM", { locale: es })}
          </h2>
          <div className={clsx(
            "grid grid-cols-1 sm:grid-cols-2 gap-4",
            dense ? "lg:grid-cols-3" : "lg:grid-cols-4",
          )}>
            {matches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                prediction={predictionByMatch[match.id]}
                onPredict={onPredict}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
