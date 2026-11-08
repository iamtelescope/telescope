# Shared UI pieces (components/common)

App-wide building blocks owned by the app shell. Reuse these instead of hand-rolling states.

## States

| Component | Props | Use for |
|---|---|---|
| `EmptyState.vue` | `icon` (lucide component), `title`, `description` (or `#description` slot), `compact` (smaller paddings, for panels and tables), `card` (bordered, max 600px), `role` (default `status`). Default slot: action buttons. | Empty lists, "no results", not found. |
| `ErrorState.vue` | `title` (default "Something went wrong"), `description`, `error` (string or array, shown monospace), `retry` (shows "Try again", emits `retry`), `compact`, `card`. Default slot: extra actions. | A failed load. Renders `role="alert"`, `data-testid="error-state"`. |
| `LoadingState.vue` | `label` (visible text; without it screen readers still hear "Loading"), `compact`. | A first load with nothing to show yet. Prefer `SkeletonList` for tables. |

```vue
<EmptyState :icon="Bell" title="No alerts yet" description="Alerts notify a channel when a query crosses a threshold.">
    <Button label="New alert" icon="pi pi-plus" size="small" @click="create" />
</EmptyState>
<ErrorState :error="error" retry @retry="load" compact />
```

## Dialogs, toasts and shortcuts

- Destructive actions: `const confirmDestructive = useConfirmDestructive()` from `confirm.js`, then
  `confirmDestructive({ header, message, acceptLabel: 'Delete', accept })`. It uses the `<ConfirmDialog group="app">`
  in `App.vue`, focuses Cancel first and colours the accept button as danger.
- Toasts: `useToast()` from PrimeVue; `App.vue` shows them bottom-right.
- Command palette and shortcut list: set `shell.paletteOpen` / `shell.shortcutsOpen` (`shell.js`). Add a row to
  `SHORTCUTS` in `shell.js` when you add a keyboard shortcut. `isTypingTarget(el)` tells a text field from the page.
- Navigation entries live in `navigation.js` (core) and `features/<name>/nav.js`; the sidebar and the palette both read them.

## Dates and titles

- `datetime.js`: `formatDateTime(value, { zone, ms, withZone })` gives `2026-11-07 14:03:12 UTC`,
  `formatRelative(value)` gives `5 minutes ago`, `formatDuration(ms)` gives `950 ms`, `1.5 s` or `2m 5s`.
  Values may be ISO strings, epoch ms, `Date` or luxon. Empty or invalid values give `—`.
- `DateTimeFormatted.vue`: `value`, `relative` (show "5 minutes ago", full date in the tooltip).
- `pageTitle.js`: the router names each tab from the route; call `setPageTitle(name)` once a view knows a better name
  (e.g. the dashboard's name).
- `Copy.vue`: `value`, `label` (default "Copy to clipboard"); a keyboard-reachable button that shows a check when copied.
