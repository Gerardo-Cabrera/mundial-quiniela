import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useUserPredictions } from "@/hooks";
import { PredictionCard } from "@/components/PredictionCard";
import { Spinner, EmptyState } from "@/components/ui";

interface Props {
  userId: number;
  teamName: string;
  onClose: () => void;
}

/**
 * Pronósticos de un participante abiertos desde la Tabla General. El backend solo
 * devuelve los de partidos ya iniciados o finalizados, así que nunca se ven las
 * apuestas de partidos por empezar. Portal a <body> por la misma razón que
 * PredictionModal (los contenedores de página con `.animate-in` crean un
 * containing block que rompería el `position: fixed`).
 */
export function UserPredictionsModal({ userId, teamName, onClose }: Props) {
  const { data: predictions, isLoading } = useUserPredictions(userId);
  const { t } = useTranslation();

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ucl-navy/80 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-lg card border-ucl-gold/25 p-6 shadow-2xl animate-in flex flex-col max-h-[85vh]">
        <button
          onClick={onClose}
          aria-label={t("common.close")}
          className="absolute top-4 right-4 text-ucl-silver/60 hover:text-ucl-white transition-colors"
        >
          <X size={20} />
        </button>

        <h2 className="font-display text-2xl text-ucl-gold mb-1 pr-8 truncate">{teamName}</h2>
        <p className="text-ucl-silver/60 text-sm mb-5">{t("userPredictions.subtitle")}</p>

        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner size="lg" /></div>
        ) : !predictions?.length ? (
          <EmptyState
            icon="🔒"
            title={t("userPredictions.emptyTitle")}
            description={t("userPredictions.emptyDescription")}
          />
        ) : (
          <div className="space-y-3 overflow-y-auto -mr-1 pr-1">
            {predictions.map((pred) => (
              <PredictionCard key={pred.id} pred={pred} />
            ))}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
