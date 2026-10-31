// Minimal, safe Markdown renderer for legal/CMS text. All input is HTML-escaped first,
// so stored text can never inject markup. Supports headings, bold, italics, lists, quotes, paragraphs.
function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

function inline(value: string): string {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, '$1<em>$2</em>')
}

export function renderMarkdown(source: string): string {
  const out: string[] = []
  let list: 'ul' | 'ol' | null = null
  let paragraph: string[] = []
  const flushParagraph = () => {
    if (paragraph.length) out.push(`<p>${inline(paragraph.join(' '))}</p>`)
    paragraph = []
  }
  const closeList = () => {
    if (list) out.push(`</${list}>`)
    list = null
  }
  for (const raw of source.split('\n')) {
    const line = raw.trimEnd()
    const heading = /^(#{1,3})\s+(.*)$/.exec(line)
    const bullet = /^[-*]\s+(.*)$/.exec(line)
    const numbered = /^\d+\.\s+(.*)$/.exec(line)
    const quote = /^>\s?(.*)$/.exec(line)
    if (!line.trim()) { flushParagraph(); closeList(); continue }
    if (heading) {
      flushParagraph(); closeList()
      const level = heading[1].length + 1
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`)
    } else if (bullet || numbered) {
      flushParagraph()
      const kind = bullet ? 'ul' : 'ol'
      if (list !== kind) { closeList(); out.push(`<${kind}>`); list = kind }
      out.push(`<li>${inline((bullet ?? numbered)![1])}</li>`)
    } else if (quote) {
      flushParagraph(); closeList()
      out.push(`<blockquote>${inline(quote[1])}</blockquote>`)
    } else {
      closeList()
      paragraph.push(line.trim())
    }
  }
  flushParagraph(); closeList()
  return out.join('\n')
}
