import { NavLink, useNavigate } from "react-router-dom";
import { Trophy, CalendarDays, Goal, ListChecks, LogOut, KeyRound, User } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/store/authStore";
import { clsx } from "clsx";

const NAV_ITEMS = [
  { to: "/",            labelKey: "nav.table",       icon: Trophy },
  { to: "/matches",     labelKey: "nav.matches",     icon: CalendarDays },
  { to: "/results",     labelKey: "nav.results",     icon: Goal },
  { to: "/predictions", labelKey: "nav.predictions", icon: ListChecks },
];

export function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col fixed left-0 top-0 h-full w-56 bg-ucl-navy border-r border-ucl-blue/40 z-50">
        {/* Logo */}
        <div className="px-6 py-6 border-b border-ucl-blue/30">
          <h1 className="font-display text-3xl text-ucl-gold tracking-wider">{t("brand.name")}</h1>
          <p className="text-ucl-silver/60 text-xs mt-0.5 font-mono">{t("brand.tagline")}</p>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all duration-150",
                  isActive
                    ? "bg-ucl-gold/15 text-ucl-gold border border-ucl-gold/25"
                    : "text-ucl-silver hover:text-ucl-white hover:bg-ucl-blue/30"
                )
              }
            >
              <Icon size={17} />
              {t(labelKey)}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="px-4 py-4 border-t border-ucl-blue/30">
          <div className="flex items-center gap-2 mb-3 px-2">
            <div className="w-7 h-7 rounded-full bg-ucl-gold/20 border border-ucl-gold/30 flex items-center justify-center">
              <User size={14} className="text-ucl-gold" />
            </div>
            <span className="text-xs text-ucl-silver truncate">{user?.team_name}</span>
          </div>
          <button
            onClick={() => navigate("/change-password")}
            className="w-full flex items-center gap-2 px-2 py-2 mb-2 rounded-lg text-sm text-ucl-silver hover:text-ucl-white hover:bg-ucl-blue/30 transition-colors"
          >
            <KeyRound size={14} /> {t("nav.changePassword")}
          </button>
          <button onClick={handleLogout} className="btn-secondary w-full flex items-center justify-center gap-2 text-sm py-2">
            <LogOut size={14} /> {t("nav.logout")}
          </button>
        </div>
      </aside>

      {/* Mobile bottom nav */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-ucl-navy/95 backdrop-blur border-t border-ucl-blue/40 flex">
        {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex-1 flex flex-col items-center gap-1 py-3 text-xs transition-colors",
                isActive ? "text-ucl-gold" : "text-ucl-silver/60"
              )
            }
          >
            <Icon size={20} />
            <span>{t(labelKey)}</span>
          </NavLink>
        ))}
      </nav>
    </>
  );
}
