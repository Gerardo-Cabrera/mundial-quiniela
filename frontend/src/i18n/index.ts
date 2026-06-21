import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import es from "./locales/es.json";

/**
 * i18n del frontend: todos los textos visibles viven en archivos de traducción
 * (`locales/*.json`), no hardcodeados en los componentes. Hoy solo español; añadir
 * un idioma = otro JSON + su entrada en `resources` (y un selector si se desea).
 */
export const DEFAULT_LANGUAGE = "es";

i18n.use(initReactI18next).init({
  resources: { es: { translation: es } },
  lng: DEFAULT_LANGUAGE,
  fallbackLng: DEFAULT_LANGUAGE,
  interpolation: { escapeValue: false }, // React ya escapa el contenido
  react: { useSuspense: false },         // recursos en línea → listos de forma síncrona
});

export default i18n;
