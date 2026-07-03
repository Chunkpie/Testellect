# 18 — UI Guidelines

## Visual direction

The project summary calls for a "modern dashboard inspired by Linear, Vercel, Notion, Stripe." Concretely, that means:

- **Restrained color palette**: mostly neutral grays/whites (or near-black in dark mode) with a single accent color used sparingly for primary actions and key data highlights — not a UI where every section has a different bright color.
- **Generous whitespace** over dense, cramped layouts — even though this app has a lot of structured data (curriculum trees, question banks, analytics tables), resist the urge to cram everything onto one screen. Use progressive disclosure (expandable tree nodes, drill-down navigation) instead.
- **Typography-led hierarchy**: rely on font weight/size differences for visual hierarchy rather than heavy borders/boxes everywhere. A clean sans-serif (e.g., Inter) for UI chrome.
- **Subtle elevation**: soft shadows and thin borders (not heavy drop-shadows) to separate cards/panels, consistent with shadcn/ui's default aesthetic — lean into shadcn's defaults rather than fighting them.
- **Data density where it matters**: dashboards and tables (Question Bank list, Analytics tables) can be denser than marketing-style pages — Linear/Stripe-style products are dense in their data views and spacious in their settings/forms views; mirror that split here.

## Component library

Build on **shadcn/ui** primitives (per `05-frontend-specification.md`) rather than custom-building buttons/inputs/dialogs/tables from scratch — this is both faster and more consistent. Customize via Tailwind config (colors, radius, font) rather than overriding shadcn component internals extensively.

## Dark mode

Required (per the project summary's explicit "Supports Dark Mode" requirement). Implement via Tailwind's `dark:` variant driven by a class on `<html>`, toggled via the `uiStore` Zustand store (per `05-frontend-specification.md`) and persisted (server-side in `users` settings or at minimum in a cookie/localStorage — note `localStorage` is fine in the actual deployed frontend app, the restriction on `localStorage` in `<persistent_storage_for_artifacts>` only applies to Claude-generated artifacts, not this real application). Test every module in both modes — particularly chart colors and the Question Bank's "AI-generated, unreviewed" badge, which must remain clearly legible/distinct in both themes.

## Status and badge conventions (use consistently across modules)

| Status type | Visual treatment |
|---|---|
| `pending_review` (questions) | Amber/yellow badge, "AI-generated, unreviewed" label — must never look like "approved" |
| `approved` | Green badge |
| `rejected` | Gray/red, struck-through or visually de-emphasized, still visible in audit views |
| `needs_manual_review` (OMR) | Amber badge with a small flag icon |
| Mastery levels (`weak`/`developing`/`proficient`/`advanced`) | A consistent 4-step color ramp (e.g., red → amber → light green → deep green), used identically across every dashboard so a teacher learns it once and reads it everywhere |
| Processing status (books) | A horizontal step-indicator showing pipeline stage progress, not just a spinner — per `05-frontend-specification.md`'s "Live AI Progress" |

## Forms

- React Hook Form + Zod (per `05-frontend-specification.md`) — validation errors appear inline beneath the relevant field, not in a generic top-of-form alert only.
- Multi-step forms (Blueprint Builder) use a visible step indicator and preserve entered data when navigating back/forward between steps.
- Destructive actions (delete student, reject question, restore backup) always require a confirmation dialog with the specific item named in the confirmation text ("Delete student Aarav Patel?" not just "Are you sure?").

## Tables

- Sortable, filterable columns for any list with more than ~20 typical rows (Question Bank, Students, Audit Logs).
- Sticky header row on scroll for long tables.
- Bulk actions (e.g., approve multiple questions at once) via row checkboxes + an action bar that appears once at least one row is selected.

## Charts (Analytics module)

- Recharts (per `05-frontend-specification.md`), styled to match the rest of the app's restrained palette — avoid Recharts' default rainbow color cycling; define an explicit, limited color set tied to meaning (e.g., always use the same mastery-level color ramp from the badge conventions above, not arbitrary chart-library defaults).
- Every chart needs an accessible data table fallback or at minimum clear axis labels and a legend — don't rely on hover tooltips as the only way to read a chart's values, since printed reports (`10-report-engine.md`) can't hover.

## Accessibility baseline

- Sufficient color contrast in both light and dark themes (aim for WCAG AA at minimum) — particularly check this for the status badges and mastery-level color ramp, which carry meaning through color and should also carry a text label, not color alone.
- All interactive elements keyboard-navigable (shadcn/ui's underlying Radix primitives handle most of this correctly by default — don't override away their built-in keyboard handling).
- Form inputs have associated labels (not placeholder-only labeling).

## Empty states

Every list/table view needs a designed empty state (not a blank white panel) — e.g., Question Bank with zero questions yet should prompt "Upload a textbook to get started" with a link to the Books module, not just show an empty table header.

## Loading and error states

- Use skeleton loaders (shadcn/ui has primitives for this) for initial data loads, not spinners, for anything table/card-shaped — better perceived performance.
- Every data-fetching component needs an explicit error state (TanStack Query's `isError`) with a retry action, not a silent blank screen on failure.
