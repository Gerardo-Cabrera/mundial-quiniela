import type { FallbackProps } from "react-error-boundary";
import { useTranslation } from "react-i18next";

export function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const { t } = useTranslation();
  return (
    <div className="min-h-screen bg-ucl-navy flex items-center justify-center p-4">
      <div className="card p-8 max-w-md w-full text-center space-y-4">
        <h2 className="font-display text-3xl text-red-400">{t("error.title")}</h2>
        <p className="text-ucl-silver/70 text-sm break-words">
          {error?.message || t("error.unexpected")}
        </p>
        <button
          onClick={resetErrorBoundary}
          className="btn-primary"
          aria-label={t("error.retryAria")}
        >
          {t("error.retry")}
        </button>
      </div>
    </div>
  );
}
