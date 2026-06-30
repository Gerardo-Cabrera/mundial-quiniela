import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/api/client";
import { Spinner } from "@/components/ui";

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const { login } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useTranslation();

  // El registro está cerrado (el Mundial ya inició): las cuentas de los 16
  // participantes se aprovisionan por script. Aquí solo se inicia sesión.
  const handleSubmit = async () => {
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err: any) {
      setError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen ucl-stars-bg flex items-center justify-center p-4">
      {/* Stars decorativas */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-ucl-gold/30 rounded-full animate-pulse"
            style={{
              top:  `${Math.random() * 100}%`,
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
            }}
          />
        ))}
      </div>

      <div className="w-full max-w-sm relative">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="font-display text-6xl text-ucl-gold tracking-widest">{t("brand.name")}</h1>
          <p className="text-ucl-silver/70 font-mono text-sm mt-1">{t("brand.tagline")}</p>
          <div className="mt-3 flex justify-center gap-1">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-ucl-gold/40" />
            ))}
          </div>
        </div>

        {/* Card */}
        <div className="card border-ucl-gold/20 p-6 shadow-[0_0_60px_rgba(201,168,76,0.08)]">
          <h2 className="text-center text-ucl-silver text-sm font-mono uppercase tracking-wider mb-6">
            {t("auth.tabLogin")}
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("auth.email")}</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                placeholder={t("auth.emailPlaceholder")}
                className="input-base w-full"
                aria-label={t("auth.emailAria")}
              />
            </div>

            <div>
              <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("auth.password")}</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                placeholder="••••••••"
                className="input-base w-full"
                aria-label={t("auth.password")}
              />
            </div>

            {error && (
              <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
            >
              {loading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("auth.submitLogin")}
            </button>
          </div>
        </div>

        <p className="text-center text-ucl-silver/40 text-xs mt-6 font-mono">
          {t("brand.copyright")}
        </p>
      </div>
    </div>
  );
}
