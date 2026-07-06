import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en";
import zhCN from "./locales/zh-CN";

export const SUPPORTED_LANGS = ["zh-CN", "en"] as const;
export type Lang = (typeof SUPPORTED_LANGS)[number];

const saved = (localStorage.getItem("lang") as Lang) || "zh-CN";

i18n.use(initReactI18next).init({
  resources: {
    "zh-CN": { translation: zhCN },
    en: { translation: en },
  },
  lng: saved,
  fallbackLng: "zh-CN",
  interpolation: { escapeValue: false },
});

export default i18n;
