import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/api/client";
import { Spinner } from "@/components/ui";

/**
 * Cambio de contraseña. Un solo formulario para los dos casos:
 *  - `forced` (primer ingreso, must_change_password): pantalla completa, sin cancelar.
 *  - voluntario (desde el Navbar): tarjeta dentro del layout, con cancelar.
 */
export default function ChangePasswordPage({ forced = false }: { forced?: boolean }) {
  const [current, setCurrent] = useState("");
  const [next, setNext]       = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  const { changePassword, logout } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleSubmit = async () => {
    setError("");
    if (next !== confirm) {
      setError(t("auth.changePassword.mismatch"));
      return;
    }
    if (next.length < 8) {  // misma regla que el backend; evita el 422 y da mensaje claro
      setError(t("auth.changePassword.tooShort"));
      return;
    }
    setLoading(true);
    try {
      await changePassword(current, next);
      toast.success(t("auth.changePassword.success"));
      navigate("/");
    } catch (err: any) {
      setError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setLoading(false);
    }
  };

  const field = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    submitOnEnter = false,
  ) => (
    <div>
      <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{label}</label>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => submitOnEnter && e.key === "Enter" && handleSubmit()}
        placeholder="••••••••"
        className="input-base w-full"
        aria-label={label}
      />
    </div>
  );

  const card = (
    <div className="card border-ucl-gold/20 p-6">
      <h2 className="text-center text-ucl-gold font-display text-2xl tracking-wide mb-1">
        {t("auth.changePassword.title")}
      </h2>
      <p className="text-center text-ucl-silver/70 text-sm mb-6">
        {forced ? t("auth.changePassword.forcedNotice") : t("auth.changePassword.voluntaryHint")}
      </p>

      <div className="space-y-4">
        {field(t("auth.changePassword.current"), current, setCurrent)}
        {field(t("auth.changePassword.new"), next, setNext)}
        {field(t("auth.changePassword.confirm"), confirm, setConfirm, true)}

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
          {loading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("auth.changePassword.submit")}
        </button>

        {forced ? (
          <button
            onClick={() => { logout(); navigate("/login"); }}
            className="w-full text-center text-ucl-silver/60 hover:text-ucl-silver text-sm"
          >
            {t("nav.logout")}
          </button>
        ) : (
          <button
            onClick={() => navigate("/")}
            className="w-full text-center text-ucl-silver/60 hover:text-ucl-silver text-sm"
          >
            {t("auth.changePassword.cancel")}
          </button>
        )}
      </div>
    </div>
  );

  if (forced) {
    return (
      <div className="min-h-screen ucl-stars-bg flex items-center justify-center p-4">
        <div className="w-full max-w-sm">{card}</div>
      </div>
    );
  }
  return <div className="max-w-sm mx-auto">{card}</div>;
}
