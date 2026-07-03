import { useMyPredictions, useDeletePrediction } from "@/hooks";
import { PageLoader, EmptyState } from "@/components/ui";
import { PredictionCard } from "@/components/PredictionCard";
import { Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

export default function MyPredictionsPage() {
  const { data: predictions, isLoading } = useMyPredictions();
  const { mutate: deletePred }           = useDeletePrediction();
  const { t } = useTranslation();

  const totalPoints = predictions?.reduce((s, p) => s + p.points_earned, 0) ?? 0;
  const calculated  = predictions?.filter((p) => p.is_calculated).length ?? 0;

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl text-ucl-gold">{t("myPredictions.title")}</h1>
          <p className="text-ucl-silver/60 text-sm mt-1">{t("myPredictions.registered", { n: predictions?.length ?? 0 })}</p>
        </div>
        {calculated > 0 && (
          <div className="text-right">
            <p className="font-display text-4xl text-ucl-gold">{totalPoints}</p>
            <p className="text-xs text-ucl-silver/60 font-mono">{t("myPredictions.matchPoints")}</p>
          </div>
        )}
      </div>

      {isLoading ? (
        <PageLoader />
      ) : !predictions?.length ? (
        <EmptyState
          icon="🎯"
          title={t("myPredictions.emptyTitle")}
          description={t("myPredictions.emptyDescription")}
        />
      ) : (
        <div className="space-y-3">
          {predictions.map((pred) => (
            <PredictionCard
              key={pred.id}
              pred={pred}
              action={!pred.is_calculated && pred.match.status === "scheduled" ? (
                <button
                  onClick={() => deletePred(pred.id)}
                  className="text-ucl-silver/30 hover:text-red-400 transition-colors p-1"
                  title={t("myPredictions.deleteTooltip")}
                >
                  <Trash2 size={15} />
                </button>
              ) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
