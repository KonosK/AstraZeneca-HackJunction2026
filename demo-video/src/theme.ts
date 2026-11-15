export const COLORS = {
  bg: "#07131A",
  teal: "#1FA6A0",
  tealDeep: "#0C4F55",
  cyan: "#7EE0D6",
  amber: "#E0A45A",
  slate: "#1B2832",
  glass: "rgba(18, 36, 44, 0.55)",
  text: "#F4F8F7",
  muted: "rgba(244, 248, 247, 0.72)",
  danger: "#E06B6B",
} as const;

export const FPS = 30;

/**
 * VO part A (layers) is ~44s and must finish inside hook+architecture
 * before the live-call chapter. Net duration stays < 118s.
 * Scenes 10+34+36+22+15 = 117s; 4×12f fades ⇒ ~115.4s.
 */
export const TIMING = {
  hook: 10 * FPS,
  architecture: 34 * FPS,
  demo1: 36 * FPS,
  demo2: 22 * FPS,
  outro: 15 * FPS,
  fade: 12,
} as const;

/** Full layer VO length (seconds) — cut after Layer 3, before evidence. */
export const VO_LAYERS_SECONDS = 44;

export const DURATION_FRAMES =
  TIMING.hook +
  TIMING.architecture +
  TIMING.demo1 +
  TIMING.demo2 +
  TIMING.outro -
  TIMING.fade * 4;
