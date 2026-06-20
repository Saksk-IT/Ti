"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.markdownToRichTextHtml = markdownToRichTextHtml;
function escapeHtml(input) {
    return (input || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
function inlineFormat(input) {
    var s = input || '';
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
function markdownToRichTextHtml(markdown) {
    var raw = (markdown || '').toString().replace(/\r\n/g, '\n').trim();
    if (!raw)
        return '';
    // 先整体转义，避免 AI 输出原生 HTML 造成注入/样式污染
    var escaped = escapeHtml(raw);
    // 代码块：先提取成占位符，避免被行级/内联规则误处理
    var codeBlocks = [];
    var withPlaceholders = escaped.replace(/```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g, function (_m, lang, code) {
        var idx = codeBlocks.length;
        var langLabel = lang ? "<div class=\"md-code-lang\">".concat(inlineFormat(String(lang)), "</div>") : '';
        codeBlocks.push("".concat(langLabel, "<pre class=\"md-pre\"><code class=\"md-code-block\">").concat(code, "</code></pre>"));
        return "\n@@CODEBLOCK_".concat(idx, "@@\n");
    });
    var lines = withPlaceholders.split('\n');
    var out = [];
    var inUl = false;
    var inOl = false;
    var paragraphParts = [];
    var closeLists = function () {
        if (inUl)
            out.push('</ul>');
        if (inOl)
            out.push('</ol>');
        inUl = false;
        inOl = false;
    };
    var flushParagraph = function () {
        if (!paragraphParts.length)
            return;
        out.push("<p class=\"md-p\">".concat(paragraphParts.join('<br/>'), "</p>"));
        paragraphParts = [];
    };
    for (var _i = 0, lines_1 = lines; _i < lines_1.length; _i++) {
        var line = lines_1[_i];
        var trimmed = (line || '').trim();
        if (!trimmed) {
            flushParagraph();
            closeLists();
            continue;
        }
        var codeMatch = trimmed.match(/^@@CODEBLOCK_(\d+)@@$/);
        if (codeMatch) {
            flushParagraph();
            closeLists();
            var idx = Number(codeMatch[1]) || 0;
            if (codeBlocks[idx])
                out.push(codeBlocks[idx]);
            continue;
        }
        var hrMatch = trimmed.match(/^(-{3,}|\*{3,}|_{3,})$/);
        if (hrMatch) {
            flushParagraph();
            closeLists();
            out.push('<hr class="md-hr" />');
            continue;
        }
        var hMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
        if (hMatch) {
            flushParagraph();
            closeLists();
            var level = Math.min(6, Math.max(1, hMatch[1].length));
            out.push("<h".concat(level, " class=\"md-h md-h").concat(level, "\">").concat(inlineFormat(hMatch[2]), "</h").concat(level, ">"));
            continue;
        }
        var bqMatch = trimmed.match(/^>\s+(.+)$/);
        if (bqMatch) {
            flushParagraph();
            closeLists();
            out.push("<blockquote class=\"md-bq\">".concat(inlineFormat(bqMatch[1]), "</blockquote>"));
            continue;
        }
        var ulMatch = line.match(/^\s*[-*]\s+(.+)$/);
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
            out.push("<li class=\"md-li\">".concat(inlineFormat(ulMatch[1].trim()), "</li>"));
            continue;
        }
        var olMatch = line.match(/^\s*\d+\.\s+(.+)$/);
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
            out.push("<li class=\"md-li\">".concat(inlineFormat(olMatch[1].trim()), "</li>"));
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
