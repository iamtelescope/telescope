import { reactive } from 'vue'

// App-wide overlays any component may open: shell.paletteOpen = true, shell.shortcutsOpen = true.
export const shell = reactive({ paletteOpen: false, shortcutsOpen: false })

export const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '')
export const modKey = isMac ? '⌘' : 'Ctrl'

// Keyboard shortcuts listed in the "?" dialog; areas may push rows here when they add one.
export const SHORTCUTS = [
    { group: 'Anywhere', keys: [modKey, 'K'], label: 'Open the command palette (pages, dashboards, saved views)' },
    { group: 'Anywhere', keys: ['?'], label: 'Show keyboard shortcuts' },
    { group: 'Anywhere', keys: ['Esc'], label: 'Close the open dialog, palette or panel' },
    { group: 'Command palette', keys: ['↑', '↓'], label: 'Move through results', join: 'or' },
    { group: 'Command palette', keys: ['Enter'], label: 'Open the selected result' },
    { group: 'Search', keys: ['Enter'], label: 'Run the query in a search or filter box' },
    { group: 'Search', keys: ['↑', '↓'], label: 'Previous or next row while the row panel is open', join: 'or' },
    { group: 'Search', keys: ['k', 'j'], label: 'Previous or next row, as ↑ and ↓', join: 'or' },
    { group: 'Search', keys: ['Esc'], label: 'Close the row panel' },
    { group: 'Dashboards', keys: ['Esc'], label: 'Leave kiosk mode, or close the tile editor' },
    { group: 'Dashboards', keys: [modKey, 'Enter'], label: 'Run the query of an SQL tile in the tile editor' },
]

// True when a key press belongs to a text field or code editor, not to a global shortcut.
export const isTypingTarget = (el) =>
    !!el &&
    (el.isContentEditable ||
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) ||
        !!el.closest?.('.monaco-editor, [contenteditable="true"]'))
