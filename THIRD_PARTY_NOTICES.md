# Third-party notices

## HyperDX

`backend/telescope/fetchers/chart.py` (`pick_granularity`, the auto step) is ported from
`convertDateRangeToGranularityString` in HyperDX (`packages/common-utils/src/core/utils.ts`),
https://github.com/hyperdxio/hyperdx

```
MIT License

Copyright (c) 2023 DeploySentinel, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- `dev/otel/schema/compat_logs.sql`, `compat_traces.sql`, `compat_metrics.sql` and `k8s_logs.sql` are adapted from HyperDX
  `docker/otel-collector/schema/seed/00002_otel_logs_compat.sql`, `00005_otel_traces_compat.sql` and `00003_otel_metrics.sql` (MIT, above).
- `backend/telescope_alerts/evaluator.py` (window alignment, threshold comparison, consecutive windows, backfill) is adapted
  from HyperDX `packages/api/src/tasks/checkAlerts/index.ts` (MIT, above).
- `backend/telescope_alerts/templating.py` (message shape, comparators, template variables) is adapted from HyperDX
  `packages/api/src/tasks/checkAlerts/template.ts` and `docs/alert-webhook-template-variables.md` (MIT, above).
- `backend/telescope_alerts/channels/slack.py`, `webhook.py` and `net.py` (Slack payload, generic webhook, idempotency key,
  redirect refusal) are adapted from HyperDX `packages/api/src/tasks/checkAlerts/transports/slack.ts` and `generic.ts` (MIT, above).
- `backend/telescope_alerts/models.py` and `ui/src/features/alerts/useAlerts.js` (threshold types, intervals) follow HyperDX
  `packages/common-utils/src/types.ts` `AlertThresholdType` and `ALERT_INTERVAL_TO_MINUTES` (MIT, above).
- `ui/src/features/alerts/PreviewChart.vue` (threshold shading) is adapted from HyperDX
  `packages/app/src/components/AlertPreviewChart.tsx` (MIT, above).
- `ui/src/composables/useLiveTail.js` adapts the live-tail timer of HyperDX `useLiveUpdate` in
  `packages/app/src/DBSearchPage.tsx` (interval polling, skipped while the tab is hidden or a query runs) (MIT, above).
- `ui/src/utils/context.js` and `ui/src/components/explorer/results/tabs/ContextTab.vue` adapt the context ranges, quick filters
  and match presets of HyperDX `packages/app/src/components/ContextSidePanel.tsx` and `ContextFilterPills.tsx` (MIT, above).
- `backend/telescope/fetchers/facets.py` (sampled value reads capped by `max_rows_to_read`, the 3e6 default) is adapted from
  HyperDX `packages/common-utils/src/core/metadata.ts`, and `ui/src/components/explorer/FacetSidebar.vue` with
  `ui/src/components/explorer/facets/FacetGroup.vue` (include/exclude, "show more") from
  `packages/app/src/components/DBSearchPageFilters.tsx` (MIT, above).
- `backend/telescope/fetchers/chart.py` (`bind_query`) and `ui/src/utils/dashboards.js` (`bindFlyql`) follow the variable semantics of HyperDX
  `packages/common-utils/src/variables.ts` (an empty selection is a no-op) and `types.ts` `DashboardFilterSchema` (MIT, above); no code is copied.
- `backend/telescope_otel/detect.py` (OTel schema detection) and the role list in `backend/telescope_otel/roles.py` are adapted from
  HyperDX `packages/app/src/source.ts` (`inferTableSourceConfig`) and `packages/api/src/models/source.ts` (MIT, above).
- `backend/telescope_alerts/services.py` (silence, evaluations paging, firing-transition markers) and the schedule
  offset/start in `backend/telescope_alerts/evaluator.py` are adapted from HyperDX `packages/api/src/routers/api/alerts.ts`
  and `packages/api/src/tasks/checkAlerts/index.ts` (`getScheduledWindowStart`); `ui/src/features/alerts/AlertDetail.vue`,
  `AlertsView.vue` and `SilenceButton.vue` from `packages/app/src/AlertDetailPage.tsx` and `AlertsPage.tsx` (MIT, above).
- `backend/telescope/fetchers/chart.py` (`parse_formula`, `eval_formula`: the arithmetic grammar, depth and length limits, a missing
  operand as 0 and a zero divisor as null) is adapted from HyperDX `packages/common-utils/src/core/formula.ts`, and the per-series
  `If` combinator in `backend/telescope/fetchers/clickhouse.py` follows `packages/common-utils/src/core/renderChartConfig.ts` (MIT, above).
- `backend/telescope_otel/trace.py` (span tree build, the `Error`/`STATUS_CODE_ERROR` rule, the span cap with a truncated flag) and
  `ui/src/features/traces/TraceWaterfall.vue` (service palette without red/green, collapse) are adapted from HyperDX
  `packages/app/src/components/DBTraceWaterfallChart.tsx`, `traceWaterfallLimits.ts` and `packages/common-utils/src/core/spanPredicates.ts`;
  `ui/src/features/traces/SpanDetail.vue` follows `SpanEventsSubpanel.tsx` and `SpanLinksSubpanel.tsx` (MIT, above).
- `backend/telescope/patterns/mine.py` and `masking.py` (grouping by cluster, sample scaling, trend buckets, body flattening)
  are adapted from HyperDX `packages/common-utils/src/drain/mine-patterns.ts` and `packages/app/src/hooks/usePatterns.tsx`, and
  `ui/src/components/explorer/patterns/PatternTable.vue` with `PatternDrawer.vue` from `packages/app/src/components/PatternTable.tsx`
  and `PatternSidePanel.tsx` (MIT, above).
- `backend/telescope/query_attribution.py` (`log_comment` keys, the character allowlist and length cap) is adapted from HyperDX
  `packages/common-utils/src/clickhouse/attribution.ts`, and `backend/telescope_api2/views.py` (resource shapes, list pagination)
  follows `packages/api/src/routers/external-api/v2/*` (MIT, above).
- `ui/src/components/explorer/results/sections/rowpanel.js` and the row panel sections next to it (top-level attributes,
  exception from attributes or span events, HTTP headers and bodies, span events, pod/node infrastructure correlations and
  their time ranges) are adapted from HyperDX `packages/app/src/components/DBRowOverviewPanel.tsx`, `ExceptionSubpanel.tsx`,
  `HttpMessageSections.tsx`, `SpanEventsSubpanel.tsx`, `DBInfraPanel.tsx` and `infraCorrelations.ts` (MIT, above).

## Drain3

`backend/telescope/patterns/drain.py` is a port of the Drain algorithm from Drain3 (`drain3/drain.py`, version 0.9.11),
https://github.com/logpai/Drain3, also ported by HyperDX as `packages/common-utils/src/drain/drain.ts`.

```
MIT License

Copyright (c) 2020-2022 International Business Machines
and the Drain3 project contributors.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
