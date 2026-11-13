import type { Locale } from "./content";

/**
 * GordonKit, the organization this documentation belongs to. Every GordonKit site names the one
 * `@id` that gordonkit.com declares, so search engines and AI assistants see one publisher behind
 * all of them. Shared by the prerendered pages (`seo.ts`) and the app (`App.tsx`).
 */
export const parentOrganization = {
  id: "https://gordonkit.com/#organization",
  name: "GordonKit",
  url: "https://gordonkit.com/",
} as const;

/** gordonkit.com has the same five languages as this site. */
const parentLocalePath: Record<Locale, string> = { en: "en", "en-AU": "en-AU", "zh-TW": "zh-TW", "zh-CN": "zh-CN", ja: "ja" };

export function parentSiteUrl(locale: Locale): string {
  return `${parentOrganization.url}${parentLocalePath[locale]}/`;
}

/** The footer text before the gordonkit.com link. */
export const parentSiteLabel: Record<Locale, string> = {
  en: "A GordonKit project:",
  "en-AU": "A GordonKit project:",
  "zh-TW": "GordonKit 旗下網站：",
  "zh-CN": "GordonKit 旗下网站：",
  ja: "GordonKit のプロジェクト：",
};
