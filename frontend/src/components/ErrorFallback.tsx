import type { FallbackProps } from "react-error-boundary";

export function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="min-h-screen bg-ucl-navy flex items-center justify-center p-4">
      <div className="card p-8 max-w-md w-full text-center space-y-4">
        <h2 className="font-display text-3xl text-red-400">Algo salió mal</h2>
        <p className="text-ucl-silver/70 text-sm break-words">
          {error?.message || "Error inesperado en la aplicación."}
        </p>
        <button
          onClick={resetErrorBoundary}
          className="btn-primary"
          aria-label="Reintentar carga de la aplicación"
        >
          Reintentar
        </button>
      </div>
    </div>
  );
}
