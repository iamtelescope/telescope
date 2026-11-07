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
- `backend/telescope/fetchers/facets.py` (sampled value reads capped by `max_rows_to_read`, the 3e6 default) is adapted from
  HyperDX `packages/common-utils/src/core/metadata.ts`, and `ui/src/components/explorer/FacetSidebar.vue` with
  `ui/src/components/explorer/facets/FacetGroup.vue` (include/exclude, "show more") from
  `packages/app/src/components/DBSearchPageFilters.tsx` (MIT, above).
