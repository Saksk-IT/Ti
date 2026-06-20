function escapeHtml(input: string): string {
  return (input || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function inlineFormat(input: string): string {
  let s = input || '';

  // inline code
  s = s.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>');
  // bold
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // strikethrough
  s = s.replace(/~~([^~]+)~~/g, '<del>$1</del>');
  // italic (simple)
  s = s.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, '$1<em>$2</em>');
  // links
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a class="md-link" href="$2">$1</a>');

  return s;
}

export function markdownToRichTextHtml(markdown: any): string {
  const raw = (markdown || '').toString().replace(/\r\n/g, '\n').trim();
  if (!raw) return '';

  // 先整体转义，避免 AI 输出原生 HTML 造成注入/样式污染
  const escaped = escapeHtml(raw);

  // 代码块：先提取成占位符，避免被行级/内联规则误处理
  const codeBlocks: string[] = [];
  const withPlaceholders = escaped.replace(/```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g, (_m, lang, code) => {
    const idx = codeBlocks.length;
    const langLabel = lang ? `<div class="md-code-lang">${inlineFormat(String(lang))}</div>` : '';
    codeBlocks.push(`${langLabel}<pre class="md-pre"><code class="md-code-block">${code}</code></pre>`);
    return `\n@@CODEBLOCK_${idx}@@\n`;
  });

  const lines = withPlaceholders.split('\n');
  const out: string[] = [];

  let inUl = false;
  let inOl = false;
  let paragraphParts: string[] = [];

  const closeLists = () => {
    if (inUl) out.push('</ul>');
    if (inOl) out.push('</ol>');
    inUl = false;
    inOl = false;
  };

  const flushParagraph = () => {
    if (!paragraphParts.length) return;
    out.push(`<p class="md-p">${paragraphParts.join('<br/>')}</p>`);
    paragraphParts = [];
  };

  for (const line of lines) {
    const trimmed = (line || '').trim();
    if (!trimmed) {
      flushParagraph();
      closeLists();
      continue;
    }

    const codeMatch = trimmed.match(/^@@CODEBLOCK_(\d+)@@$/);
    if (codeMatch) {
      flushParagraph();
      closeLists();
      const idx = Number(codeMatch[1]) || 0;
      if (codeBlocks[idx]) out.push(codeBlocks[idx]);
      continue;
    }

    const hrMatch = trimmed.match(/^(-{3,}|\*{3,}|_{3,})$/);
    if (hrMatch) {
      flushParagraph();
      closeLists();
      out.push('<hr class="md-hr" />');
      continue;
    }

    const hMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushParagraph();
      closeLists();
      const level = Math.min(6, Math.max(1, hMatch[1].length));
      out.push(`<h${level} class="md-h md-h${level}">${inlineFormat(hMatch[2])}</h${level}>`);
      continue;
    }

    const bqMatch = trimmed.match(/^>\s+(.+)$/);
    if (bqMatch) {
      flushParagraph();
      closeLists();
      out.push(`<blockquote class="md-bq">${inlineFormat(bqMatch[1])}</blockquote>`);
      continue;
    }

    const ulMatch = line.match(/^\s*[-*]\s+(.+)$/);
    if (ulMatch) {
      flushParagraph();
      if (inOl) {
        out.push('</ol>');
        inOl = false;
      }
      if (!inUl) {
        out.push('<ul class="md-ul">');
        inUl = true;
      }
      out.push(`<li class="md-li">${inlineFormat(ulMatch[1].trim())}</li>`);
      continue;
    }

    const olMatch = line.match(/^\s*\d+\.\s+(.+)$/);
    if (olMatch) {
      flushParagraph();
      if (inUl) {
        out.push('</ul>');
        inUl = false;
      }
      if (!inOl) {
        out.push('<ol class="md-ol">');
        inOl = true;
      }
      out.push(`<li class="md-li">${inlineFormat(olMatch[1].trim())}</li>`);
      continue;
    }

    // 普通段落
    closeLists();
    paragraphParts.push(inlineFormat(trimmed));
  }

  flushParagraph();
  closeLists();

  return out.join('');
}

