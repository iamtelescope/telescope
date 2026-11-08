<template>
    <Dialog
        :visible="visible"
        @update:visible="(v) => (v ? emit('update:visible', true) : requestClose())"
        modal
        :closeOnEscape="false"
        :style="{ width: '95vw', maxWidth: '1600px' }"
        :breakpoints="{ '960px': '98vw' }"
        :pt="{ content: { class: 'pb-0' } }"
        data-testid="tile-editor"
    >
        <template #header>
            <div class="flex flex-col">
                <span class="text-xl font-semibold">{{ isNew ? 'New tile' : 'Edit tile' }}</span>
                <span class="text-sm text-surface-500 dark:text-surface-400">
                    The preview updates as you edit; Esc closes
                </span>
            </div>
        </template>
        <div v-if="form" class="flex flex-col lg:flex-row gap-5 lg:h-[72vh]">
            <div class="flex flex-col gap-4 lg:w-[30rem] shrink-0 lg:overflow-y-auto lg:pr-2 pb-2">
                <div class="flex flex-col gap-1">
                    <label for="tile_title" class="font-medium">Title</label>
                    <InputText
                        id="tile_title"
                        v-model="form.title"
                        size="small"
                        maxlength="128"
                        placeholder="Untitled tile"
                        autofocus
                        @keydown.enter="runPreview"
                    />
                </div>
                <div class="flex flex-col gap-1">
                    <label for="tile_description" class="font-medium">
                        Description <span class="font-normal text-surface-500">(optional)</span>
                    </label>
                    <Textarea
                        id="tile_description"
                        v-model="form.description"
                        rows="1"
                        autoResize
                        size="small"
                        maxlength="1024"
                        placeholder="Shown as a hint next to the title"
                        data-testid="tile-description-input"
                    />
                </div>
                <div v-if="sectionOptions.length > 1" class="flex flex-col gap-1">
                    <label class="font-medium">Section</label>
                    <Select
                        v-model="form.section"
                        :options="sectionOptions"
                        optionLabel="label"
                        optionValue="value"
                        size="small"
                        data-testid="tile-section"
                    />
                </div>
                <div class="flex flex-col gap-1">
                    <label class="font-medium">Display</label>
                    <div class="grid grid-cols-6 gap-1" role="radiogroup" data-testid="tile-display">
                        <button
                            v-for="d in displayButtons"
                            :key="d.value"
                            type="button"
                            role="radio"
                            :aria-checked="chart.display === d.value"
                            :data-display="d.value"
                            class="flex flex-col items-center gap-1 py-2 rounded-md border text-xs transition-colors"
                            :class="
                                chart.display === d.value
                                    ? 'border-primary bg-highlight font-medium'
                                    : 'border-surface-200 dark:border-surface-700 text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800'
                            "
                            @click="setDisplay(d.value)"
                        >
                            <component :is="d.icon" class="w-5 h-5" :stroke-width="1.75" />
                            {{ d.label }}
                        </button>
                    </div>
                </div>

                <div v-if="chart.display === 'text'" class="flex flex-col gap-1">
                    <label for="tile_text" class="font-medium">Text</label>
                    <Textarea
                        id="tile_text"
                        v-model="chart.text"
                        rows="12"
                        maxlength="10000"
                        autoResize
                        placeholder="Notes for this dashboard"
                    />
                </div>
                <RawSqlFields
                    v-else-if="chart.display === 'sql'"
                    :chart="chart"
                    :validation="preview.validation.value"
                    @submit="runPreview"
                />
                <template v-else>
                    <div class="flex flex-col gap-1">
                        <label class="font-medium">Source</label>
                        <Select
                            v-model="chart.source"
                            :options="sources"
                            optionLabel="name"
                            optionValue="slug"
                            filter
                            size="small"
                            placeholder="Choose a source"
                            :invalid="!!sourceError"
                            @change="onSourceChange"
                        >
                            <template #option="{ option }">
                                <div class="flex items-center">
                                    <img
                                        :src="require(`@/assets/${option.kind}.png`)"
                                        height="16px"
                                        width="16px"
                                        class="mr-2"
                                    />
                                    {{ option.name }} <span class="ml-2 text-surface-500">{{ option.slug }}</span>
                                </div>
                            </template>
                        </Select>
                        <ErrorText v-if="sourceError" :text="sourceError" class="text-sm" />
                    </div>

                    <template v-if="source">
                        <div v-if="!logTile" class="flex flex-col gap-1">
                            <div class="flex items-center justify-between">
                                <label class="font-medium">Series</label>
                                <Button
                                    icon="pi pi-plus"
                                    label="Add series"
                                    text
                                    size="small"
                                    :disabled="chart.series.length >= maxSeries"
                                    v-tooltip.top="
                                        chart.series.length >= maxSeries ? `At most ${maxSeries} series here` : null
                                    "
                                    @click="addSeries"
                                />
                            </div>
                            <div
                                v-for="(s, idx) in chart.series"
                                :key="idx"
                                class="flex flex-col gap-1 pb-2 border-b border-surface-100 dark:border-surface-800 last:border-0"
                                :class="{ 'opacity-60': s.hidden }"
                                data-testid="tile-series"
                            >
                                <div class="flex items-center gap-1">
                                    <Select
                                        v-model="s.agg"
                                        :options="aggOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        optionDisabled="disabled"
                                        size="small"
                                        class="w-32 shrink-0"
                                        data-testid="series-agg"
                                        @change="onAggChange(s)"
                                    />
                                    <MetricNamePicker
                                        v-if="s.agg === 'metric'"
                                        :source="chart.source"
                                        :range="props.range"
                                        :modelValue="s.metric"
                                        :invalid="!!seriesErrors[idx]"
                                        class="flex-1 min-w-0"
                                        @update:modelValue="(m) => setMetric(s, m)"
                                    />
                                    <InputText
                                        v-else-if="s.agg === 'formula'"
                                        v-model="s.formula"
                                        size="small"
                                        class="flex-1 min-w-0 font-mono"
                                        :placeholder="formulaExample"
                                        maxlength="1024"
                                        aria-label="Formula"
                                        data-testid="series-formula"
                                        :invalid="!!seriesErrors[idx]"
                                        @keydown.enter="runPreview"
                                    />
                                    <Select
                                        v-else
                                        v-model="s.column"
                                        :options="columnOptions(s.agg)"
                                        filter
                                        size="small"
                                        class="flex-1 min-w-0"
                                        :placeholder="s.agg === 'count' ? 'all rows' : 'Column'"
                                        :disabled="s.agg === 'count'"
                                        :invalid="!!seriesErrors[idx]"
                                    />
                                    <Select
                                        v-if="s.agg === 'quantile'"
                                        v-model="s.level"
                                        :options="QUANTILE_LEVELS"
                                        size="small"
                                        class="w-24 shrink-0"
                                    />
                                    <label
                                        v-if="!isHeatmap"
                                        class="series-color relative shrink-0 w-6 h-6 rounded border border-surface-300 dark:border-surface-600 cursor-pointer"
                                        :style="{ background: s.color || 'transparent' }"
                                        v-tooltip.top="s.color ? 'Series color' : 'Automatic color'"
                                    >
                                        <i v-if="!s.color" class="pi pi-palette text-xs text-surface-500 m-auto"></i>
                                        <input
                                            type="color"
                                            class="absolute inset-0 opacity-0 cursor-pointer"
                                            :value="s.color || '#2a78d6'"
                                            aria-label="Series color"
                                            @input="(e) => (s.color = e.target.value)"
                                        />
                                    </label>
                                    <Button
                                        v-if="s.color"
                                        icon="pi pi-replay"
                                        text
                                        size="small"
                                        severity="secondary"
                                        class="shrink-0 w-6 h-6 p-0"
                                        aria-label="Automatic color"
                                        v-tooltip.top="'Automatic color'"
                                        @click="delete s.color"
                                    />
                                    <Button
                                        v-if="!isHeatmap"
                                        :icon="s.hidden ? 'pi pi-eye-slash' : 'pi pi-eye'"
                                        text
                                        size="small"
                                        severity="secondary"
                                        class="shrink-0"
                                        :aria-label="s.hidden ? 'Show series' : 'Hide series'"
                                        v-tooltip.top="
                                            s.hidden ? 'Hidden: only used by formulas' : 'Hide, e.g. a formula operand'
                                        "
                                        data-testid="series-hide"
                                        @click="s.hidden = !s.hidden"
                                    />
                                    <Button
                                        icon="pi pi-times"
                                        text
                                        size="small"
                                        severity="secondary"
                                        class="shrink-0"
                                        :disabled="chart.series.length < 2"
                                        aria-label="Remove series"
                                        @click="chart.series.splice(idx, 1)"
                                    />
                                </div>
                                <div class="flex items-center gap-1">
                                    <Select
                                        v-if="s.agg === 'metric'"
                                        v-model="s.metric.agg"
                                        :options="metricAggOptions(s.metric.type)"
                                        optionLabel="label"
                                        optionValue="value"
                                        size="small"
                                        class="w-28 shrink-0"
                                        data-testid="metric-agg"
                                    />
                                    <InputText
                                        v-if="!isHeatmap"
                                        v-model="s.alias"
                                        size="small"
                                        :class="s.agg === 'metric' ? 'w-28' : 'w-40'"
                                        class="shrink-0"
                                        :placeholder="`Alias: ${seriesLabel(s)}`"
                                        maxlength="64"
                                        aria-label="Alias"
                                        data-testid="series-alias"
                                        @keydown.enter="runPreview"
                                    />
                                    <InputText
                                        v-if="s.agg === 'metric'"
                                        v-model="s.metric.attrs_filter"
                                        size="small"
                                        class="flex-1 min-w-0 font-mono"
                                        placeholder="Only points where… e.g. Attributes.'http.route' = '/'"
                                        maxlength="10000"
                                        aria-label="Attribute filter"
                                        data-testid="metric-attrs-filter"
                                        @keydown.enter="runPreview"
                                    />
                                    <InputText
                                        v-else-if="s.agg !== 'formula' && !countOnly"
                                        v-model="s.where"
                                        size="small"
                                        class="flex-1 min-w-0 font-mono"
                                        placeholder="Only rows where… (FlyQL)"
                                        maxlength="10000"
                                        aria-label="Series filter"
                                        data-testid="series-where"
                                        @keydown.enter="runPreview"
                                    />
                                </div>
                                <ErrorText v-if="seriesErrors[idx]" :text="seriesErrors[idx]" class="text-sm" />
                            </div>
                            <span v-if="hasFormula" class="text-xs text-surface-500 dark:text-surface-400">
                                Formulas use + - * / and parentheses over series aliases; a zero divisor gives no value.
                            </span>
                            <ErrorText v-if="seriesListError" :text="seriesListError" class="text-sm" />
                        </div>

                        <div v-if="source.contextColumns && countOnly" class="flex flex-col gap-1">
                            <label class="font-medium">Context</label>
                            <ContextColumns
                                :key="source.slug"
                                :source="source"
                                :contextColumns="chart.context_columns"
                                :contextColumnsData="contextColumnsData"
                                @columnChanged="(p) => (chart.context_columns[p.name] = p.value)"
                            />
                        </div>

                        <div class="flex flex-col gap-1">
                            <label class="font-medium">Filter</label>
                            <QueryEditor
                                :key="source.slug"
                                :source="source"
                                :value="chart.query"
                                :from="range.from"
                                :to="range.to"
                                :placeholder="queryExample"
                                @change="(v) => (chart.query = v)"
                                @submit="runPreview"
                            />
                            <ErrorText v-if="serverError('query')" :text="serverError('query')" class="text-sm" />
                        </div>

                        <div v-if="chart.display === 'search'" class="grid grid-cols-[1fr_auto] gap-3">
                            <div class="flex flex-col gap-1 min-w-0">
                                <label for="tile_columns" class="font-medium">
                                    Columns <span class="font-normal text-surface-500">(optional)</span>
                                </label>
                                <InputText
                                    id="tile_columns"
                                    v-model="chart.columns"
                                    size="small"
                                    class="font-mono"
                                    maxlength="10000"
                                    :placeholder="defaultColumns"
                                    data-testid="tile-columns"
                                    @keydown.enter="runPreview"
                                />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="font-medium">Rows per page</label>
                                <InputNumber
                                    v-model="chart.limit"
                                    :min="1"
                                    :max="SEARCH_TILE_MAX_LIMIT"
                                    size="small"
                                    inputClass="w-16"
                                    showButtons
                                    data-testid="tile-page-size"
                                    @keydown.enter="runPreview"
                                />
                            </div>
                        </div>
                        <div v-else-if="chart.display === 'patterns'" class="grid grid-cols-[1fr_auto] gap-3">
                            <div class="flex flex-col gap-1 min-w-0">
                                <label class="font-medium">Pattern column</label>
                                <Select
                                    v-model="chart.column"
                                    :options="patternColumns(source)"
                                    filter
                                    showClear
                                    size="small"
                                    :placeholder="bodyColumn(source) || 'Choose a column'"
                                    data-testid="tile-pattern-column"
                                />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="font-medium">Sample</label>
                                <Select
                                    v-model="chart.sample"
                                    :options="sampleOptions"
                                    optionLabel="label"
                                    optionValue="value"
                                    size="small"
                                    data-testid="tile-pattern-sample"
                                />
                            </div>
                        </div>
                        <template v-else>
                            <div class="grid grid-cols-[1fr_auto] gap-3">
                                <div class="flex flex-col gap-1 min-w-0">
                                    <label class="font-medium" :class="{ 'opacity-50': !usesGroupBy }">
                                        Group by
                                        <span v-if="!groupRequired" class="font-normal text-surface-500"
                                            >(optional)</span
                                        >
                                    </label>
                                    <div v-for="(g, idx) in groupBys" :key="idx" class="flex items-center gap-1">
                                        <Select
                                            :modelValue="g ? { name: g } : null"
                                            :options="groupByOptions"
                                            optionLabel="name"
                                            editable
                                            :showClear="!!g && usesGroupBy"
                                            size="small"
                                            class="flex-1 min-w-0"
                                            :disabled="!usesGroupBy"
                                            :placeholder="usesGroupBy ? 'None' : `Not used by ${displayLabel}`"
                                            :invalid="!!groupByError"
                                            data-testid="tile-group-by"
                                            @change="(e) => onGroupByChange(idx, e)"
                                        />
                                        <Button
                                            v-if="idx > 0"
                                            icon="pi pi-times"
                                            text
                                            size="small"
                                            severity="secondary"
                                            aria-label="Remove group by column"
                                            @click="groupBys.splice(idx, 1)"
                                        />
                                    </div>
                                    <Button
                                        v-if="usesGroupBy && groupBys.length < maxGroupBy && groupBys[0]"
                                        icon="pi pi-plus"
                                        label="Group by column"
                                        text
                                        size="small"
                                        class="self-start py-0"
                                        data-testid="tile-add-group-by"
                                        @click="groupBys.push('')"
                                    />
                                    <ErrorText v-if="groupByError" :text="groupByError" class="text-sm" />
                                </div>
                                <div class="flex flex-col gap-1">
                                    <label class="font-medium" :class="{ 'opacity-50': !usesLimit }">Top groups</label>
                                    <InputNumber
                                        v-model="chart.limit"
                                        :min="1"
                                        :max="maxLimit(chart.display)"
                                        size="small"
                                        inputClass="w-16"
                                        showButtons
                                        :disabled="!usesLimit"
                                        :invalid="!!limitError"
                                        v-tooltip.top="`Groups to keep, 1..${maxLimit(chart.display)}`"
                                        @keydown.enter="runPreview"
                                    />
                                </div>
                            </div>
                            <ErrorText v-if="limitError" :text="limitError" class="text-sm -mt-3" />

                            <div class="grid grid-cols-3 gap-3">
                                <div class="flex flex-col gap-1">
                                    <label class="font-medium" :class="{ 'opacity-50': !timeseries && !isHeatmap }">
                                        Granularity
                                    </label>
                                    <Select
                                        v-model="chart.granularity"
                                        :options="granularityOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        size="small"
                                        :disabled="!timeseries && !isHeatmap"
                                    />
                                </div>
                                <div class="flex flex-col gap-1">
                                    <label class="font-medium" :class="{ 'opacity-50': !hasUnit }">Unit</label>
                                    <Select
                                        v-model="numberFormat.unit"
                                        :options="unitOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        size="small"
                                        :disabled="!hasUnit"
                                        data-testid="tile-unit"
                                    />
                                </div>
                                <div class="flex flex-col gap-1">
                                    <label class="font-medium" :class="{ 'opacity-50': !hasNumberFormat }"
                                        >Decimals</label
                                    >
                                    <InputNumber
                                        v-model="numberFormat.decimals"
                                        :min="0"
                                        :max="6"
                                        size="small"
                                        fluid
                                        showButtons
                                        :disabled="!hasNumberFormat"
                                    />
                                </div>
                            </div>
                            <div v-if="hasUnit" class="grid grid-cols-3 gap-3 -mt-2">
                                <InputText
                                    v-model="numberFormat.prefix"
                                    size="small"
                                    maxlength="16"
                                    placeholder="Prefix, e.g. $"
                                    aria-label="Prefix"
                                />
                                <InputText
                                    v-model="numberFormat.suffix"
                                    size="small"
                                    maxlength="16"
                                    placeholder="Suffix, e.g. req/s"
                                    aria-label="Suffix"
                                    data-testid="tile-suffix"
                                />
                                <label class="flex items-center gap-2 text-sm">
                                    <Checkbox v-model="numberFormat.compact" binary inputId="tile_compact" />
                                    <span>Compact (1.2K)</span>
                                </label>
                            </div>

                            <div v-if="timeseries || chart.display === 'number'" class="flex flex-wrap gap-x-5 gap-y-2">
                                <label class="flex items-center gap-2 text-sm">
                                    <Checkbox v-model="chart.compare" binary data-testid="tile-compare" />
                                    <span>Compare to the previous period</span>
                                </label>
                                <label v-if="chart.display === 'number'" class="flex items-center gap-2 text-sm">
                                    <Checkbox v-model="chart.sparkline" binary data-testid="tile-sparkline" />
                                    <span>Sparkline</span>
                                </label>
                            </div>
                        </template>

                        <div v-if="hasColorRules" class="flex flex-col gap-1">
                            <div class="flex items-center justify-between">
                                <label class="font-medium">
                                    Color rules <span class="font-normal text-surface-500">(first match wins)</span>
                                </label>
                                <Button
                                    icon="pi pi-plus"
                                    label="Rule"
                                    text
                                    size="small"
                                    :disabled="colorRules.length >= 10"
                                    data-testid="tile-add-color-rule"
                                    @click="colorRules.push({ op: 'gt', value: 0, color: '#e34948' })"
                                />
                            </div>
                            <div
                                v-for="(rule, idx) in colorRules"
                                :key="idx"
                                class="flex items-center gap-1"
                                data-testid="tile-color-rule"
                            >
                                <span class="text-sm text-surface-500 w-12 shrink-0">value</span>
                                <Select
                                    v-model="rule.op"
                                    :options="COLOR_RULE_OPS"
                                    optionLabel="label"
                                    optionValue="value"
                                    size="small"
                                    class="w-20 shrink-0"
                                />
                                <InputNumber
                                    v-model="rule.value"
                                    size="small"
                                    class="flex-1 min-w-0"
                                    inputClass="w-full"
                                    :maxFractionDigits="6"
                                    aria-label="Rule value"
                                />
                                <label
                                    class="relative shrink-0 w-6 h-6 rounded border border-surface-300 dark:border-surface-600 cursor-pointer"
                                    :style="{ background: rule.color }"
                                >
                                    <input
                                        type="color"
                                        class="absolute inset-0 opacity-0 cursor-pointer"
                                        :value="rule.color"
                                        aria-label="Rule color"
                                        @input="(e) => (rule.color = e.target.value)"
                                    />
                                </label>
                                <Button
                                    icon="pi pi-times"
                                    text
                                    size="small"
                                    severity="secondary"
                                    aria-label="Remove rule"
                                    @click="colorRules.splice(idx, 1)"
                                />
                            </div>
                        </div>

                        <div v-if="source.isRawQueryAllowed()" class="flex flex-col gap-2">
                            <button
                                type="button"
                                class="flex items-center gap-2 text-sm font-medium text-surface-600 dark:text-surface-300 hover:text-primary self-start"
                                data-testid="tile-advanced"
                                @click="advancedOpen = !advancedOpen"
                            >
                                <i
                                    :class="advancedOpen ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
                                    class="text-xs"
                                />
                                Advanced
                                <Tag v-if="!advancedOpen && chart.raw_query" value="SQL" severity="secondary" />
                            </button>
                            <div v-if="advancedOpen" class="flex flex-col gap-1">
                                <label class="font-medium">Raw SQL condition</label>
                                <span class="text-sm text-surface-500 dark:text-surface-400">
                                    Added to the WHERE clause together with the filter
                                </span>
                                <RawQueryEditor
                                    :key="source.slug"
                                    :source="source"
                                    :value="chart.raw_query"
                                    @change="(v) => (chart.raw_query = v)"
                                    @submit="runPreview"
                                />
                                <ErrorText
                                    v-if="serverError('raw_query')"
                                    :text="serverError('raw_query')"
                                    class="text-sm"
                                />
                            </div>
                        </div>
                    </template>
                </template>
            </div>

            <div class="flex flex-col flex-1 min-w-0 gap-2 pb-2">
                <div class="flex items-center justify-between gap-2 min-h-8">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="font-medium">Preview</span>
                        <span v-if="chart.display !== 'text'" class="text-sm text-surface-500 truncate">
                            {{ rangeLabel }}
                        </span>
                    </div>
                    <Button
                        v-if="chart.display !== 'text'"
                        label="Run"
                        icon="pi pi-play"
                        size="small"
                        outlined
                        :disabled="!canPreview"
                        :loading="preview.loading.value"
                        data-testid="tile-run"
                        @click="runPreview"
                    />
                </div>
                <div
                    class="flex-1 min-h-[24rem] border rounded-lg border-surface-200 dark:border-surface-700 p-3 bg-surface-0 dark:bg-surface-900"
                    data-testid="tile-editor-preview"
                >
                    <div class="h-full flex flex-col">
                        <div v-if="form.title" class="font-medium mb-2 truncate">{{ form.title }}</div>
                        <div class="flex-1 min-h-0">
                            <LogTileView
                                v-if="previewChart && !problem && isLogTile(previewChart.display)"
                                :chart="previewChart"
                                :range="range"
                                :timeZone="timeZone"
                            />
                            <ChartView
                                v-else-if="chart.display === 'text' || (previewChart && !problem)"
                                :chart="chart.display === 'text' ? chart : previewChart"
                                :data="preview.data.value"
                                :loading="preview.loading.value"
                                :error="preview.error.value"
                                :code="preview.code.value"
                                :validation="preview.validation.value"
                                :timeZone="timeZone"
                                @retry="runPreview"
                            />
                            <div
                                v-else
                                class="flex flex-col items-center justify-center h-full gap-2 text-sm text-surface-500"
                            >
                                <i class="pi pi-chart-line text-2xl opacity-60" />
                                {{ problem || 'The preview updates as you edit' }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <template #footer>
            <div class="flex items-center justify-end gap-2 w-full pt-3">
                <Button label="Cancel" severity="secondary" outlined size="small" @click="requestClose" />
                <Button
                    :label="isNew ? 'Add tile' : 'Apply'"
                    size="small"
                    :disabled="!!problem"
                    data-testid="tile-apply"
                    @click="onApply"
                />
            </div>
        </template>
    </Dialog>
    <ConfirmDialog group="tile-editor" />
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import {
    Dialog,
    Button,
    Checkbox,
    ConfirmDialog,
    InputText,
    InputNumber,
    Select,
    Tag,
    Textarea,
    useConfirm,
} from 'primevue'
import { useDebounceFn } from '@vueuse/core'
import {
    ChartArea,
    ChartBarBig,
    ChartColumnStacked,
    ChartLine,
    ChartPie,
    Code,
    Grid3x3,
    Hash,
    ScrollText,
    Shapes,
    Sheet,
    Type,
} from 'lucide-vue-next'

import ErrorText from '@/components/common/ErrorText.vue'
import ChartView from '@/components/dashboards/ChartView.vue'
import LogTileView from '@/components/dashboards/charts/LogTileView.vue'
import { PATTERN_SAMPLES } from '@/components/dashboards/charts/logTiles'
import { PATTERN_KINDS, patternColumns } from '@/components/explorer/patterns/patterns'
import { bodyColumn } from '@/utils/explorerPaging'
import ContextColumns from '@/components/explorer/controls/ContextColumns.vue'
import MetricNamePicker from '@/components/dashboards/metrics/MetricNamePicker.vue'
import {
    METRIC_AGGS,
    METRIC_AGG_LABELS,
    defaultMetricAgg,
    isMetricsSource,
    metricLabel,
    useMetricAttributes,
} from '@/components/dashboards/metrics/metrics'
import QueryEditor from '@/components/explorer/controls/QueryEditor.vue'
import RawQueryEditor from '@/components/explorer/controls/RawQueryEditor.vue'
import RawSqlFields from '@/features/rawsql/RawSqlFields.vue'
import { RAW_SQL_EXAMPLE, rawSqlBody, useTileData } from '@/features/rawsql/service.js'
import { durationUnit } from '@/components/dashboards/charts/heatmap.js'
import { rangeText } from '@/components/dashboards/charts/format.js'
import { SourceService } from '@/sdk/services/source'
import {
    AGGS,
    COLOR_RULE_OPS,
    DISPLAYS,
    GRANULARITIES,
    MAX_GROUP_BY,
    MAX_SERIES,
    NUMBER_UNITS,
    QUANTILE_LEVELS,
    SEARCH_TILE_MAX_LIMIT,
    SINGLE_SERIES_DISPLAYS,
    countOnlyKind,
    isLogTile,
    isNumericType,
    isTimeseries,
    maxLimit,
} from '@/utils/dashboards.js'

// `sections` are the dashboard's sections, so the tile can be placed in one; `rawSql` offers the SQL display.
const props = defineProps(['visible', 'tile', 'sources', 'range', 'timeZone', 'sections', 'rawSql'])
const emit = defineEmits(['update:visible', 'apply'])

const ICONS = {
    line: ChartLine,
    stacked_area: ChartArea,
    stacked_bar: ChartColumnStacked,
    number: Hash,
    table: Sheet,
    bar: ChartBarBig,
    pie: ChartPie,
    search: ScrollText,
    patterns: Shapes,
    heatmap: Grid3x3,
    text: Type,
    sql: Code,
}
const UNIT_LABELS = {
    number: 'number',
    bytes: 'bytes (KiB)',
    bytes_si: 'bytes (kB)',
    duration_ns: 'duration ns',
    duration_us: 'duration µs',
    duration_ms: 'duration ms',
    duration_s: 'duration s',
    percent: 'percent',
}
const unitOptions = NUMBER_UNITS.map((u) => ({ value: u, label: UNIT_LABELS[u] || u }))
// The heatmap sits before Text; it draws one numeric column over time on ClickHouse sources.
const DISPLAY_BUTTONS = [
    ...DISPLAYS.filter((d) => d.value !== 'text'),
    { value: 'heatmap', label: 'Heatmap' },
    ...DISPLAYS.filter((d) => d.value === 'text'),
].map((d) => ({ ...d, icon: ICONS[d.value] }))
const displayButtons = computed(() =>
    props.rawSql ? [...DISPLAY_BUTTONS, { value: 'sql', label: 'SQL', icon: Code }] : DISPLAY_BUTTONS,
)

const sourceSrv = new SourceService()
const preview = useTileData()
const confirm = useConfirm()

const form = ref(null)
const numberFormat = ref({ unit: 'number', decimals: 0 })
const contextColumnsData = ref(null)
const groupBys = ref([''])
const colorRules = ref([])
const previewChart = ref(null)
const advancedOpen = ref(false)
const confirming = ref(false)
let snapshot = ''

const isNew = computed(() => !props.tile?.id)
const chart = computed(() => form.value.chart)
const source = computed(() => (props.sources || []).find((s) => s.slug === chart.value.source) || null)
const countOnly = computed(() => !!source.value && countOnlyKind(source.value.kind))
const metrics = computed(() => isMetricsSource(source.value))
const metricAttributes = useMetricAttributes()
const isHeatmap = computed(() => chart.value.display === 'heatmap')
const logTile = computed(() => isLogTile(chart.value.display))
const sampleOptions = PATTERN_SAMPLES.map((value) => ({ label: value.toLocaleString(), value }))
const defaultColumns = computed(() => {
    const columns = source.value?.defaultChosenColumns || []
    return `Default: ${Array.isArray(columns) ? columns.join(', ') : columns}`
})
const maxSeries = computed(() => (isHeatmap.value ? 1 : MAX_SERIES))
const displayLabel = computed(() => DISPLAY_BUTTONS.find((d) => d.value === chart.value.display)?.label || '')
const singleSeries = computed(() => SINGLE_SERIES_DISPLAYS.includes(chart.value.display))
const groupRequired = computed(() => ['bar', 'pie'].includes(chart.value.display))
const maxGroupBy = computed(() => (countOnly.value ? 1 : MAX_GROUP_BY))
const hasNumberFormat = computed(() => ['number', 'table', 'bar', 'pie'].includes(chart.value.display))
const hasColorRules = computed(() => ['number', 'table', 'bar'].includes(chart.value.display))
const hasFormula = computed(() => chart.value.series.some((s) => s.agg === 'formula'))
const sectionOptions = computed(() => [
    { value: '', label: 'No section' },
    ...(props.sections || []).map((s) => ({ value: s.id, label: s.title || 'Untitled section' })),
])
const timeseries = computed(() => isTimeseries(chart.value.display))
const hasUnit = computed(() => hasNumberFormat.value || timeseries.value || isHeatmap.value)
const usesGroupBy = computed(() => !['number', 'heatmap'].includes(chart.value.display))
const usesLimit = computed(() => usesGroupBy.value && !!chart.value.group_by)
const granularityOptions = GRANULARITIES.map((g) => ({ value: g, label: g === 'auto' ? 'Auto' : g }))
const rangeLabel = computed(() => (props.range ? rangeText(props.range.from, props.range.to, props.timeZone) : ''))

const defaultChart = () => ({
    source: props.sources?.[0]?.slug || '',
    display: 'line',
    series: [{ agg: 'count' }],
    query: '',
    raw_query: '',
    context_columns: {},
    group_by: '',
    granularity: 'auto',
    limit: 10,
    columns: '',
    column: '',
    sample: 10000,
})

const state = () => JSON.stringify([form.value, numberFormat.value, groupBys.value, colorRules.value])

const splitGroupBy = (value) =>
    (value || '')
        .split(',')
        .map((g) => g.trim())
        .filter(Boolean)

const init = () => {
    const tile = props.tile ? JSON.parse(JSON.stringify(props.tile)) : {}
    const base = { ...defaultChart(), text: '', ...tile.chart }
    form.value = {
        title: tile.title || '',
        description: tile.description || '',
        section: tile.section || '',
        chart: base,
    }
    numberFormat.value = { unit: 'number', decimals: 0, ...(tile.chart?.number_format || {}) }
    groupBys.value = splitGroupBy(base.group_by)
    if (!groupBys.value.length) groupBys.value = ['']
    colorRules.value = JSON.parse(JSON.stringify(base.color_rules || []))
    advancedOpen.value = !!base.raw_query
    preview.abort()
    preview.data.value = null
    preview.validation.value = null
    previewChart.value = null
    snapshot = state()
    loadContextColumns()
}

const onKeydown = (event) => {
    // Editors that consume Esc (open dropdowns, autocomplete) mark it handled.
    if (event.key === 'Escape' && !event.defaultPrevented && !confirming.value) requestClose()
}

watch(
    () => props.visible,
    (visible) => {
        if (visible) {
            init()
            document.addEventListener('keydown', onKeydown)
        } else {
            preview.abort()
            document.removeEventListener('keydown', onKeydown)
        }
    },
    { immediate: true },
)
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

const requestClose = () => {
    if (!form.value || state() === snapshot) return emit('update:visible', false)
    confirming.value = true
    confirm.require({
        group: 'tile-editor',
        header: 'Discard changes?',
        message: 'This tile has unsaved changes.',
        icon: 'pi pi-exclamation-triangle',
        rejectProps: { label: 'Keep editing', severity: 'secondary', outlined: true, size: 'small' },
        acceptProps: { label: 'Discard', severity: 'danger', size: 'small' },
        accept: () => emit('update:visible', false),
        onHide: () => setTimeout(() => (confirming.value = false)),
    })
}

const loadContextColumns = async () => {
    contextColumnsData.value = null
    if (!source.value || !countOnlyKind(source.value.kind)) return
    const slug = source.value.slug
    const response = await sourceSrv.getContextColumnsData(slug)
    if (response.result && source.value?.slug === slug) contextColumnsData.value = response.data
}

const AGG_LABELS = { last_value: 'last value', quantile: 'percentile' }
const aggOptions = computed(() =>
    (isHeatmap.value ? ['heatmap'] : [...(metrics.value ? ['metric'] : []), ...AGGS, 'formula']).map((a) => ({
        value: a,
        label: AGG_LABELS[a] || a,
        disabled: countOnly.value && a !== 'count',
    })),
)
const metricAggOptions = (type) =>
    (METRIC_AGGS[type] || []).map((a) => ({ value: a, label: METRIC_AGG_LABELS[a] || a }))

const emptyMetric = () => ({ name: '', type: 'gauge', agg: 'avg' })
const setMetric = (s, { name, type }) => {
    const agg = METRIC_AGGS[type].includes(s.metric.agg) ? s.metric.agg : defaultMetricAgg(type)
    s.metric = { ...s.metric, name, type, agg }
}
const firstMetric = computed(() => form.value?.chart.series.find((s) => s.agg === 'metric' && s.metric?.name)?.metric)
watch(
    () => [
        form.value?.chart.source,
        firstMetric.value?.name,
        firstMetric.value?.type,
        props.range?.from,
        props.range?.to,
    ],
    () => {
        const m = firstMetric.value
        if (m && metrics.value)
            metricAttributes.load(chart.value.source, { ...props.range, name: m.name, type: m.type })
    },
)

const columnOptions = (agg) => {
    const result = []
    for (const [name, col] of Object.entries(source.value?.columns || {})) {
        if (agg === 'uniq' || isNumericType(col.type)) result.push(name)
    }
    return result
}

// Example over the aliases already typed, e.g. "errors / total * 100".
const formulaExample = computed(() => {
    const aliases = chart.value.series.filter((s) => s.agg !== 'formula' && s.alias).map((s) => s.alias)
    if (aliases.length >= 2) return `${aliases[0]} / ${aliases[1]} * 100`
    return aliases.length ? `${aliases[0]} * 100` : 'Alias the series, then e.g. errors / total * 100'
})

// A sensible first column: a duration-like numeric one, or a group-by column for uniq.
const defaultColumn = (agg) => {
    const options = columnOptions(agg)
    const columns = source.value?.columns || {}
    if (agg === 'uniq') return options.find((c) => columns[c].group_by) || options[0]
    const duration = source.value?.otelRole?.('duration')
    if (agg === 'heatmap' && options.includes(duration)) return duration
    return options.find((c) => /duration|latency|elapsed|bytes|size/i.test(c)) || options[0]
}

const seriesLabel = (s) => {
    if (s.agg === 'count') return 'count()'
    if (s.agg === 'heatmap') return `heatmap(${s.column || '…'})`
    if (s.agg === 'metric') return metricLabel(s.metric)
    if (s.agg === 'formula') return s.formula || 'formula'
    const column = s.column || '…'
    if (s.agg === 'quantile') return `p${Math.round((s.level ?? 0.95) * 100)}(${column})`
    return `${s.agg}(${column})`
}

// Short FlyQL example built from the source's own columns.
const queryExample = computed(() => {
    const columns = Object.entries(source.value?.columns || {})
    const level = columns.find(([name]) => /^(level|severity|severity_text)$/i.test(name))
    if (level) return `${level[0]} = 'ERROR'`
    const text = columns.find(([, col]) => col.group_by && String(col.type).toLowerCase().includes('string'))
    return text ? `${text[0]} = 'value'` : ''
})

// Same option logic as GraphSettings, driven by the chosen source.
const groupByOptions = computed(() => {
    // Metric charts group by the chosen metric's attribute keys.
    if (metrics.value && firstMetric.value)
        return [{ name: 'ServiceName' }, ...metricAttributes.data.value.map((k) => ({ name: k.path }))]
    let result = []
    for (const [key, value] of Object.entries(source.value?.columns || {})) {
        if (value.group_by) {
            result.push({ name: key })
        }
    }
    return result
})

const onGroupByChange = (idx, event) => {
    let value = event.value
    if (typeof value == 'object') {
        if (value === null) {
            value = ''
        } else {
            value = value.name
        }
    }
    groupBys.value[idx] = value
    if (!value && idx > 0) groupBys.value.splice(idx, 1)
}

watch(
    groupBys,
    (list) => {
        const columns = list.filter(Boolean)
        if (form.value && splitGroupBy(chart.value.group_by).join() !== columns.join())
            chart.value.group_by = columns.join(', ')
    },
    { deep: true },
)

const onAggChange = (s) => {
    if (s.agg === 'metric') {
        s.metric = s.metric || { ...(firstMetric.value || emptyMetric()) }
        delete s.attrs_filter
        delete s.column
        delete s.level
        delete s.where
        delete s.formula
        return
    }
    delete s.metric
    if (s.agg === 'count' || s.agg === 'formula') delete s.column
    else if (!s.column || !columnOptions(s.agg).includes(s.column)) s.column = defaultColumn(s.agg)
    if (s.agg === 'quantile') s.level = s.level ?? 0.95
    else delete s.level
    if (s.agg === 'formula') {
        delete s.where
        s.formula = s.formula ?? ''
    } else delete s.formula
}

const addSeries = () => {
    const s = countOnly.value ? { agg: 'count' } : { agg: metrics.value ? 'metric' : 'avg' }
    onAggChange(s)
    chart.value.series.push(s)
}

const onSourceChange = () => {
    chart.value.context_columns = {}
    chart.value.group_by = ''
    groupBys.value = ['']
    if (isHeatmap.value) chart.value.series = [{ agg: 'heatmap' }]
    else if (countOnly.value) chart.value.series = chart.value.series.map(() => ({ agg: 'count' }))
    else if (metrics.value)
        chart.value.series = chart.value.series.map((s) =>
            s.agg === 'formula' ? s : { agg: 'metric', metric: emptyMetric() },
        )
    else chart.value.series.forEach((s) => s.agg === 'metric' && (s.agg = 'count'))
    chart.value.series.forEach(onAggChange)
    loadContextColumns()
}

// The heatmap's own duration unit follows its source and column, and goes with the display,
// unless the user picked another unit; a freshly opened tile keeps the unit it has.
const heatmapUnit = computed(() =>
    form.value && isHeatmap.value ? durationUnit(source.value, chart.value.series[0]?.column) : null,
)
watch([form, heatmapUnit], ([f, unit], [oldForm, old]) => {
    if (f === oldForm && numberFormat.value.unit === (old || 'number')) numberFormat.value.unit = unit || 'number'
})

const setDisplay = (display) => {
    const c = chart.value
    if ((display === 'search') !== (c.display === 'search')) c.limit = display === 'search' ? 50 : 10
    if (display === 'sql') {
        c.display = display
        c.sql = c.sql || RAW_SQL_EXAMPLE
        c.connection = c.connection ?? null
        return
    }
    // The series, not the display: an SQL display in between keeps the heatmap series.
    const wasHeatmap = c.series?.[0]?.agg === 'heatmap'
    c.display = display
    if (display === 'heatmap') {
        c.series = [{ agg: 'heatmap' }]
        onAggChange(c.series[0])
        c.group_by = ''
        groupBys.value = ['']
    } else if (wasHeatmap) {
        c.series = [{ agg: metrics.value ? 'metric' : 'count' }]
        onAggChange(c.series[0])
    }
    // A single-value display keeps the first series, unless hidden operands feed a formula.
    if (singleSeries.value && c.series.length > 1 && !c.series.some((s) => s.hidden)) c.series = c.series.slice(0, 1)
    if (c.display === 'number') {
        c.group_by = ''
        groupBys.value = ['']
    }
    if (!isTimeseries(display) && display !== 'number') c.compare = false
    if (display !== 'number') c.sparkline = false
    if (c.limit > maxLimit(c.display)) c.limit = maxLimit(c.display)
}

// Client-side checks of spec 2.1, shown next to their fields; the server validates the rest.
const sourceError = computed(() => {
    if (!form.value || ['text', 'sql'].includes(chart.value.display)) return null
    if (!chart.value.source) return 'Choose a source'
    if (!source.value) return `Source ${chart.value.source} is not available`
    return serverError('source')
})

const seriesErrors = computed(() =>
    (form.value && source.value ? chart.value.series : []).map((s, idx) => {
        if (countOnly.value && s.agg !== 'count') return `${s.agg} is not supported for ${source.value.kind}`
        if (s.agg === 'formula') return s.formula?.trim() ? serverSeriesError(idx) : 'Type a formula'
        if (s.agg === 'metric') return s.metric?.name ? serverSeriesError(idx) : 'Choose a metric'
        if (s.agg !== 'count' && !s.column) return `Choose a column for ${s.agg}`
        return serverSeriesError(idx)
    }),
)

const groupByError = computed(() => {
    if (!form.value || !usesGroupBy.value) return null
    if (chart.value.display === 'bar' && !chart.value.group_by) return 'Top N needs a group by column'
    if (chart.value.display === 'pie' && !chart.value.group_by) return 'Pie needs a group by column'
    return serverError('group_by')
})

const limitError = computed(() => {
    if (!form.value || !usesLimit.value) return null
    const max = maxLimit(chart.value.display)
    const limit = chart.value.limit
    return !limit || limit < 1 || limit > max ? `Top groups must be 1..${max}` : null
})

const problem = computed(() => {
    if (!form.value || chart.value.display === 'text') return null
    if (chart.value.display === 'sql') {
        if (chart.value.connection == null) return 'Choose a connection'
        return chart.value.sql?.trim() ? null : 'Type a SELECT query'
    }
    if (sourceError.value && !source.value) return sourceError.value
    if (chart.value.display === 'patterns' && !PATTERN_KINDS.includes(source.value.kind))
        return `Patterns are not supported for ${source.value.kind} sources`
    if (chart.value.display === 'patterns' && !chart.value.column && !bodyColumn(source.value))
        return 'Choose a pattern column'
    if (chart.value.display === 'search' && !(chart.value.limit >= 1 && chart.value.limit <= SEARCH_TILE_MAX_LIMIT))
        return `Rows per page must be 1..${SEARCH_TILE_MAX_LIMIT}`
    if (logTile.value) return null
    if (isHeatmap.value && source.value.kind !== 'clickhouse') return 'Heatmaps need a ClickHouse source'
    const series = seriesErrors.value.find((e, idx) => e && !serverSeriesError(idx))
    if (series) return series
    const shown = chart.value.series.filter((s) => !s.hidden).length
    if (singleSeries.value && chart.value.series.length > 1 && shown !== 1)
        return `${chart.value.display} shows exactly 1 series: hide the others`
    if (!shown) return 'Show at least 1 series'
    if (chart.value.series.every((s) => s.agg === 'formula')) return 'A formula needs at least one query series'
    if (groupRequired.value && !chart.value.group_by) return groupByError.value
    return limitError.value
})

const canPreview = computed(() => !!form.value && chart.value.display !== 'text' && !problem.value)

const cleanChart = () => {
    const c = chart.value
    if (c.display === 'text') return { display: 'text', text: c.text || '' }
    if (c.display === 'sql')
        return { display: 'sql', connection: c.connection, sql: c.sql || '', granularity: c.granularity || 'auto' }
    if (isLogTile(c.display)) {
        const result = {
            source: c.source,
            display: c.display,
            query: c.query || '',
            raw_query: c.raw_query || '',
            context_columns: c.context_columns || {},
        }
        if (c.display === 'search') return { ...result, columns: (c.columns || '').trim(), limit: c.limit }
        return { ...result, column: c.column || '', sample: c.sample || 10000 }
    }
    const result = {
        source: c.source,
        display: c.display,
        series: c.series.map((s) => {
            const item = { agg: s.agg }
            if (s.agg === 'metric') {
                const { name, type, agg, attrs_filter } = s.metric
                item.metric = { name, type, agg }
                if (attrs_filter?.trim()) item.metric.attrs_filter = attrs_filter.trim()
            } else if (s.agg === 'formula') item.formula = (s.formula || '').trim()
            else if (s.agg !== 'count') item.column = s.column
            if (s.agg === 'quantile') item.level = s.level
            if (s.alias) item.alias = s.alias
            if (s.where?.trim() && s.agg !== 'formula') item.where = s.where.trim()
            if (s.color) item.color = s.color
            if (s.hidden) item.hidden = true
            return item
        }),
        query: c.query || '',
        raw_query: c.raw_query || '',
        context_columns: c.context_columns || {},
        group_by: c.display === 'number' ? '' : c.group_by || '',
        granularity: c.granularity || 'auto',
        limit: c.limit,
    }
    if (hasUnit.value) {
        // Optional format keys are only stored when set, so v1 tiles keep their shape.
        const { prefix, suffix, compact, ...format } = numberFormat.value
        result.number_format = { ...format }
        if (prefix) result.number_format.prefix = prefix
        if (suffix) result.number_format.suffix = suffix
        if (compact) result.number_format.compact = true
    }
    if (c.compare && (timeseries.value || c.display === 'number')) result.compare = true
    if (c.sparkline && c.display === 'number') result.sparkline = true
    if (hasColorRules.value && colorRules.value.length) {
        result.color_rules = colorRules.value
            .filter((r) => typeof r.value === 'number')
            .map((r) => ({ op: r.op, value: r.value, color: r.color }))
    }
    return result
}

const flatten = (value) => {
    if (!value) return []
    if (typeof value === 'string') return [value]
    if (Array.isArray(value)) return value.flatMap(flatten)
    return Object.entries(value).flatMap(([k, v]) => flatten(v).map((t) => `${k}: ${t}`))
}

const serverError = (name) => flatten(preview.validation.value?.fields?.[name]).join('; ') || null
const seriesListError = computed(() => {
    const errors = preview.validation.value?.fields?.series
    return Array.isArray(errors) ? flatten(errors).join('; ') : null
})
const serverSeriesError = (idx) => {
    const errors = preview.validation.value?.fields?.series
    return errors && !Array.isArray(errors) ? flatten(errors[idx]).join('; ') || null : null
}

const runPreview = () => {
    if (!canPreview.value) return
    const c = cleanChart()
    previewChart.value = c
    if (c.display === 'sql') return preview.load(c.connection, rawSqlBody(c, props.range), 'sql')
    if (isLogTile(c.display)) return
    preview.load(c.source, {
        from: props.range.from,
        to: props.range.to,
        query: c.query,
        dashboard_query: props.range.query || '',
        raw_query: c.raw_query,
        context_columns: c.context_columns,
        display: c.display,
        series: c.series,
        group_by: c.group_by,
        granularity: c.granularity,
        limit: c.limit,
        params: props.range.params || {},
        compare: !!c.compare,
        sparkline: !!c.sparkline,
    })
}

// Live preview: rerun shortly after the chart settings change.
const previewKey = computed(() => (props.visible && canPreview.value ? JSON.stringify(cleanChart()) : null))
const debouncedPreview = useDebounceFn(runPreview, 500)
watch(previewKey, (key) => key && debouncedPreview())

const onApply = () => {
    const { title, description, section } = form.value
    emit('apply', { title, description, section, chart: cleanChart() })
    emit('update:visible', false)
}
</script>
