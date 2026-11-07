import { DateTime } from 'luxon'

import { localTimeZone, moveTimestampToTimeZone } from '@/utils/datetimeranges'

const escapeHtml = (value) =>
    String(value).replace(
        /[&<>"']/g,
        (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
    )

const calcRenderOptions = (type, timestamps, width) => {
    let options = {}
    if (type == 'column') {
        let max = 15

        if (!timestamps) {
            return options
        }

        let columns = timestamps.length
        if (columns < 150) {
            columns = 150
        }

        // left-rigth padding of graph
        let padding = 70
        // spaces between columns
        let totalSpacing = columns + 2

        // calculate expected graph width
        width = width - padding - totalSpacing

        let min = Math.floor(width / columns / 2)
        if (min <= 0 || columns > 200) {
            min = 1
        }
        if (min > max) {
            min = max
        }
        let factor = 0.3
        options['size'] = [factor, max, min]
        options['radius'] = 0.2
    }
    return options
}

const makeTooltipRender = (timeZone, nameLabel, valueLabel, escape) => (data) => {
    const text = escape ? escapeHtml : (value) => value
    const dateTimeString = DateTime.fromMillis(data.x, { zone: timeZone }).toFormat('yyyy-MM-dd HH:mm:ss')
    let html = `<div class="font-medium pb-2 dark:text-neutral-300">${dateTimeString}</div><table class='p-0 m-0 w-full'>`
    html += `<tr class="pb-2"><th></th><th class="text-left pb-2 pr-2 dark:text-neutral-300">${text(nameLabel)}</th><th class="text-right pb-2 dark:text-neutral-300">${text(valueLabel)}</th></tr>`
    let i = 0
    for (const item of data.scales[0].rows.sort((a, b) => b.originalValue - a.originalValue)) {
        if (item.dataValue == 0 && i > 25) {
            continue
        }
        html += '<tr>'
        html += `<td class="p-0 border-0 pr-2"><i style="color:${item.color};" class="pi pi-circle-fill"></i></td>`
        html += `<td class="p-0 border-0 pr-2">${text(item.name)}</td>`
        html += `<td class="p-0 border-0 text-right"> ${text(item.dataValue)}</td>`
        html += '</tr>'
        i++
    }
    html += '</table>'
    return html
}

// series: [{name, data, color}]; width sizes the columns of a column chart.
const getChartSettings = ({
    type,
    timestamps,
    series,
    timeZone,
    theme,
    width,
    nameLabel = 'Name',
    valueLabel = 'Count',
    plotLines = [],
    stacking = type != 'line',
    escape = false,
    onSelect,
}) => {
    return {
        timeline: timestamps,
        timeMultiplier: 1,
        legend: {
            show: true,
        },
        adaptive: true,
        height: 800,
        scales: {
            y: {
                stacking: stacking,
            },
        },
        tooltip: {
            sum: true,
            render: makeTooltipRender(timeZone, nameLabel, valueLabel, escape),
        },
        chart: {
            appearance: {
                drawOrder: ['plotLines', 'axes', 'series'],
                theme: theme,
            },
            series: {
                type: type,
                renderOptions: calcRenderOptions(type, timestamps, width),
                lineWidth: 1,
                width: 1,
            },
        },
        axes: {
            x: {
                plotLines: plotLines,
                values: [
                    // tick incr default year month day hour min sec mode
                    [3600 * 24 * 365 * 1000, '{YYYY} {MMM}', null, null, null, null, null, null, 1],
                    [3600 * 24 * 28 * 1000, '{MMM}', null, null, null, null, null, null, 1],
                    [3600 * 24 * 1000, '{MMM} {DD}', null, null, null, null, null, null, 1],
                    [3600 * 1000, '{HH}:{mm}', null, null, null, null, null, null, 1],
                    [60 * 1000, '{HH}:{mm}', null, null, null, null, null, null, 1],
                    [1 * 1000, '{HH}:{mm}:{ss}', null, null, null, null, null, null, 1],
                    [0.001 * 1000, '{HH}:{mm}:{ss}.{fff}', null, null, null, null, null, null, 1],
                ],
            },
        },
        hooks: {
            onSelect: [(e) => onSelect && onSelect({ from: e.from, to: e.to })],
        },
        series: series,
        editUplotOptions: (opts) => {
            opts.tzDate = (dateOrTs) => {
                const timestamp = typeof dateOrTs === 'number' ? dateOrTs : dateOrTs.valueOf()
                return new Date(moveTimestampToTimeZone(timestamp, timeZone, localTimeZone))
            }
            // Disable zoom on range selection since we reload data
            opts.cursor = opts.cursor || {}
            opts.cursor.drag = opts.cursor.drag || {}
            opts.cursor.drag.setScale = false
            return opts
        },
    }
}

export { getChartSettings }
