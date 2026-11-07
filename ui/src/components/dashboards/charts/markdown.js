// A small markdown subset for text tiles. All input is HTML-escaped first, so user HTML never renders;
// only the tags below are produced, and links accept http(s), mailto and same-site paths.
const escapeHtml = (value) =>
    String(value).replace(
        /[&<>"']/g,
        (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
    )

const SAFE_URL = /^(https?:\/\/|mailto:|\/(?![/\\])|#)/i

const link = (text, url) =>
    SAFE_URL.test(url) ? `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>` : text

const inline = (escaped) => {
    const codes = []
    let s = escaped.replace(/`([^`]+)`/g, (_, code) => {
        codes.push(`<code>${code}</code>`)
        return `\u0000${codes.length - 1}\u0000`
    })
    s = s
        .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, text, url) => link(text, url))
        .replace(/(^|[\s(])(https?:\/\/[^\s<)]*[^\s<).,;:!?])/g, (_, pre, url) => `${pre}${link(url, url)}`)
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^*\w])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
        .replace(/(^|[^\w])_([^_\s][^_]*)_(?!\w)/g, '$1<em>$2</em>')
        .replace(/~~([^~]+)~~/g, '<del>$1</del>')
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => codes[i])
}

export const renderMarkdown = (text) => {
    const lines = escapeHtml(text || '').split('\n')
    const out = []
    let i = 0
    while (i < lines.length) {
        const line = lines[i]
        if (/^\s*```/.test(line)) {
            const body = []
            i++
            while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++])
            i++
            out.push(`<pre><code>${body.join('\n')}</code></pre>`)
            continue
        }
        const heading = line.match(/^(#{1,4})\s+(.*)$/)
        if (heading) {
            out.push(`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`)
            i++
            continue
        }
        if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) {
            out.push('<hr>')
            i++
            continue
        }
        const list = line.match(/^\s*([-*+]|\d+[.)])\s+/)
        if (list) {
            const ordered = /\d/.test(list[1])
            const pattern = ordered ? /^\s*\d+[.)]\s+(.*)$/ : /^\s*[-*+]\s+(.*)$/
            const items = []
            let m
            while (i < lines.length && (m = lines[i].match(pattern))) {
                const task = m[1].match(/^\[([ xX])\]\s+(.*)$/)
                items.push(task ? `${task[1] === ' ' ? '☐' : '☑'} ${inline(task[2])}` : inline(m[1]))
                i++
            }
            const tag = ordered ? 'ol' : 'ul'
            out.push(`<${tag}>${items.map((item) => `<li>${item}</li>`).join('')}</${tag}>`)
            continue
        }
        if (/^&gt;\s?/.test(line)) {
            const quote = []
            while (i < lines.length && /^&gt;\s?/.test(lines[i])) quote.push(lines[i++].replace(/^&gt;\s?/, ''))
            out.push(`<blockquote>${inline(quote.join('<br>'))}</blockquote>`)
            continue
        }
        if (!line.trim()) {
            i++
            continue
        }
        const para = []
        while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*```|\s*([-*+]|\d+[.)])\s|&gt;)/.test(lines[i])) {
            para.push(lines[i++])
        }
        if (!para.length) para.push(lines[i++])
        out.push(`<p>${inline(para.join('<br>'))}</p>`)
    }
    return out.join('')
}
