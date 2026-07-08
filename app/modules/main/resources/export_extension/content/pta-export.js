// ==UserScript==
// @name         PTA题目导出-全能
// @namespace    https://docs.scriptcat.org/
// @version      0.1.1
// @description  try to take over the world!
// @author       Saksk
// @match        https://pintia.cn/*
// @match        https://pta.pintia.cn/*
// @match        https://pintia.cn/problem-sets/*/exam/problems/*
// @match        https://pta.pintia.cn/problem-sets/*/exam/problems/*
// @match        https://*.yuketang.cn/*
// @match        https://*.yuketang.cn/result/*
// @match        https://*.yuketang.cn/exam_room/show_paper*
// @grant        none
// @require      https://unpkg.com/docx@7.1.1/build/index.js
// @require      https://unpkg.com/file-saver@2.0.5/dist/FileSaver.min.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js
// ==/UserScript==

/**
 * PTA题目导出.js
 *
 * 目标：
 * - 在 PTA（pintia.cn / pta.pintia.cn）“答题结果/题目浏览/试卷回顾”等页面，智能识别题型并导出题目 JSON
 * - 在雨课堂考试结果页（*.yuketang.cn/result/*）通过 show_paper 接口导出题目 JSON
 *
 * 导出模式：
 * - 精简：仅保留 题干/选项/答案/解析
 * - PQF：兼容本项目导入（包含 type/tags/difficulty）
 *
 * 使用方式（二选一）：
 * 1) 控制台方式：打开 PTA 页面 → F12 → Console → 粘贴本文件全文执行 → 右下角出现“导出”悬浮按钮
 * 2) 油猴方式：把本文件内容粘贴到 Tampermonkey 新脚本（可自行补充 @match），保存后刷新页面
 *
 * 注意：
 * - 若页面使用“虚拟列表/懒加载”，请先滚动到最底部确保题目都进入 DOM，再点击“解析题目”
 * - 选择题/判断题：若页面不展示标准答案，答错时无法推断正确答案，则导出 answer 为空
 * - 填空题：若本题判定“答案正确”，则把填空框值作为答案导出；否则导出 answer 为空（避免误判）
 * - “解锁选项”：解除页面输入框禁用，便于复制/查看（不会自动提交）
 * - “导出 Word”：下载 .doc（HTML 格式，Word 可直接打开）；“导出 PDF”：打开打印预览，请选择“另存为 PDF”
 */

(() => {
  'use strict';

  const TOOL_ID = 'pta-export-tool-v1';
  const DEFAULT_DIFFICULTY = 3;
  const UI_Z_INDEX = 2147483647;
  const ANSWER_VERIFY_NOTICE = '该题目答案错误，请你核对后修改答案';
  const MANUAL_EDIT_ATTR = 'data-ptaexp-manual';
  const UNSUPPORTED_PAGE_NOTICE =
    '当前页面暂不支持导出：请打开已支持的 PTA 题目页面、雨课堂考试结果页或 show_paper 页面后再试。';
  const YUKETANG_LOGIN_MISSING_NOTICE =
    '雨课堂登录态缺失或无权限：请先在当前浏览器登录雨课堂，确认可打开该考试结果页，刷新后再点击解析题目。';
  const YUKETANG_SHOW_PAPER_FALLBACK_NOTICE =
    'show_paper 拉取失败：请刷新页面后重试；可以直接打开 show_paper 页面确认接口能返回 JSON，再回到考试结果页点击解析题目。';

  // =======================
  // 导出后引流到题库网站（可按需修改）
  // =======================
  const SAK_SITE_NAME = 'SAK 题库';
  const SAK_SITE_URL_KEY = 'sak_site_url_v1';
  const SAK_BANK_ID_KEY = 'sak_bank_id_v1';
  const SAK_IMPORT_MESSAGE_TYPE = 'SAK_IMPORT_TO_BANK_REQUEST';
  const DEFAULT_SAK_SITE_URL = 'http://localhost:8000';

  function getSakSiteUrl() {
    try {
      const v = String(localStorage.getItem(SAK_SITE_URL_KEY) || '').trim();
      return v || DEFAULT_SAK_SITE_URL;
    } catch (e) {
      return DEFAULT_SAK_SITE_URL;
    }
  }

  function getSakPromoLine() {
    const url = getSakSiteUrl();
    return `导入刷题推荐：${SAK_SITE_NAME}（${url}）`;
  }

  function getSakBankId() {
    try {
      return String(localStorage.getItem(SAK_BANK_ID_KEY) || '').trim();
    } catch (e) {
      return '';
    }
  }

  function saveSakBankId(bankId) {
    const id = String(bankId || '').trim();
    if (!/^[1-9]\d*$/.test(id)) {
      throw new Error('个人题库 ID 需为正整数');
    }
    localStorage.setItem(SAK_BANK_ID_KEY, id);
    return id;
  }

  function sakResolveUrl(path) {
    const base = String(getSakSiteUrl() || '').trim().replace(/\/+$/g, '') || DEFAULT_SAK_SITE_URL;
    const p = String(path || '').trim();
    if (!p) return base;
    if (/^https?:\/\//i.test(p)) return p;
    return p.startsWith('/') ? base + p : base + '/' + p;
  }

  function buildSakPromoMessage(exportType, fileName) {
    const f = fileName ? `（${fileName}）` : '';
    if (exportType === 'unsupported') {
      return `${UNSUPPORTED_PAGE_NOTICE}\n\n支持范围：PTA 题目页面、雨课堂考试结果页、雨课堂 show_paper 页面。`;
    }
    if (exportType === 'parse-error') {
      return '请按上方提示处理后，刷新页面并重新点击“解析题目”。如果接口页能直接显示 JSON，助手会优先读取页面内数据。';
    }
    if (exportType === 'help') {
      return `全流程（PTA → ${SAK_SITE_NAME}）：\n1) 先滚动到最底部，确保题目加载完成。\n2) 点击脚本「解析题目」，推荐「下载 JSON」。\n3) 打开 ${SAK_SITE_NAME} → 个人题库 → 新建题库。\n4) 进入题库 → 题目管理 → 导入 JSON。\n5) 抽查 3–5 题；异常题在题目编辑里修正。\n6) 回到题库详情开始刷题（错题/收藏会自动沉淀）。`;
    }
    if (exportType === 'json-copy') {
      return `已生成 JSON。\n下一步：打开 ${SAK_SITE_NAME} → 个人题库 → 进入题库 → 题目管理 → 导入 JSON。`;
    }
    if (exportType === 'json-download') {
      return `已下载 JSON${f}。\n下一步：打开 ${SAK_SITE_NAME} → 个人题库 → 进入题库 → 题目管理 → 导入 JSON。`;
    }
    if (exportType === 'bank-import') {
      return `已发送到个人题库${f}。\n可打开 ${SAK_SITE_NAME} 的题目管理页抽查导入结果。`;
    }
    if (exportType === 'docx' || exportType === 'doc') {
      return `已导出 Word${f}。\n提示：Word 更适合编辑/复习；如需导入刷题，建议导出 JSON。`;
    }
    if (exportType === 'pdf') {
      return `已导出 PDF${f}。\n提示：PDF 更适合打印/复习；如需导入刷题，建议导出 JSON。`;
    }
    if (exportType === 'print') {
      return `已打开打印预览。\n提示：如需导入刷题，请导出 JSON 并导入 ${SAK_SITE_NAME}。`;
    }
    return `导出完成。\n下一步：打开 ${SAK_SITE_NAME} 导入并开始刷题。`;
  }

  function requestSakBankId() {
    const current = getSakBankId();
    const raw = window.prompt('请输入要导入的个人题库 ID：', current || '');
    if (raw === null) return null;
    return saveSakBankId(raw);
  }

  function getImportQuestionCount(payload) {
    return Array.isArray(payload?.questions) ? payload.questions.length : 0;
  }

  function sendSakImportRequest(payload, bankId) {
    return new Promise((resolve, reject) => {
      if (typeof chrome === 'undefined' || !chrome.runtime || typeof chrome.runtime.sendMessage !== 'function') {
        reject(new Error('一键导入需使用“SAK 题库导出助手扩展”版本'));
        return;
      }

      chrome.runtime.sendMessage(
        {
          type: SAK_IMPORT_MESSAGE_TYPE,
          siteUrl: getSakSiteUrl(),
          bankId,
          payload,
        },
        (response) => {
          const lastError = chrome.runtime.lastError;
          if (lastError) {
            reject(new Error(lastError.message || '扩展后台导入失败'));
            return;
          }
          if (!response || !response.ok) {
            reject(new Error(String(response?.message || '导入失败')));
            return;
          }
          resolve(response.body || {});
        }
      );
    });
  }

  async function importPayloadToSakBank(payload) {
    const count = getImportQuestionCount(payload);
    if (!count) throw new Error('没有可导入的题目');

    const bankId = requestSakBankId();
    if (!bankId) return null;

    const result = await sendSakImportRequest(payload, bankId);
    return { bankId, result };
  }

  function normalizeNewlines(text) {
    return String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  }

  function compactWhitespace(text) {
    const t = normalizeNewlines(text);
    // 保留换行，压缩连续空格/制表符
    return t
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n[ \t]+/g, '\n')
      .replace(/[ \t]{2,}/g, ' ')
      .trim();
  }

  // 规范化各种“看起来像空格”的字符（保留换行）
  function normalizeSpaceLikeChars(text) {
    let t = String(text || '');
    if (!t) return '';
    // 复制/富文本里常见的“零宽空格/连接符”等，会导致导出到 Word 后出现奇怪间距
    t = t.replace(/[\u200B-\u200D\uFEFF\u2060]/g, '');
    // 将多种 Unicode 空格统一为普通空格（注意：不动 \n）
    // 不能直接用 /\p{Zs}/u（低版本浏览器会语法错误），改为运行时构造
    let zs = null;
    try {
      zs = new RegExp('\\p{Zs}', 'gu');
    } catch (e) {
      zs = null;
    }
    if (zs) {
      t = t.replace(zs, ' ');
    } else {
      t = t.replace(/[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]/g, ' ');
    }
    return t;
  }

  // 修复部分页面“中文被空格打散”的情况（谨慎触发，避免误伤英文/数字空格）
  function maybeCompactCjkSpacing(text) {
    let t = normalizeSpaceLikeChars(text);
    if (!t) return '';
    const looksBad =
      /[\u4E00-\u9FFF][ \t]+[\u4E00-\u9FFF]/.test(t) ||
      /([（【《〈“‘])[ \t]+[\u4E00-\u9FFF]/.test(t) ||
      /[\u4E00-\u9FFF][ \t]+([，。！？；：、）】》〉”’])/.test(t);
    if (!looksBad) return t;
    t = t.replace(/([\u4E00-\u9FFF])[ \t]+(?=[\u4E00-\u9FFF])/g, '$1');
    t = t.replace(/[ \t]+([，。！？；：、）】》〉”’])/g, '$1');
    t = t.replace(/([（【《〈“‘])[ \t]+/g, '$1');
    return t;
  }

  function normalizeForExport(text) {
    // 保留缩进/空格/换行，仅做必要的字符规范化
    return normalizeSpaceLikeChars(normalizeNewlines(text));
  }

  function extractTextPreserveWhitespace(root) {
    if (!root) return '';

    // 仅在典型“内容块”上补换行，避免 div/容器造成过多空行
    const newlineAfterTags = new Set(['P', 'LI', 'TR', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'PRE', 'BLOCKQUOTE']);

    let out = '';

    function walk(node) {
      if (!node) return;

      if (node.nodeType === Node.TEXT_NODE) {
        out += node.nodeValue || '';
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return;

      const el = node;
      const tag = el.tagName;
      if (tag === 'BR') {
        out += '\n';
        return;
      }

      // <pre> 需要按原样保留其内部所有空白符
      if (tag === 'PRE') {
        out += el.textContent || '';
        if (!out.endsWith('\n')) out += '\n';
        return;
      }

      const before = out.length;
      for (const child of Array.from(el.childNodes || [])) walk(child);

      if (newlineAfterTags.has(tag) && out.length > before && !out.endsWith('\n')) out += '\n';
    }

    walk(root);
    let text = normalizeForExport(out);
    // 去掉末尾由容器补上的单个换行，保留正文内部的换行与缩进
    text = text.replace(/\n$/, '');
    return text;
  }

  function safeText(el) {
    if (!el) return '';
    return maybeCompactCjkSpacing(extractTextPreserveWhitespace(el));
  }

  function isPtaExamPage() {
    const host = String(window.location?.hostname || '').toLowerCase();
    const path = String(window.location?.pathname || '');
    return (host === 'pintia.cn' || host === 'pta.pintia.cn') && /^\/problem-sets\/[^/]+\/exam\/problems\/[^/]+/.test(path);
  }

  function isYuketangExamPage() {
    const host = String(window.location?.hostname || '').toLowerCase();
    const path = String(window.location?.pathname || '');
    return host.endsWith('yuketang.cn') && (/^\/result\/[^/]+/.test(path) || /^\/exam_room\/show_paper/.test(path));
  }

  function isSupportedExportPage() {
    return isPtaExamPage() || isYuketangExamPage();
  }

  function getPageSupportState() {
    if (isYuketangExamPage()) {
      return {
        supported: true,
        title: '雨课堂题目导出',
        readyLog: '脚本已就绪：点击“解析题目”将读取雨课堂 show_paper 数据',
        readyHint: '提示：请保持当前雨课堂账号已登录，解析时会读取本页考试数据。',
        initialStatus: '未解析',
        parseLabel: '解析题目',
      };
    }
    if (isPtaExamPage()) {
      return {
        supported: true,
        title: 'PTA题目导出',
        readyLog: '脚本已就绪：先滚动到底，再点“解析题目”',
        readyHint: '提示：先滚动到底，确保题目全部加载。',
        initialStatus: '未解析',
        parseLabel: '解析题目',
      };
    }
    return {
      supported: false,
      title: 'SAK 题库导出助手',
      readyLog: UNSUPPORTED_PAGE_NOTICE,
      readyHint: UNSUPPORTED_PAGE_NOTICE,
      initialStatus: UNSUPPORTED_PAGE_NOTICE,
      parseLabel: '查看支持范围',
    };
  }

  function getToolTitle() {
    return getPageSupportState().title;
  }

  function getReadyLogText() {
    return getPageSupportState().readyLog;
  }

  function getReadyHintText() {
    return getPageSupportState().readyHint;
  }

  function htmlToPlainText(value) {
    if (value === null || value === undefined) return '';
    if (Array.isArray(value)) return value.map((x) => htmlToPlainText(x)).filter(Boolean).join('\n');
    if (typeof value === 'object') {
      const nested = getFirstValueByKeys(value, [
        'text',
        'content',
        'html',
        'title',
        'name',
        'value',
        'optionContent',
        'questionContent',
        'questionTitle',
      ]);
      return nested === undefined ? '' : htmlToPlainText(nested);
    }

    const source = String(value).replace(/\\n/g, '\n');
    if (!source) return '';
    const textarea = document.createElement('textarea');
    textarea.innerHTML = source;
    const decoded = textarea.value;
    const hasActualHtml = /<\s*\/?\s*[a-zA-Z][^>]*>/i.test(source);
    const htmlSource = hasActualHtml ? source : decoded;
    if (!/[<&][a-zA-Z/#?!]/.test(htmlSource)) {
      return maybeCompactCjkSpacing(decoded).replace(/[ \t]+\n/g, '\n').trim();
    }

    const box = document.createElement('div');
    box.innerHTML = htmlSource.replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|li|tr|h[1-6])>/gi, '\n');
    box.querySelectorAll('script,style,noscript').forEach((n) => n.remove());
    return maybeCompactCjkSpacing(box.innerText || box.textContent || '')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/[ \t]+\n/g, '\n')
      .trim();
  }

  function getFirstValueByKeys(obj, keys) {
    if (!obj || typeof obj !== 'object') return undefined;
    const lowerKeyMap = Object.keys(obj).reduce((acc, key) => {
      acc[String(key).toLowerCase()] = key;
      return acc;
    }, {});
    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) return obj[key];
      const realKey = lowerKeyMap[String(key).toLowerCase()];
      if (realKey !== undefined) return obj[realKey];
    }
    return undefined;
  }

  function parseMaybeJson(value) {
    if (typeof value !== 'string') return value;
    const text = value.trim();
    if (!text || !/^[\[{]/.test(text)) return value;
    try {
      return JSON.parse(text);
    } catch (e) {
      return value;
    }
  }

  function parseFirstNumber(text) {
    const m = String(text || '').match(/-?\d+(?:\.\d+)?/);
    if (!m) return null;
    const n = Number(m[0]);
    return Number.isFinite(n) ? n : null;
  }

  function normalizeOptionText(text) {
    return String(text || '').replace(/\s+/g, '').trim();
  }

  function stripOptionPrefix(raw) {
    const line = String(raw || '');
    return line.replace(/^\s*\(?[A-Z]([\.、\s\)]|$)\s*/i, '');
  }

  function indexToLetter(idx) {
    const i = Number(idx);
    if (!Number.isInteger(i) || i < 0) return '';
    const seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    return i < seed.length ? seed[i] : String(i + 1);
  }

  function optionTextToBoolean(text) {
    const raw = normalizeOptionText(text);
    if (!raw) return null;

    const cleaned = raw
      .replace(/[()（）【】[\]{}<>《》「」“”‘’"'：:，,。.．、;；!！?？]/g, '')
      .toUpperCase();
    if (!cleaned) return null;

    const trueTokens = ['TRUE', 'T', 'YES', 'Y', '对', '正确', '是', '√'];
    const falseTokens = ['FALSE', 'F', 'NO', 'N', '错', '错误', '否', '×'];

    function stripKnownTokens(s) {
      let out = String(s || '');
      const tokens = [...trueTokens, ...falseTokens].sort((a, b) => b.length - a.length);
      for (const token of tokens) {
        if (!token) continue;
        out = out.split(token).join('');
      }
      return out;
    }

    // 若含未知字符（例如“不对/不正确”），不做推断，避免误判
    if (stripKnownTokens(cleaned)) return null;

    const hasTrue = trueTokens.some((t) => cleaned.includes(t));
    const hasFalse = falseTokens.some((t) => cleaned.includes(t));
    if (hasTrue && !hasFalse) return true;
    if (hasFalse && !hasTrue) return false;
    return null;
  }

  function isBooleanOptions(options) {
    if (!Array.isArray(options) || options.length !== 2) return false;
    const a = optionTextToBoolean(options[0]);
    const b = optionTextToBoolean(options[1]);
    return typeof a === 'boolean' && typeof b === 'boolean' && a !== b;
  }

  function getQuestionBlocks() {
    // qt.txt 对应结构：div.pc-x.pt-2.pl-4.scroll-mt-0[id]
    const blocks = Array.from(document.querySelectorAll('div.pc-x[id]'));
    // 过滤掉非题目块（例如页面里其它 pc-x）
    return blocks.filter((b) => b.querySelector('.markdownBlock_tErSz, .rendered-markdown, .rendered-markdown-invert'));
  }

  function parseHeaderMeta(block) {
    const raw = Array.from(block.querySelectorAll('.pc-text-raw'))
      .map((el) => String(el.textContent || '').trim())
      .filter(Boolean);

    const meta = {
      numberLabel: '',
      score: null,
      author: '',
      org: '',
      sourceId: String(block.id || '').trim(),
    };

    // 题号一般在 button 内
    const numEl = block.querySelector('button.pc-button .pc-text-raw');
    meta.numberLabel = String(numEl?.textContent || '').trim();

    for (const t of raw) {
      if (meta.score == null && t.includes('分数')) meta.score = parseFirstNumber(t);
      if (!meta.author && t.includes('作者')) meta.author = t.replace(/^作者\s*/g, '').trim();
      if (!meta.org && t.includes('单位')) meta.org = t.replace(/^单位\s*/g, '').trim();
    }
    return meta;
  }

  function parseEval(block) {
    // qt.txt 对应结构：div.grid ... 里以 key/value 交替排列（评测结果/得分）
    const out = { resultText: '', gotScore: null };
    const grids = Array.from(block.querySelectorAll('div.grid'));
    for (const grid of grids) {
      const text = String(grid.textContent || '');
      if (!text.includes('评测结果') && !text.includes('得分')) continue;

      const items = Array.from(grid.children).map((el) => String(el.textContent || '').trim());
      for (let i = 0; i < items.length - 1; i++) {
        const key = items[i];
        const val = items[i + 1];
        if (key.includes('评测结果')) out.resultText = val;
        if (key.includes('得分')) out.gotScore = parseFirstNumber(val);
      }
      if (out.resultText || typeof out.gotScore === 'number') break;
    }

    // 兜底：有些布局不会以 grid 输出，但会直接在块内出现“答案正确/答案错误”
    if (!out.resultText && block) {
      const t = String(block.innerText || block.textContent || '');
      if (t.includes('答案正确')) out.resultText = '答案正确';
      else if (t.includes('答案错误')) out.resultText = '答案错误';
    }
    return out;
  }

  function inferCorrectness(evalText, gotScore, fullScore) {
    const t = String(evalText || '').trim();
    if (t.includes('答案正确')) return true;
    if (t.includes('答案错误')) return false;
    // 兼容：有些页面只显示“正确/错误/对/错/√/×”
    const boolVal = optionTextToBoolean(t);
    if (typeof boolVal === 'boolean') return boolVal;
    // 兜底：用得分对比满分
    if (typeof gotScore === 'number' && typeof fullScore === 'number') {
      if (gotScore >= fullScore) return true;
      if (gotScore <= 0) return false;
    }
    return null;
  }

  function parseCorrectAnswerLettersFromBlock(block) {
    if (!block) return [];
    // 有些页面会在题目块内展示“正确答案/标准答案/参考答案：A(或AB...)”
    const text = String(block.innerText || block.textContent || '');
    if (!text) return [];

    const m = text.match(/(?:正确答案|标准答案|参考答案)\s*[:：]?\s*([A-Za-z]{1,8})/);
    if (!m) return [];

    const letters = String(m[1] || '')
      .toUpperCase()
      .replace(/[^A-Z]/g, '')
      .split('')
      .filter(Boolean);

    // 去重保持顺序
    const seen = new Set();
    const out = [];
    for (const c of letters) {
      if (!seen.has(c)) {
        seen.add(c);
        out.push(c);
      }
    }
    return out;
  }

  function parseCorrectBooleanFromBlock(block, options) {
    if (!block) return null;
    const text = String(block.innerText || block.textContent || '');
    if (!text) return null;

    // 1) 直接给出“正确/错误/对/错/√/×/T/F/TRUE/FALSE”
    const mToken = text.match(
      /(?:正确答案|标准答案|参考答案)\s*[:：]?\s*(正确|错误|对|错|√|×|TRUE|FALSE|T|F)\b/i
    );
    if (mToken) {
      const b = optionTextToBoolean(mToken[1]);
      if (typeof b === 'boolean') return b;
    }

    // 2) 以字母形式给出（A/B）
    const letters = parseCorrectAnswerLettersFromBlock(block);
    if (letters.length) {
      const idxs = lettersToChoiceIndices(letters);
      const idx = idxs.length ? idxs[0] : null;
      if (Number.isInteger(idx) && Array.isArray(options) && idx >= 0 && idx < options.length) {
        const b = optionTextToBoolean(options[idx]);
        if (typeof b === 'boolean') return b;
      }
    }

    return null;
  }

  function lettersToChoiceIndices(letters) {
    if (!Array.isArray(letters) || !letters.length) return [];
    const out = [];
    for (const c of letters) {
      const u = String(c || '').toUpperCase();
      if (u >= 'A' && u <= 'Z') out.push(u.charCodeAt(0) - 65);
    }
    return out.filter((n) => Number.isInteger(n) && n >= 0).sort((a, b) => a - b);
  }

  const YUKETANG_OPTION_KEYS = [
    'optionList',
    'option_list',
    'options',
    'option',
    'optionDtos',
    'optionArray',
    'choiceList',
    'choice_list',
    'choices',
    'questionOptions',
    'question_options',
    'answerOptions',
    'answer_options',
    'items',
  ];

  const YUKETANG_ANSWER_KEYS = [
    'rightAnswer',
    'right_answer',
    'rightAnswers',
    'right_answers',
    'correctAnswer',
    'correct_answer',
    'correctAnswers',
    'correct_answers',
    'standardAnswer',
    'standard_answer',
    'referenceAnswer',
    'reference_answer',
    'answer',
    'answers',
    'answerContent',
    'answer_content',
    'rightAnswerContent',
    'right_answer_content',
    'stuAnswer',
    'stu_answer',
    'studentAnswer',
    'student_answer',
    'myAnswer',
    'my_answer',
    'userAnswer',
    'user_answer',
    'resultAnswer',
    'result_answer',
  ];

  function normalizeBooleanFlag(value) {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') {
      if (value === 1) return true;
      if (value === 0) return false;
    }
    const raw = String(value ?? '').trim().toLowerCase();
    if (!raw) return null;
    if (['1', 'true', 'yes', 'y', 'right', 'correct', '正确', '对', '是'].includes(raw)) return true;
    if (['0', 'false', 'no', 'n', 'wrong', 'incorrect', '错误', '错', '否'].includes(raw)) return false;
    return null;
  }

  function normalizeYuketangOptionLabel(raw, idx) {
    const text = String(raw ?? '').trim();
    if (/^[A-Z]$/i.test(text)) return text.toUpperCase();
    if (/^\d+$/.test(text)) {
      const n = Number(text);
      if (Number.isInteger(n) && n >= 1 && n <= 26) return indexToLetter(n - 1);
      if (Number.isInteger(n) && n >= 0 && n < 26) return indexToLetter(n);
    }
    return indexToLetter(idx);
  }

  function looksLikeYuketangOptionItem(item) {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return false;
    const text = getFirstValueByKeys(item, [
      'optionContent',
      'option_content',
      'content',
      'html',
      'text',
      'title',
      'name',
      'body',
      'value',
    ]);
    const marker = getFirstValueByKeys(item, [
      'label',
      'key',
      'prefix',
      'sort',
      'option',
      'optionNo',
      'option_no',
      'optionName',
      'option_name',
      'id',
      'optionId',
      'option_id',
      'isCorrect',
      'is_correct',
      'correct',
      'right',
      'isRight',
      'is_right',
    ]);
    return text !== undefined && marker !== undefined;
  }

  function isYuketangOptionArray(value) {
    return Array.isArray(value) && value.some((item) => looksLikeYuketangOptionItem(item));
  }

  function extractYuketangOptionItems(obj) {
    let optionArray = parseMaybeJson(getFirstValueByKeys(obj, YUKETANG_OPTION_KEYS));
    const answerArray = parseMaybeJson(getFirstValueByKeys(obj, ['answer', 'answers']));
    if (!Array.isArray(optionArray) && isYuketangOptionArray(answerArray)) optionArray = answerArray;

    if (!Array.isArray(optionArray)) return [];
    return optionArray
      .map((item, idx) => {
        if (item && typeof item === 'object') {
          const label = normalizeYuketangOptionLabel(
            getFirstValueByKeys(item, [
              'label',
              'key',
              'prefix',
              'sort',
              'option',
              'optionNo',
              'option_no',
              'optionName',
              'option_name',
              'name',
            ]),
            idx
          );
          const id = String(
            getFirstValueByKeys(item, ['id', 'optionId', 'option_id', 'answerId', 'answer_id', 'itemId', 'item_id', 'oid', 'value']) ?? ''
          ).trim();
          const text = stripOptionPrefix(
            htmlToPlainText(
              getFirstValueByKeys(item, ['optionContent', 'option_content', 'content', 'html', 'text', 'title', 'body', 'value'])
            )
          );
          const correct = normalizeBooleanFlag(
            getFirstValueByKeys(item, ['isCorrect', 'is_correct', 'correct', 'right', 'isRight', 'is_right', 'rightFlag', 'right_flag', 'correctFlag', 'correct_flag', 'isAnswer', 'is_answer'])
          );
          return { label, id, text, correct, raw: item };
        }
        return {
          label: indexToLetter(idx),
          id: '',
          text: stripOptionPrefix(htmlToPlainText(item)),
          correct: null,
          raw: item,
        };
      })
      .filter((item) => item.text);
  }

  function getYuketangStemCandidate(obj) {
    return htmlToPlainText(
      getFirstValueByKeys(obj, [
        'questionContent',
        'question_content',
        'questionTitle',
        'question_title',
        'questionName',
        'question_name',
        'quesName',
        'ques_name',
        'questionStem',
        'question_stem',
        'stem',
        'stemHtml',
        'stem_html',
        'problemContent',
        'problem_content',
        'problemTitle',
        'problem_title',
        'problem',
        'topic',
        'subject',
        'title',
        'name',
        'content',
        'description',
        'body',
        'question',
        'questionText',
        'question_text',
      ])
    ).replace(/^\s*\d+\s*[\.、]\s*/g, '');
  }

  function getYuketangAnalysisCandidate(obj) {
    return htmlToPlainText(
      getFirstValueByKeys(obj, [
        'analysis',
        '解析',
        'explanation',
        'explain',
        'answerAnalysis',
        'answer_analysis',
        'analysisContent',
        'analysis_content',
        'remark',
        'remarks',
      ])
    );
  }

  function getYuketangAnswerCandidate(obj) {
    for (const key of YUKETANG_ANSWER_KEYS) {
      const value = parseMaybeJson(getFirstValueByKeys(obj, [key]));
      if (value === undefined) continue;
      if (isYuketangOptionArray(value)) {
        const correctItems = value.filter(
          (item) => normalizeBooleanFlag(getFirstValueByKeys(item, ['isCorrect', 'is_correct', 'correct', 'right', 'isRight', 'is_right'])) === true
        );
        if (correctItems.length) return correctItems;
        continue;
      }
      return value;
    }
    return undefined;
  }

  function flattenYuketangAnswerValues(value) {
    const out = [];
    const walk = (item) => {
      const parsed = parseMaybeJson(item);
      if (parsed === null || parsed === undefined) return;
      if (Array.isArray(parsed)) {
        parsed.forEach((x) => walk(x));
        return;
      }
      if (typeof parsed === 'object') {
        const nested = getFirstValueByKeys(parsed, [
          'label',
          'key',
          'prefix',
          'option',
          'optionNo',
          'option_no',
          'optionName',
          'option_name',
          'id',
          'optionId',
          'option_id',
          'answerId',
          'answer_id',
          'value',
          'answer',
          'rightAnswer',
          'right_answer',
          'correctAnswer',
          'correct_answer',
          'content',
          'text',
          'name',
          'title',
        ]);
        if (nested !== undefined && nested !== parsed) walk(nested);
        return;
      }
      const text = htmlToPlainText(parsed).trim();
      if (text) out.push(text);
    };
    walk(value);
    return out;
  }

  function matchYuketangOptionToken(token, optionItems) {
    const raw = String(token || '').trim();
    if (!raw) return null;
    const plain = stripOptionPrefix(raw).trim();
    const upper = raw.toUpperCase();

    const byLabelOrId = optionItems.find((opt) => {
      const label = String(opt.label || '').trim().toUpperCase();
      const id = String(opt.id || '').trim();
      return (!!label && upper === label) || (!!id && raw === id);
    });
    if (byLabelOrId) return optionItems.indexOf(byLabelOrId);

    if (/^\d+$/.test(raw)) {
      const n = Number(raw);
      if (Number.isInteger(n) && n >= 1 && n <= optionItems.length) return n - 1;
      if (Number.isInteger(n) && n >= 0 && n < optionItems.length) return n;
    }

    const byText = optionItems.find((opt) => {
      const text = String(opt.text || '').trim();
      return text && (plain === text || raw === text);
    });
    return byText ? optionItems.indexOf(byText) : null;
  }

  function normalizeYuketangChoiceAnswer(rawAnswer, optionItems) {
    const fromFlags = optionItems
      .map((opt, idx) => (opt.correct === true ? idx : null))
      .filter((idx) => Number.isInteger(idx));
    const values = flattenYuketangAnswerValues(rawAnswer);
    const out = [];

    for (const value of values) {
      const compactLetters = String(value || '').trim().toUpperCase();
      const tokens = /^[A-Z]{2,26}$/.test(compactLetters)
        ? compactLetters.split('')
        : String(value || '')
            .split(/[\s,，;；|、]+/)
            .map((x) => x.trim())
            .filter(Boolean);
      for (const token of tokens) {
        const idx = matchYuketangOptionToken(token, optionItems);
        if (Number.isInteger(idx) && idx >= 0 && idx < optionItems.length && !out.includes(idx)) out.push(idx);
      }
    }

    const merged = out.length ? out : fromFlags;
    return merged.slice().sort((a, b) => a - b);
  }

  function normalizeYuketangType(rawType, stem, optionItems, rawAnswer) {
    const typeText = htmlToPlainText(rawType).replace(/\s+/g, '').toLowerCase();
    const optionTexts = optionItems.map((item) => item.text);
    const choiceAnswer = normalizeYuketangChoiceAnswer(rawAnswer, optionItems);

    if (/多选|多项|multiple|multi|checkbox/.test(typeText)) return 'multi_choice';
    if (/判断|正误|truefalse|true\/false|boolean|judge/.test(typeText)) return 'boolean';
    if (/填空|blank|completion|cloze/.test(typeText)) return 'fill';
    if (/简答|问答|主观|essay|subjective|shortanswer|short_answer/.test(typeText)) return 'essay';
    if (/单选|单项|single|radio|choice/.test(typeText)) return 'single_choice';
    if (/^2$/.test(typeText) && optionItems.length) return 'multi_choice';
    if (/^4$/.test(typeText)) return 'fill';
    if (/^5$/.test(typeText)) return 'essay';
    if (optionItems.length === 2 && isBooleanOptions(optionTexts)) return 'boolean';
    if (optionItems.length && choiceAnswer.length > 1) return 'multi_choice';
    if (optionItems.length) return 'single_choice';
    if (/_{2,}|（\s*）|\(\s*\)|\{\d+\}/.test(String(stem || ''))) return 'fill';
    return 'essay';
  }

  function normalizeYuketangBooleanAnswer(rawAnswer, optionItems) {
    const direct = flattenYuketangAnswerValues(rawAnswer)
      .map((value) => optionTextToBoolean(value))
      .find((value) => typeof value === 'boolean');
    if (typeof direct === 'boolean') return [direct];

    const idxs = normalizeYuketangChoiceAnswer(rawAnswer, optionItems);
    if (idxs.length) {
      const value = optionTextToBoolean(optionItems[idxs[0]]?.text);
      if (typeof value === 'boolean') return [value];
    }

    const flagged = optionItems.find((item) => item.correct === true);
    if (flagged) {
      const value = optionTextToBoolean(flagged.text);
      if (typeof value === 'boolean') return [value];
    }
    return [];
  }

  function normalizeYuketangAnswer(rawAnswer, type, optionItems) {
    if (type === 'boolean') return normalizeYuketangBooleanAnswer(rawAnswer, optionItems);
    if (type === 'single_choice' || type === 'multi_choice') {
      const idxs = normalizeYuketangChoiceAnswer(rawAnswer, optionItems);
      return type === 'single_choice' ? idxs.slice(0, 1) : idxs;
    }

    const values = flattenYuketangAnswerValues(rawAnswer);
    if (type === 'fill') return values.map((value) => [value]).filter((group) => group[0]);
    if (type === 'essay') return values.length ? [values.join('\n')] : [];
    return [];
  }

  function hasPortableAnswer(answer, type) {
    const list = Array.isArray(answer) ? answer : [];
    if (!list.length) return false;
    if (type === 'fill') return list.some((group) => Array.isArray(group) && group.some((x) => String(x || '').trim()));
    return list.some((value) => typeof value === 'boolean' || Number.isFinite(value) || String(value || '').trim());
  }

  function looksLikeYuketangQuestionObject(obj) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return false;
    const stem = getYuketangStemCandidate(obj);
    if (stem.length < 2) return false;
    const optionItems = extractYuketangOptionItems(obj);
    const rawType = getFirstValueByKeys(obj, ['typeName', 'type_name', 'questionTypeName', 'question_type_name', 'questionType', 'question_type', 'qType', 'q_type', 'type', 'problemType', 'problem_type']);
    const rawAnswer = getYuketangAnswerCandidate(obj);
    const keys = Object.keys(obj).map((key) => String(key).toLowerCase());
    const hasStemKey = keys.some((key) =>
      [
        'questioncontent',
        'question_content',
        'questiontitle',
        'question_title',
        'questionstem',
        'question_stem',
        'problemcontent',
        'problem_content',
        'stem',
        'stemhtml',
        'stem_html',
        'topic',
        'question',
        'questiontext',
        'question_text',
      ].includes(key)
    );
    return hasStemKey || optionItems.length > 0 || rawAnswer !== undefined || rawType !== undefined;
  }

  function collectYuketangQuestionObjects(root) {
    const found = [];
    const seen = new WeakSet();
    const walk = (node, depth) => {
      if (!node || depth > 14 || typeof node !== 'object') return;
      if (seen.has(node)) return;
      seen.add(node);
      if (Array.isArray(node)) {
        node.forEach((item) => walk(item, depth + 1));
        return;
      }
      if (looksLikeYuketangQuestionObject(node)) found.push(node);
      Object.keys(node).forEach((key) => walk(node[key], depth + 1));
    };
    walk(root, 0);
    return found;
  }

  function normalizeYuketangQuestion(obj) {
    const stem = getYuketangStemCandidate(obj);
    if (!stem) return null;
    const optionItems = extractYuketangOptionItems(obj);
    const rawType = getFirstValueByKeys(obj, ['typeName', 'type_name', 'questionTypeName', 'question_type_name', 'questionType', 'question_type', 'qType', 'q_type', 'type', 'problemType', 'problem_type']);
    const rawAnswer = getYuketangAnswerCandidate(obj);
    const type = normalizeYuketangType(rawType, stem, optionItems, rawAnswer);
    const options = type === 'single_choice' || type === 'multi_choice' ? optionItems.map((item) => item.text) : [];
    const answer = normalizeYuketangAnswer(rawAnswer, type, optionItems);
    const answerCertain = hasPortableAnswer(answer, type);
    const baseAnalysis = getYuketangAnalysisCandidate(obj);
    const needsNotice = !answerCertain && ['single_choice', 'multi_choice', 'boolean', 'fill'].includes(type);

    return {
      type,
      content: stem,
      options: type === 'boolean' ? ['正确', '错误'] : options,
      answer,
      analysis: baseAnalysis || (needsNotice ? ANSWER_VERIFY_NOTICE : ''),
      __answerCertain: answerCertain,
      __boolCorrected: false,
    };
  }

  function dedupeYuketangQuestions(questions) {
    const seen = new Set();
    return (Array.isArray(questions) ? questions : []).filter((q) => {
      const key = [
        String(q?.type || ''),
        String(q?.content || '').replace(/\s+/g, ''),
        (Array.isArray(q?.options) ? q.options : []).join('|').replace(/\s+/g, ''),
      ].join('::');
      if (!key.replace(/:/g, '')) return false;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function buildYuketangStats(totalBlocks, questions) {
    const stats = {
      source: 'yuketang',
      total_blocks: totalBlocks,
      parsed: questions.length,
      skipped_empty: Math.max(0, totalBlocks - questions.length),
      unknown_answer: 0,
      need_verify: 0,
      boolean_corrected: 0,
      type_counts: {
        single_choice: 0,
        multi_choice: 0,
        boolean: 0,
        fill: 0,
        essay: 0,
      },
    };
    questions.forEach((q) => {
      const type = String(q?.type || 'essay');
      if (stats.type_counts[type] != null) stats.type_counts[type] += 1;
      if (!hasPortableAnswer(q?.answer, type)) stats.unknown_answer += 1;
      if (q?.__answerCertain === false && ['single_choice', 'multi_choice', 'boolean', 'fill'].includes(type)) stats.need_verify += 1;
    });
    return stats;
  }

  function buildYuketangPortableJson(payload) {
    const root = payload && typeof payload === 'object' && payload.data !== undefined ? payload.data : payload;
    const questionObjects = collectYuketangQuestionObjects(root);
    const questions = dedupeYuketangQuestions(questionObjects.map((obj) => normalizeYuketangQuestion(obj)).filter(Boolean));
    return {
      questions,
      stats: buildYuketangStats(questionObjects.length, questions),
    };
  }

  function getYuketangExamId() {
    const params = new URLSearchParams(window.location.search || '');
    const direct = params.get('exam_id') || params.get('examId') || params.get('examid');
    if (direct) return String(direct).trim();
    const m = String(window.location.pathname || '').match(/\/result\/([^/?#]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function looksLikeYuketangLoginMissing(response, bodyText) {
    const status = Number(response?.status || 0);
    if (status === 401 || status === 403) return true;

    const text = String(bodyText || '').trim();
    if (!text || /^[\[{]/.test(text)) return false;
    const sample = text.slice(0, 3000).toLowerCase();
    return /登录|未登录|无权限|认证|授权|login|signin|sign in|passport|unauthorized|forbidden/.test(sample);
  }

  function getYuketangResponseMessage(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return '';
    const value = getFirstValueByKeys(payload, ['message', 'msg', 'error', 'errorMsg', 'error_msg', 'detail', 'reason']);
    return htmlToPlainText(value).trim();
  }

  function looksLikeYuketangLoginMessage(message) {
    return /登录|未登录|无权限|认证|授权|login|signin|sign in|passport|unauthorized|forbidden/i.test(String(message || ''));
  }

  function looksLikeYuketangFailedPayload(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
    const success = getFirstValueByKeys(payload, ['success', 'ok']);
    if (success === false || String(success).toLowerCase() === 'false') return true;
    const code = getFirstValueByKeys(payload, ['code', 'status', 'errcode', 'errorCode', 'error_code']);
    if (typeof code === 'number') return code !== 0 && code !== 200;
    const codeText = String(code ?? '').trim().toLowerCase();
    return Boolean(codeText && !['0', '200', 'ok', 'success'].includes(codeText));
  }

  function buildYuketangShowPaperFetchErrorMessage(detail) {
    const extra = String(detail || '').trim();
    return extra ? `${YUKETANG_SHOW_PAPER_FALLBACK_NOTICE}（${extra}）` : YUKETANG_SHOW_PAPER_FALLBACK_NOTICE;
  }

  function tryReadYuketangInlineJson() {
    if (!/^\/exam_room\/show_paper/.test(String(window.location.pathname || ''))) return null;
    const text = String(document.querySelector('pre')?.textContent || document.body?.textContent || '').trim();
    if (!text || !/^[\[{]/.test(text)) return null;
    try {
      return JSON.parse(text);
    } catch (e) {
      return null;
    }
  }

  async function fetchYuketangShowPaperPayload() {
    const inline = tryReadYuketangInlineJson();
    if (inline) return inline;

    const examId = getYuketangExamId();
    if (!examId) throw new Error('未找到雨课堂 exam_id');

    const url = new URL('/exam_room/show_paper', window.location.origin);
    url.searchParams.set('exam_id', examId);
    let response = null;
    try {
      response = await fetch(url.toString(), {
        credentials: 'include',
        headers: {
          accept: 'application/json, text/plain, */*',
          'x-client': 'web',
          xtbz: 'cloud',
        },
      });
    } catch (e) {
      const detail = String(e?.message || e || '网络请求失败');
      throw new Error(buildYuketangShowPaperFetchErrorMessage(detail));
    }

    let text = '';
    try {
      text = await response.text();
    } catch (e) {
      const detail = String(e?.message || e || '读取响应失败');
      throw new Error(buildYuketangShowPaperFetchErrorMessage(detail));
    }

    if (looksLikeYuketangLoginMissing(response, text)) throw new Error(YUKETANG_LOGIN_MISSING_NOTICE);
    if (!response.ok) throw new Error(buildYuketangShowPaperFetchErrorMessage(`HTTP ${response.status}`));

    try {
      const parsed = JSON.parse(text);
      const payloadMessage = getYuketangResponseMessage(parsed);
      if (looksLikeYuketangLoginMessage(payloadMessage)) throw new Error(YUKETANG_LOGIN_MISSING_NOTICE);
      if (looksLikeYuketangFailedPayload(parsed)) {
        throw new Error(buildYuketangShowPaperFetchErrorMessage(payloadMessage || '接口返回失败'));
      }
      return parsed;
    } catch (e) {
      if (e && e.message === YUKETANG_LOGIN_MISSING_NOTICE) throw e;
      if (String(e?.message || '').startsWith(YUKETANG_SHOW_PAPER_FALLBACK_NOTICE)) throw e;
      throw new Error(buildYuketangShowPaperFetchErrorMessage('接口返回内容不是 JSON'));
    }
  }

  function getBestStemElement(root) {
    if (!root) return null;
    // PTA 页面经常使用 rendered-markdown + tailwind 的 dark:rendered-markdown-invert（class 含 ":"）
    const candidates = Array.from(
      root.querySelectorAll('.rendered-markdown, .dark\\:rendered-markdown-invert, .markdownBlock_tErSz')
    );

    // 优先：不在选项 label 内的 markdown（避免把选项当成题干）
    const stemEl = candidates.find((el) => !el.closest('label'));
    return stemEl || candidates[0] || root;
  }

  function getBestMarkdownText(root) {
    const stemEl = getBestStemElement(root);
    return safeText(stemEl || root);
  }

  function hasFillBlanks(root) {
    if (!root) return false;
    return Boolean(
      root.querySelector('span[id^="blank"][data-blank="true"]') ||
        root.querySelector('input[data-blank="true"], textarea[data-blank="true"]')
    );
  }

  function extractFillFromStem(stemEl) {
    if (!stemEl) return { content: '', values: [] };

    // 优先：PTA 填空题常见结构：<span id="blankX" data-blank="true"> ... <input value="..."> ... </span>
    const blankSpans = Array.from(stemEl.querySelectorAll('span[id^="blank"][data-blank="true"]'));
    const blankInputs = blankSpans.length
      ? blankSpans.map((s) => s.querySelector('input, textarea')).filter(Boolean)
      : Array.from(stemEl.querySelectorAll('input[data-blank="true"], textarea[data-blank="true"]'));

    const values = blankInputs.map((input) => maybeCompactCjkSpacing(String(input?.value || input?.getAttribute('value') || '').trim()));

    // 构造带 {0}{1} 占位符的题干
    const clone = stemEl.cloneNode(true);

    const cloneBlankSpans = Array.from(clone.querySelectorAll('span[id^="blank"][data-blank="true"]'));
    if (cloneBlankSpans.length) {
      cloneBlankSpans.forEach((span, i) => {
        span.replaceWith(document.createTextNode(`{${i}}`));
      });
    } else {
      const cloneInputs = Array.from(clone.querySelectorAll('input[data-blank="true"], textarea[data-blank="true"]'));
      cloneInputs.forEach((input, i) => {
        input.replaceWith(document.createTextNode(`{${i}}`));
      });
    }

    const content = safeText(clone);
    return { content, values };
  }

  function parseOptionLabel(label) {
    if (!label) return { key: '', text: '' };

    const spans = Array.from(label.querySelectorAll('span'));
    const keySpan = spans.find((s) => /^[A-Z]\.?$/.test(String(s.textContent || '').trim()));
    const key = keySpan ? String(keySpan.textContent || '').replace(/[^A-Za-z]/g, '').toUpperCase() : '';

    // PTA 单选题：A./B. 的 span + 一个 markdown 容器
    const optMarkdown =
      label.querySelector('.rendered-markdown, .dark\\:rendered-markdown-invert') ||
      label.querySelector('.markdownBlock_tErSz');
    let text = safeText(optMarkdown);

    // fallback：直接用 label 文本并去掉前缀
    if (!text) {
      const rawLabelText = safeText(label);
      const boolVal = optionTextToBoolean(rawLabelText);
      if (typeof boolVal === 'boolean') text = rawLabelText.trim();
      else text = stripOptionPrefix(rawLabelText);
    }

    // 兜底：部分判断题/图标选项可能没有可见文本，尝试从 input/value/aria-label 里取（仅限可识别为 boolean 的值）
    if (!text) {
      const input = label.querySelector('input[type="radio"], input[type="checkbox"]');
      const candidates = [
        input?.value,
        input?.getAttribute('value'),
        input?.getAttribute('aria-label'),
        label.getAttribute('aria-label'),
        input?.getAttribute('title'),
        label.getAttribute('title'),
      ];
      for (const c of candidates) {
        const s = String(c || '').trim();
        if (!s) continue;
        if (typeof optionTextToBoolean(s) === 'boolean') {
          text = s;
          break;
        }
      }
    }
    return { key, text: String(text || '') };
  }

  function parseOptions(block) {
    const inputs = Array.from(block.querySelectorAll('input[type="radio"], input[type="checkbox"]'));
    const options = [];
    const optionKeys = [];
    const checkedIndices = [];

    for (const input of inputs) {
      const label = input.closest('label');
      const parsed = parseOptionLabel(label);
      const txt = parsed.text;
      if (!txt) continue;
      const idx = options.length;
      options.push(txt);

      let key = parsed.key;
      if (!key) {
        const boolVal = optionTextToBoolean(txt);
        if (typeof boolVal === 'boolean') key = boolVal ? '正确' : '错误';
      }
      optionKeys.push(key || indexToLetter(idx));
      if (input.checked) checkedIndices.push(idx);
    }

    const hasCheckbox = inputs.some((i) => i.type === 'checkbox');
    const hasRadio = inputs.some((i) => i.type === 'radio');
    const inputKind = hasCheckbox ? 'checkbox' : hasRadio ? 'radio' : '';
    return { options, optionKeys, checkedIndices, inputKind };
  }

  function detectPortableType(block, options, inputKind, contentText) {
    if (inputKind === 'checkbox') return 'multi_choice';
    if (inputKind === 'radio') {
      if (isBooleanOptions(options)) return 'boolean';
      return 'single_choice';
    }
    if (hasFillBlanks(block)) return 'fill';
    // 简单启发：若题干包含明显填空占位，可识别为 fill；否则 essay
    const c = String(contentText || '');
    if (/_{2,}|（\s*）|\(\s*\)/.test(c)) return 'fill';
    if (/\{0\}|\{1\}/.test(c)) return 'fill';
    return 'essay';
  }

  function buildPortableQuestion(block, index, opts) {
    const header = parseHeaderMeta(block);
    const evalInfo = parseEval(block);
    const manualEdited = String(block?.getAttribute(MANUAL_EDIT_ATTR) || '') === '1';

    const stemEl = getBestStemElement(block);
    let content = safeText(stemEl || block);

    const { options, checkedIndices, inputKind } = parseOptions(block);
    const type = detectPortableType(block, options, inputKind, content);
    let fillValues = [];
    if (type === 'fill') {
      const fill = extractFillFromStem(stemEl);
      if (fill?.content) content = fill.content;
      if (Array.isArray(fill?.values)) fillValues = fill.values;
    }
    const isCorrect = inferCorrectness(evalInfo.resultText, evalInfo.gotScore, header.score);

    let pqfOptions = [];
    if (type === 'boolean') pqfOptions = ['正确', '错误'];
    else if (type === 'single_choice' || type === 'multi_choice') pqfOptions = options.slice();

    let answer = [];
    let answerCertain = false;
    let boolCorrected = false;
    let analysis = '';

    if (type === 'boolean') {
      let selected = null;
      if (checkedIndices.length) selected = optionTextToBoolean(options[checkedIndices[0]]);
      if (typeof selected === 'boolean') {
        if (manualEdited) {
          answer = [selected];
          answerCertain = true;
        } else if (isCorrect === true) {
          answer = [selected];
          answerCertain = true;
        } else if (isCorrect === false) {
          answer = [!selected];
          answerCertain = true;
          boolCorrected = true;
        }
      }
      if (!answer.length) {
        const b = parseCorrectBooleanFromBlock(block, options);
        if (typeof b === 'boolean') {
          answer = [b];
          answerCertain = true;
        }
      }
    } else if (type === 'single_choice') {
      if (checkedIndices.length) {
        answer = [checkedIndices[0]];
        answerCertain = manualEdited || isCorrect === true;
      }
    } else if (type === 'multi_choice') {
      if (checkedIndices.length) {
        answer = checkedIndices.slice().sort((a, b) => a - b);
        answerCertain = manualEdited || isCorrect === true;
      }
    } else if (type === 'fill') {
      // 填空题：保留输入框值；若题目显示“答案正确”，则认为答案已确定；否则标记为需核对
      if (Array.isArray(fillValues) && fillValues.length) {
        answer = fillValues.map((v) => {
          const s = String(v || '').trim();
          return s ? [s] : [];
        });
      } else {
        answer = [];
      }
      const hasAnyBlank = Array.isArray(answer) && answer.some((blank) => Array.isArray(blank) && blank.length);
      answerCertain = hasAnyBlank && (manualEdited || isCorrect === true);
      pqfOptions = [];
    } else {
      answer = [];
      pqfOptions = [];
    }

    // 兜底：若页面有显式“标准答案”，尝试补齐（避免单选答错导致无法导出答案）
    if ((type === 'single_choice' || type === 'multi_choice') && (!Array.isArray(answer) || answer.length === 0)) {
      const letters = parseCorrectAnswerLettersFromBlock(block);
      const indices = lettersToChoiceIndices(letters);
      if (indices.length) {
        if (type === 'single_choice') answer = [indices[0]];
        else answer = indices.slice();
        answerCertain = true;
      }
    }

    if ((type === 'fill' || type === 'single_choice' || type === 'multi_choice') && !answerCertain) {
      analysis = ANSWER_VERIFY_NOTICE;
    }

    return {
      type,
      content,
      options: pqfOptions,
      answer,
      analysis,
      __answerCertain: answerCertain,
      __boolCorrected: boolCorrected,
    };
  }

  async function exportPortableJson(opts) {
    if (!isSupportedExportPage()) throw new Error(UNSUPPORTED_PAGE_NOTICE);
    if (isYuketangExamPage()) {
      const payload = await fetchYuketangShowPaperPayload();
      return buildYuketangPortableJson(payload, opts);
    }
    return exportPortableJsonFromDom(opts);
  }

  function exportPortableJsonFromDom(opts) {
    const blocks = getQuestionBlocks();

    const stats = {
      total_blocks: blocks.length,
      parsed: 0,
      skipped_empty: 0,
      unknown_answer: 0,
      need_verify: 0,
      boolean_corrected: 0,
      type_counts: {
        single_choice: 0,
        multi_choice: 0,
        boolean: 0,
        fill: 0,
        essay: 0,
      },
    };

    const questions = [];

    for (let idx = 0; idx < blocks.length; idx++) {
      const b = blocks[idx];
      const q = buildPortableQuestion(b, idx, opts);
      if (!String(q.content || '').trim()) {
        stats.skipped_empty += 1;
        continue;
      }

      questions.push(q);
      stats.parsed += 1;

      const t = String(q.type || '').trim() || 'essay';
      if (stats.type_counts[t] != null) stats.type_counts[t] += 1;
      if (!Array.isArray(q.answer) || q.answer.length === 0) stats.unknown_answer += 1;
      if (q.__boolCorrected) stats.boolean_corrected += 1;
      if (q.__answerCertain === false && (t === 'single_choice' || t === 'multi_choice' || t === 'fill')) stats.need_verify += 1;
    }

    return { questions, stats };
  }

  function buildExportPayload(parsed, opts) {
    const exportMode = String(opts?.exportMode || 'minimal').trim() || 'minimal';
    const requireKnownAnswer = Boolean(opts?.requireKnownAnswer);
    const difficultyRaw =
      typeof opts?.difficulty === 'number' && Number.isFinite(opts.difficulty)
        ? Math.floor(opts.difficulty)
        : DEFAULT_DIFFICULTY;
    const difficulty = Math.max(1, Math.min(5, difficultyRaw));

    const list = Array.isArray(parsed?.questions) ? parsed.questions : [];
    const cleaned = list
      .map((q) => {
        const type = String(q?.type || '').trim() || 'essay';
        const content = String(q?.content || '');
        const options = Array.isArray(q?.options) ? q.options : [];
        const answer = Array.isArray(q?.answer) ? q.answer : [];
        const analysis = String(q?.analysis || '');
        const answerCertain =
          typeof q?.__answerCertain === 'boolean' ? q.__answerCertain : Array.isArray(answer) && answer.length > 0;
        return { type, content, options, answer, analysis, __answerCertain: Boolean(answerCertain) };
      })
      .filter((q) => q.content && String(q.content).trim());

    const filtered = requireKnownAnswer ? cleaned.filter((q) => q.__answerCertain) : cleaned;

    if (exportMode === 'pqf') {
      return {
        questions: filtered.map((q) => ({
          type: q.type,
          content: q.content,
          options: q.options,
          answer: q.answer,
          analysis: q.analysis,
          tags: [],
          difficulty,
        })),
      };
    }

    return {
      questions: filtered.map((q) => ({
        content: q.content,
        options: q.options,
        answer: q.answer,
        analysis: q.analysis,
      })),
    };
  }

  function portableTypeToZh(type) {
    const t = String(type || '').trim();
    if (t === 'single_choice') return '选择题';
    if (t === 'multi_choice') return '多选题';
    if (t === 'boolean') return '判断题';
    if (t === 'fill') return '填空题';
    return '简答题';
  }

  function portableContentToLegacyStem(type, content) {
    const t = String(type || '').trim();
    const s = String(content || '');
    if (t !== 'fill') return s;
    // Word/学习通兼容：用 "__" 表示空位
    return s.replace(/\{\d+\}/g, '__');
  }

  // Word 导入解析器常见规则：用 “;” 分隔空；用 “/” 分隔同一空的多答案
  // 因此：存储格式（;; 分隔空，; 分隔同空多答案）需要转换成 Word 友好格式（; 分隔空，/ 分隔同空多答案）
  function formatFillAnswerForWordFromStorage(storageAnswer) {
    const s = String(storageAnswer || '');
    if (!s) return '';
    const blanks = s
      .split(';;')
      .map((x) => String(x || ''))
      .filter(Boolean);
    const wordParts = blanks.map((b) => b.replace(/;/g, '/'));
    return wordParts.join(';');
  }

  function formatLegacyAnswerForDisplay(zhType, answerText) {
    const t = String(zhType || '').trim();
    const a = String(answerText || '');
    if (!a) return '';
    if (t === '判断题') {
      if (a.trim() === '正确') return '对';
      if (a.trim() === '错误') return '错';
    }
    if (t === '填空题') return formatFillAnswerForWordFromStorage(a.trim());
    return a;
  }

  function fillAnswerArrayToStorage(ans) {
    const list = Array.isArray(ans) ? ans : [];
    if (!list.length) return '';

    const parts = list.map((g) => {
      if (Array.isArray(g)) return g.map((x) => String(x || '').trim()).filter(Boolean).join(';');
      return String(g || '').trim();
    });

    while (parts.length > 1 && parts[parts.length - 1] === '') parts.pop();
    return parts.join(';;');
  }

  function formatAnswerForLegacy(q) {
    const ans = Array.isArray(q?.answer) ? q.answer : [];
    if (!ans.length) return '';

    const type = String(q?.type || '').trim() || inferPortableTypeForExport(q);

    if (type === 'boolean') {
      const v = ans[0];
      if (v === true || v === 1 || String(v).trim() === '1') return '正确';
      if (v === false || v === 0 || String(v).trim() === '0') return '错误';
      const b = optionTextToBoolean(String(v || '').trim());
      return typeof b === 'boolean' ? (b ? '正确' : '错误') : '';
    }

    if (type === 'single_choice') {
      const idx = ans.find((x) => Number.isInteger(x));
      if (!Number.isInteger(idx)) return '';
      return indexToLetter(idx) || String(idx);
    }

    if (type === 'multi_choice') {
      const idxs = ans.filter((x) => Number.isInteger(x)).slice().sort((a, b) => a - b);
      return idxs.map((i) => indexToLetter(i)).filter(Boolean).join('');
    }

    if (type === 'fill') return fillAnswerArrayToStorage(ans);

    return ans.map((x) => String(x || '').trim()).filter(Boolean).join('\n');
  }

  function buildLegacyExportPayload(parsed, opts) {
    const requireKnownAnswer = Boolean(opts?.requireKnownAnswer);
    const difficultyRaw =
      typeof opts?.difficulty === 'number' && Number.isFinite(opts.difficulty)
        ? Math.floor(opts.difficulty)
        : DEFAULT_DIFFICULTY;
    const difficulty = Math.max(1, Math.min(5, difficultyRaw));

    const list = Array.isArray(parsed?.questions) ? parsed.questions : [];
    const filteredList = requireKnownAnswer
      ? list.filter((q) => (typeof q?.__answerCertain === 'boolean' ? q.__answerCertain : Array.isArray(q?.answer) && q.answer.length > 0))
      : list;

    const out = filteredList
      .map((q) => {
        const type = String(q?.type || '').trim() || inferPortableTypeForExport(q);
        const stem = portableContentToLegacyStem(type, String(q?.content || ''));
        const options = Array.isArray(q?.options) ? q.options.map((x) => String(x || '')) : [];
        const answer = formatAnswerForLegacy({ type, options, answer: q?.answer });
        const analysis = String(q?.analysis || '');

        const zhType = portableTypeToZh(type);
        const fixedOptions = type === 'boolean' ? ['正确', '错误'] : options;

        return {
          题型: zhType,
          题干: stem,
          选项: fixedOptions,
          答案: answer,
          解析: analysis,
          难度: difficulty,
        };
      })
      .filter((q) => q.题型 && String(q.题干 || '').trim());

    return { questions: out };
  }

  async function copyToClipboard(text) {
    const t = String(text || '');
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(t);
        return true;
      }
    } catch (e) {
      // ignore and fallback
    }
    // fallback：execCommand
    const ta = document.createElement('textarea');
    ta.value = t;
    ta.setAttribute('readonly', 'true');
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch (e) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  function downloadTextFile(filename, text, mimeType) {
    const mime = String(mimeType || 'application/json;charset=utf-8');
    const blob = new Blob([String(text || '')], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  function safeFilename(name) {
    return String(name || 'PTA题目导出')
      .replace(/[\\/:*?"<>|]/g, '_')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function buildDefaultFilename() {
    const title = document.title || 'PTA题目导出';
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    const base = `${safeFilename(title)}_${ts}`;
    return `${base}.pqf.json`;
  }

  function buildDefaultWordFilename() {
    const title = document.title || 'PTA题目导出';
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    return `${safeFilename(title)}_${ts}.doc`;
  }

  function buildDefaultDocxFilename() {
    const title = document.title || 'PTA题目导出';
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    return `${safeFilename(title)}_${ts}.docx`;
  }

  function buildDefaultPdfFilename() {
    const title = document.title || 'PTA题目导出';
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    return `${safeFilename(title)}_${ts}.pdf`;
  }

  function canExportDocx() {
    try {
      return Boolean(window.docx?.Document && window.docx?.Packer && typeof window.saveAs === 'function');
    } catch (e) {
      return false;
    }
  }

  function canExportPdf() {
    try {
      return Boolean(typeof window.html2canvas === 'function' && window.jspdf?.jsPDF);
    } catch (e) {
      return false;
    }
  }

  function getLegacyQuestionsFromPayload(payload) {
    const list = Array.isArray(payload?.questions) ? payload.questions : [];
    return list.map((q, idx) => {
      const zhType = maybeCompactCjkSpacing(String(q?.题型 || '').trim());
      const stem = maybeCompactCjkSpacing(String(q?.题干 || ''));
      const options = Array.isArray(q?.选项) ? q.选项.map((x) => maybeCompactCjkSpacing(String(x || ''))) : [];
      const answer = maybeCompactCjkSpacing(String(q?.答案 || '').trim());
      const analysis = maybeCompactCjkSpacing(String(q?.解析 || ''));
      return { idx: idx + 1, zhType, stem, options, answer, analysis };
    });
  }

  async function exportLegacyPayloadToDocx(payload, filename) {
    if (!canExportDocx()) throw new Error('docx/file-saver 未加载');

    const { Document, Packer, Paragraph, TextRun, AlignmentType } = window.docx;
    const normalizeDocxText = (t) => normalizeNewlines(maybeCompactCjkSpacing(String(t || ''))).replace(/\t/g, '    ');
    const titleText = normalizeDocxText(document.title || 'PTA题目导出');
    const qs = getLegacyQuestionsFromPayload(payload);

    const children = [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [new TextRun({ text: titleText, bold: true, font: 'SimHei', size: 36 })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 160 },
        children: [new TextRun({ text: normalizeDocxText(getSakPromoLine()), font: 'SimSun', size: 18, color: '0F766E' })],
      }),
    ];

    qs.forEach((q) => {
      const stemLines = normalizeDocxText(String(q.stem || '')).split('\n');
      const stemRuns = stemLines.map((line, i) => {
        const run = { text: String(line || ''), bold: true, font: 'SimHei', size: 22 };
        if (i > 0) run.break = 1;
        return new TextRun(run);
      });

      const headerRuns = [
        new TextRun({ text: `${q.idx}. `, bold: true, font: 'SimHei', size: 22 }),
        q.zhType ? new TextRun({ text: `（${q.zhType}） `, font: 'KaiTi', size: 22 }) : null,
        ...stemRuns,
      ].filter(Boolean);

      children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 150, line: 240 }, children: headerRuns }));

      q.options.forEach((opt, i) => {
        const k = indexToLetter(i) || String(i + 1);
        const optLines = normalizeDocxText(String(opt || '')).split('\n');
        const optRuns = optLines.map((line, j) => {
          const text = j === 0 ? `${k}. ${line}` : String(line || '');
          const run = { text, font: 'SimSun', size: 20 };
          if (j > 0) run.break = 1;
          return new TextRun(run);
        });
        children.push(
          new Paragraph({
            alignment: AlignmentType.LEFT,
            spacing: { line: 240 },
            indent: { left: 420 },
            children: optRuns,
          })
        );
      });

      const { warn, rest: restAnalysis } = splitVerifyNoticeFromAnalysis(q.analysis);
      if (warn) {
        children.push(
          new Paragraph({
            alignment: AlignmentType.LEFT,
            spacing: { line: 240 },
            children: [new TextRun({ text: warn, bold: true, color: 'b91c1c', font: 'SimSun', size: 20 })],
          })
        );
      }

      const displayAnswer = formatLegacyAnswerForDisplay(q.zhType, q.answer) || String(q.answer || '');
      const answerText = normalizeDocxText(displayAnswer);
      const answerLines = answerText.split('\n');
      const answerRuns = answerLines.map((line, i) => {
        const text = i === 0 ? `答案：${line}` : String(line || '');
        const run = { text, bold: true, color: '1a73e8', font: 'SimSun', size: 20 };
        if (i > 0) run.break = 1;
        return new TextRun(run);
      });
      children.push(
        new Paragraph({
          alignment: AlignmentType.LEFT,
          spacing: { line: 240 },
          children: answerRuns,
        })
      );

      if (restAnalysis) {
        const analysisLines = normalizeDocxText(String(restAnalysis || '')).split('\n');
        const analysisRuns = analysisLines.map((line, i) => {
          const text = i === 0 ? `解析：${line}` : String(line || '');
          const run = { text, font: 'SimSun', size: 20 };
          if (i > 0) run.break = 1;
          return new TextRun(run);
        });
        children.push(
          new Paragraph({
            alignment: AlignmentType.LEFT,
            spacing: { line: 240 },
            children: analysisRuns,
          })
        );
      }
    });

    const doc = new Document({ sections: [{ children }] });
    const blob = await Packer.toBlob(doc);
    window.saveAs(blob, filename);
  }

  async function exportLegacyPayloadToPdf(payload, filename) {
    if (!canExportPdf()) throw new Error('html2canvas/jspdf 未加载');

    const qs = getLegacyQuestionsFromPayload(payload);
    const titleText = document.title || 'PTA题目导出';

    const renderArea = document.createElement('div');
    renderArea.style.position = 'absolute';
    renderArea.style.left = '-9999px';
    renderArea.style.top = '0';
    renderArea.style.width = '800px';
    renderArea.style.padding = '44px 50px';
    renderArea.style.color = '#111';
    renderArea.style.background = '#fff';
    renderArea.style.fontFamily = '"Microsoft YaHei","PingFang SC","Hiragino Sans GB","SimSun",Arial,sans-serif';
    renderArea.style.fontSize = '14px';
    renderArea.style.lineHeight = '1.65';
    renderArea.style.letterSpacing = '0';
    renderArea.style.wordBreak = 'break-word';
    renderArea.style.overflowWrap = 'anywhere';
    renderArea.style.tabSize = '4';

    const titleEl = document.createElement('div');
    titleEl.textContent = String(titleText || '');
    titleEl.style.margin = '0 0 14px 0';
    titleEl.style.textAlign = 'center';
    titleEl.style.fontSize = '20px';
    titleEl.style.fontWeight = '800';
    titleEl.style.lineHeight = '1.25';
    renderArea.appendChild(titleEl);

    const promoEl = document.createElement('div');
    promoEl.textContent = getSakPromoLine();
    promoEl.style.margin = '0 0 16px 0';
    promoEl.style.textAlign = 'center';
    promoEl.style.fontSize = '12px';
    promoEl.style.color = '#0f766e';
    promoEl.style.lineHeight = '1.35';
    renderArea.appendChild(promoEl);

    qs.forEach((q) => {
      const itemEl = document.createElement('div');
      itemEl.style.margin = '0 0 14px 0';
      itemEl.style.padding = '10px 0 14px';
      itemEl.style.borderBottom = '1px solid #eee';

      const stemText = normalizeNewlines(String(q.stem || ''));
      const qTitleEl = document.createElement('div');
      qTitleEl.style.fontWeight = '700';
      qTitleEl.style.whiteSpace = 'pre-wrap';
      qTitleEl.style.lineHeight = '1.55';
      qTitleEl.style.margin = '0 0 6px 0';
      qTitleEl.textContent = `${q.idx}. ${q.zhType ? `（${q.zhType}） ` : ''}${stemText}`;
      itemEl.appendChild(qTitleEl);

      if (Array.isArray(q.options) && q.options.length) {
        const optsEl = document.createElement('div');
        optsEl.style.marginTop = '6px';
        optsEl.style.color = '#222';
        optsEl.style.fontSize = '13px';
        optsEl.style.lineHeight = '1.6';
        optsEl.style.whiteSpace = 'pre-wrap';
        optsEl.textContent = q.options
          .map((opt, i) => {
            const k = indexToLetter(i) || String(i + 1);
            return `${k}. ${normalizeNewlines(String(opt || ''))}`;
          })
          .join('\n');
        itemEl.appendChild(optsEl);
      }

      const analysisRaw = normalizeNewlines(String(q.analysis || ''));
      const { warn, rest } = splitVerifyNoticeFromAnalysis(analysisRaw);
      if (warn) {
        const warnEl = document.createElement('div');
        warnEl.style.marginTop = '8px';
        warnEl.style.padding = '8px 10px';
        warnEl.style.borderRadius = '10px';
        warnEl.style.border = '1px solid rgba(185, 28, 28, 0.25)';
        warnEl.style.background = 'rgba(185, 28, 28, 0.06)';
        warnEl.style.color = '#b91c1c';
        warnEl.style.fontWeight = '700';
        warnEl.style.fontSize = '13px';
        warnEl.style.lineHeight = '1.6';
        warnEl.style.whiteSpace = 'pre-wrap';
        warnEl.textContent = warn;
        warnEl.setAttribute('role', 'alert');
        itemEl.appendChild(warnEl);
      }

      const ansEl = document.createElement('div');
      ansEl.style.marginTop = '6px';
      ansEl.style.fontSize = '13px';
      ansEl.style.lineHeight = '1.6';
      ansEl.style.whiteSpace = 'pre-wrap';
      const ansSpan = document.createElement('span');
      ansSpan.style.color = '#1a73e8';
      ansSpan.style.fontWeight = '700';
      const displayAnswer = formatLegacyAnswerForDisplay(q.zhType, q.answer) || String(q.answer || '');
      ansSpan.textContent = displayAnswer ? `答案：${displayAnswer}` : '答案：';
      ansEl.appendChild(ansSpan);
      itemEl.appendChild(ansEl);

      if (rest) {
        const analysisEl = document.createElement('div');
        analysisEl.style.marginTop = '6px';
        analysisEl.style.fontSize = '12.5px';
        analysisEl.style.color = '#555';
        analysisEl.style.lineHeight = '1.6';
        analysisEl.style.whiteSpace = 'pre-wrap';
        analysisEl.textContent = `解析：${rest}`;
        itemEl.appendChild(analysisEl);
      }

      renderArea.appendChild(itemEl);
    });

    document.body.appendChild(renderArea);
    try {
      if (document.fonts && document.fonts.ready) {
        try {
          await document.fonts.ready;
        } catch (e) {
          // ignore
        }
      }
      const canvas = await window.html2canvas(renderArea, { scale: 2, backgroundColor: '#ffffff' });
      const pageHeight = (canvas.height * 210) / canvas.width;
      const doc = new window.jspdf.jsPDF('p', 'mm', [210, pageHeight]);
      doc.addImage(canvas.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, 210, pageHeight);
      doc.save(filename);
    } finally {
      renderArea.remove();
    }
  }

  function escapeHtml(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function textToHtml(text) {
    return escapeHtml(String(text || '')).replace(/\n/g, '<br />');
  }

  function inferPortableTypeForExport(q) {
    const t = String(q?.type || '').trim();
    if (t) return t;

    const options = Array.isArray(q?.options) ? q.options : [];
    const ans = Array.isArray(q?.answer) ? q.answer : [];

    if (ans.length && Array.isArray(ans[0])) return 'fill';
    if (ans.length && typeof ans[0] === 'boolean') return 'boolean';

    if (options.length === 2) {
      const a = optionTextToBoolean(options[0]);
      const b = optionTextToBoolean(options[1]);
      if (typeof a === 'boolean' && typeof b === 'boolean' && a !== b) return 'boolean';
    }

    const idxs = ans.filter((x) => Number.isInteger(x));
    if (options.length && idxs.length) return idxs.length > 1 ? 'multi_choice' : 'single_choice';
    if (options.length) return 'single_choice';
    return 'essay';
  }

  function formatAnswerForExport(q) {
    const ans = Array.isArray(q?.answer) ? q.answer : [];
    if (!ans.length) return '';

    const type = inferPortableTypeForExport(q);

    if (type === 'boolean') {
      const v = ans[0];
      if (v === true || v === 1 || String(v).trim() === '1') return '正确';
      if (v === false || v === 0 || String(v).trim() === '0') return '错误';
      const b = optionTextToBoolean(String(v || '').trim());
      return typeof b === 'boolean' ? (b ? '正确' : '错误') : '';
    }

    if (type === 'single_choice') {
      const idx = ans.find((x) => Number.isInteger(x));
      if (!Number.isInteger(idx)) return '';
      return indexToLetter(idx) || String(idx);
    }

    if (type === 'multi_choice') {
      const idxs = ans.filter((x) => Number.isInteger(x)).slice().sort((a, b) => a - b);
      return idxs.map((i) => indexToLetter(i)).filter(Boolean).join('');
    }

    if (type === 'fill') {
      const groups = ans
        .map((g) => {
          if (Array.isArray(g)) return g.map((x) => String(x || '').trim()).filter(Boolean).join('/');
          return String(g || '').trim();
        })
        .filter(Boolean);
      return groups.join('；');
    }

    // essay
    return ans.map((x) => String(x || '').trim()).filter(Boolean).join('\n');
  }

  function splitVerifyNoticeFromAnalysis(analysisText) {
    const raw = String(analysisText || '').trim();
    if (!raw) return { warn: '', rest: '' };
    if (!raw.includes(ANSWER_VERIFY_NOTICE)) return { warn: '', rest: raw };
    const rest = raw
      .split(ANSWER_VERIFY_NOTICE)
      .join('')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    return { warn: ANSWER_VERIFY_NOTICE, rest };
  }

  function buildExportHtml(data) {
    const list = Array.isArray(data?.questions) ? data.questions : [];

    const rows = list
      .map((q) => {
        const content = textToHtml(q?.content || '');
        const options = Array.isArray(q?.options) ? q.options : [];
        const answerText = formatAnswerForExport(q);
        const analysisText = String(q?.analysis || '');
        const { warn, rest } = splitVerifyNoticeFromAnalysis(analysisText);

        const optionsHtml = options.length
          ? `<ol class="q-opts">${options.map((opt) => `<li>${textToHtml(opt)}</li>`).join('')}</ol>`
          : '';
        const warnHtml = warn ? `<div class="q-warn" role="alert">${escapeHtml(warn)}</div>` : '';
        const analysisHtml = rest ? `<div class="q-analysis"><span class="k">解析：</span>${textToHtml(rest)}</div>` : '';

        return `
        <section class="q">
          <div class="q-content">${content}</div>
          ${optionsHtml}
          ${warnHtml}
          <div class="q-ans"><span class="k">答案：</span>${textToHtml(answerText)}</div>
          ${analysisHtml}
        </section>
      `;
      })
      .join('\n');

    const titleText = document.title || 'PTA题目导出';
    return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(titleText)}</title>
  <style>
    :root { color-scheme: light; }
    body { margin: 0; padding: 24px 18px; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; color: #111; background: #fff; }
    .q { border: 1px solid #eee; border-radius: 12px; padding: 12px 12px; margin: 12px 0; page-break-inside: avoid; }
    .q-content { font-size: 13px; line-height: 1.65; white-space: pre-wrap; tab-size: 4; }
    .q-opts { margin: 10px 0 0 18px; padding: 0; font-size: 13px; line-height: 1.6; }
    .q-opts li { margin: 4px 0; white-space: pre-wrap; tab-size: 4; }
    .q-warn { margin-top: 10px; padding: 8px 10px; border-radius: 12px; border: 1px solid rgba(185, 28, 28, 0.25); background: rgba(185, 28, 28, 0.06); color: #b91c1c; font-weight: 750; font-size: 12.5px; line-height: 1.6; }
    .q-ans, .q-analysis { margin-top: 10px; font-size: 12.5px; color: #222; line-height: 1.6; white-space: pre-wrap; tab-size: 4; }
    .k { color: #666; }
    @media print { body { padding: 0; } .q { border-color: #ddd; } }
  </style>
</head>
<body>
  ${rows || '<div>未解析到题目。</div>'}
</body>
</html>`;
  }

  function buildLegacyExportHtml(data) {
    const list = Array.isArray(data?.questions) ? data.questions : [];

    const rows = list
      .map((q, idx) => {
        const zhType = String(q?.题型 || '').trim();
        const stem = textToHtml(q?.题干 || '');
        const options = Array.isArray(q?.选项) ? q.选项 : [];
        const rawAnswerText = String(q?.答案 || '');
        const answerText = formatLegacyAnswerForDisplay(zhType, rawAnswerText) || rawAnswerText;
        const analysisText = String(q?.解析 || '');
        const { warn, rest } = splitVerifyNoticeFromAnalysis(analysisText);

        const optionsHtml = options.length
          ? `<div class="q-opts">${options
              .map((opt, i) => {
                const k = indexToLetter(i) || String(i + 1);
                return `<div class="q-opt"><span class="q-opt-k">${escapeHtml(k)}.</span><span class="q-opt-v">${textToHtml(
                  opt
                )}</span></div>`;
              })
              .join('')}</div>`
          : '';

        const warnHtml = warn ? `<div class="q-warn" role="alert">${escapeHtml(warn)}</div>` : '';
        const analysisHtml = rest ? `<div class="q-analysis"><span class="k">解析：</span>${textToHtml(rest)}</div>` : '';

        return `
        <section class="q">
          <div class="q-title">
            <span class="q-idx">${idx + 1}.</span>
            ${zhType ? `<span class="q-type">（${escapeHtml(zhType)}）</span>` : ''}
          </div>
          <div class="q-content">${stem}</div>
          ${optionsHtml}
          ${warnHtml}
          <div class="q-ans"><span class="k">答案：</span><span class="a">${textToHtml(answerText)}</span></div>
          ${analysisHtml}
        </section>
      `;
      })
      .join('\n');

    const titleText = document.title || 'PTA题目导出';
    return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(titleText)}</title>
  <style>
    :root { color-scheme: light; }
    body { margin: 0; padding: 22px 16px; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; color: #111; background: #fff; }
    .doc-title { font-size: 18px; font-weight: 700; text-align: center; margin: 0 0 16px; }
    .doc-promo { font-size: 12px; font-weight: 650; text-align: center; margin: -10px 0 16px; color: #0f766e; }
    .q { border: 1px solid #eee; border-radius: 12px; padding: 12px 12px; margin: 12px 0; page-break-inside: avoid; }
    .q-title { font-size: 13px; font-weight: 700; line-height: 1.5; margin-bottom: 6px; }
    .q-idx { margin-right: 6px; }
    .q-type { color: #6b7280; margin-right: 6px; font-weight: 600; }
    .q-content { font-size: 13px; line-height: 1.65; white-space: pre-wrap; tab-size: 4; }
    .q-opts { margin-top: 10px; font-size: 13px; line-height: 1.6; }
    .q-opt { display: flex; gap: 8px; margin: 4px 0; }
    .q-opt-k { width: 1.2em; flex: none; color: #374151; font-weight: 700; }
    .q-opt-v { flex: 1; min-width: 0; white-space: pre-wrap; tab-size: 4; }
    .q-warn { margin-top: 10px; padding: 8px 10px; border-radius: 12px; border: 1px solid rgba(185, 28, 28, 0.25); background: rgba(185, 28, 28, 0.06); color: #b91c1c; font-weight: 750; font-size: 12.5px; line-height: 1.6; }
    .q-ans, .q-analysis { margin-top: 10px; font-size: 12.5px; color: #222; line-height: 1.6; white-space: pre-wrap; tab-size: 4; }
    .k { color: #6b7280; }
    .a { color: #1a73e8; font-weight: 700; }
    @media print { body { padding: 0; } .q { border-color: #ddd; } }
  </style>
</head>
<body>
  <h1 class="doc-title">${escapeHtml(titleText)}</h1>
  <div class="doc-promo">${escapeHtml(getSakPromoLine())}</div>
  ${rows || '<div>未解析到题目。</div>'}
</body>
</html>`;
  }

  function openPrintWindow(html) {
    const win = window.open('', '_blank');
    if (!win) return false;
    win.document.open();
    win.document.write(String(html || ''));
    win.document.close();
    const doPrint = () => {
      try {
        win.focus();
        win.print();
      } catch (e) {
        // ignore
      }
    };
    win.addEventListener('load', () => setTimeout(doPrint, 60), { once: true });
    // 兜底：部分浏览器不会触发 load
    setTimeout(doPrint, 900);
    return true;
  }

  function unlockAllInputs() {
    const scope = document.querySelector('#exam-app') || document.body;
    const els = Array.from(scope.querySelectorAll('input, textarea, select'));
    for (const el of els) {
      try {
        el.disabled = false;
        el.readOnly = false;
      } catch (e) {
        // ignore
      }
      try {
        el.removeAttribute('disabled');
        el.removeAttribute('readonly');
      } catch (e) {
        // ignore
      }
    }
    return els.length;
  }

  function injectStyle() {
    if (document.getElementById(`${TOOL_ID}-style`)) return;
    const style = document.createElement('style');
    style.id = `${TOOL_ID}-style`;
    style.textContent = `
      #${TOOL_ID} {
        position: fixed; right: 16px; bottom: 16px; z-index: ${UI_Z_INDEX};
        font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
        --ptaexp-accent: 79 70 229;
        --ptaexp-bg: rgba(255,255,255,0.86);
        --ptaexp-bg2: rgba(255,255,255,0.65);
        --ptaexp-border: rgba(15, 23, 42, 0.12);
        --ptaexp-text: rgba(15, 23, 42, 0.92);
        --ptaexp-muted: rgba(15, 23, 42, 0.62);
        --ptaexp-shadow: 0 18px 55px rgba(0,0,0,0.16);
        --ptaexp-shadow-fab: 0 10px 30px rgba(0,0,0,0.14);
        --ptaexp-ring: rgba(var(--ptaexp-accent), 0.34);
      }
      #${TOOL_ID} * { box-sizing: border-box; }

      .ptaexp-fab {
        height: 56px; min-width: 56px; padding: 0 14px;
        border-radius: 18px;
        border: 1px solid var(--ptaexp-border);
        background: rgba(255,255,255,0.78);
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
        box-shadow: var(--ptaexp-shadow-fab);
        color: var(--ptaexp-text);
        cursor: pointer; user-select: none;
        display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        font-size: 13px; font-weight: 700;
        -webkit-tap-highlight-color: transparent;
      }
      .ptaexp-fab svg { width: 18px; height: 18px; opacity: 0.88; }
      .ptaexp-fab:active { transform: translateY(0.5px); }
      .ptaexp-fab:focus-visible { outline: none; box-shadow: var(--ptaexp-shadow-fab), 0 0 0 3px var(--ptaexp-ring); }

      .ptaexp-panel {
        position: absolute; right: 0; bottom: 68px;
        width: min(392px, calc(100vw - 24px));
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg);
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        border-radius: 18px; padding: 12px;
        box-shadow: var(--ptaexp-shadow);
        display: none;
      }
      .ptaexp-panel.show { display: block; }

      .ptaexp-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
      .ptaexp-title-row { display: flex; align-items: center; gap: 8px; }
      .ptaexp-title { font-size: 13px; font-weight: 800; color: var(--ptaexp-text); margin: 0; }
      .ptaexp-sub { margin-top: 3px; font-size: 11px; color: var(--ptaexp-muted); line-height: 1.3; }
      .ptaexp-sub-row { margin-top: 4px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
      .ptaexp-sub-row .ptaexp-sub { margin: 0; flex: 1 1 auto; min-width: 180px; }
      .ptaexp-badge {
        padding: 3px 8px;
        border-radius: 999px;
        border: 1px solid var(--ptaexp-border);
        background: rgba(var(--ptaexp-accent), 0.14);
        color: var(--ptaexp-text);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.2px;
      }
      .ptaexp-icon-btn {
        width: 34px; height: 34px; border-radius: 12px;
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg2);
        color: var(--ptaexp-text);
        cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
        -webkit-tap-highlight-color: transparent;
      }
      .ptaexp-icon-btn svg { width: 16px; height: 16px; opacity: 0.82; }
      .ptaexp-icon-btn:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ptaexp-ring); }

      .ptaexp-section { margin-top: 10px; }
      .ptaexp-label { font-size: 11px; color: var(--ptaexp-muted); margin-bottom: 6px; }

      .ptaexp-chips { display: flex; flex-wrap: wrap; gap: 8px; }
      .ptaexp-chip {
        display: inline-flex; align-items: center; gap: 8px;
        border-radius: 999px;
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg2);
        color: var(--ptaexp-text);
        padding: 8px 10px;
        font-size: 12px;
        font-weight: 750;
        cursor: pointer;
        -webkit-tap-highlight-color: transparent;
      }
      .ptaexp-chip[aria-pressed="true"] {
        background: rgba(var(--ptaexp-accent), 0.14);
        border-color: rgba(var(--ptaexp-accent), 0.28);
      }
      .ptaexp-chip:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ptaexp-ring); }
      .ptaexp-chip:disabled { opacity: 0.55; cursor: not-allowed; }
      .ptaexp-chip .n {
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid var(--ptaexp-border);
        background: rgba(15, 23, 42, 0.06);
        color: var(--ptaexp-muted);
        font-size: 11px;
        font-weight: 800;
      }

      .ptaexp-links { display: inline-flex; align-items: center; gap: 6px; margin-left: auto; }
      .ptaexp-link {
        border: 1px solid transparent;
        background: transparent;
        color: var(--ptaexp-muted);
        padding: 6px 8px;
        border-radius: 12px;
        font-size: 11px;
        cursor: pointer;
        -webkit-tap-highlight-color: transparent;
      }
      .ptaexp-link:hover { background: var(--ptaexp-bg2); color: var(--ptaexp-text); border-color: var(--ptaexp-border); }
      .ptaexp-link:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ptaexp-ring); }

      .ptaexp-seg {
        display: flex; gap: 6px; padding: 4px;
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg2);
        border-radius: 14px;
      }
      .ptaexp-seg-btn {
        flex: 1;
        border: 1px solid transparent;
        background: transparent;
        color: var(--ptaexp-muted);
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 12px;
        cursor: pointer;
        -webkit-tap-highlight-color: transparent;
      }
      .ptaexp-seg-btn[aria-pressed="true"] {
        background: rgba(var(--ptaexp-accent), 0.14);
        border-color: rgba(var(--ptaexp-accent), 0.22);
        color: var(--ptaexp-text);
      }
      .ptaexp-seg-btn:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ptaexp-ring); }

      .ptaexp-check {
        display: flex; align-items: center; gap: 10px;
        padding: 10px 10px;
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg2);
        border-radius: 14px;
        font-size: 12px;
        color: var(--ptaexp-text);
        -webkit-tap-highlight-color: transparent;
      }
      .ptaexp-check input { width: 16px; height: 16px; accent-color: rgb(var(--ptaexp-accent)); }
      .ptaexp-check input:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ptaexp-ring); border-radius: 4px; }

      .ptaexp-range { display: flex; align-items: center; gap: 10px; }
      .ptaexp-range input[type="range"] { flex: 1; }
      .ptaexp-pill {
        padding: 3px 10px;
        border-radius: 999px;
        border: 1px solid var(--ptaexp-border);
        background: rgba(var(--ptaexp-accent), 0.12);
        color: var(--ptaexp-text);
        font-size: 12px;
        min-width: 34px;
        text-align: center;
      }

      .ptaexp-actions {
        margin-top: 10px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }
      .ptaexp-action {
        border-radius: 14px;
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg2);
        color: var(--ptaexp-text);
        padding: 10px 10px;
        font-size: 12px;
        cursor: pointer;
        -webkit-tap-highlight-color: transparent;
        min-height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ptaexp-action[data-primary="1"] {
        background: rgba(var(--ptaexp-accent), 0.16);
        border-color: rgba(var(--ptaexp-accent), 0.28);
      }
      .ptaexp-action:active { transform: translateY(0.5px); }
      .ptaexp-action:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ptaexp-ring); }
      .ptaexp-action:disabled {
        opacity: 0.55;
        cursor: not-allowed;
        transform: none !important;
      }
      .ptaexp-action:disabled:active { transform: none; }

      .ptaexp-muted { font-size: 11px; line-height: 1.4; color: var(--ptaexp-muted); padding: 6px 2px 0; }
      .ptaexp-status { font-size: 11px; line-height: 1.4; color: var(--ptaexp-muted); margin-top: 8px; }
      .ptaexp-guide-links { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px; }

      .ptaexp-sak-overlay {
        position: fixed;
        inset: 0;
        display: none;
        align-items: flex-end;
        justify-content: center;
        padding: 14px 14px calc(14px + env(safe-area-inset-bottom));
        background: rgba(0, 0, 0, 0.45);
      }
      .ptaexp-sak-overlay.show { display: flex; }
      @media (min-width: 560px) {
        .ptaexp-sak-overlay { align-items: center; }
      }
      .ptaexp-sak-card {
        width: min(520px, 100%);
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border-radius: 18px;
        padding: 12px;
        box-shadow: var(--ptaexp-shadow);
      }
      .ptaexp-sak-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
      .ptaexp-sak-title { font-size: 13px; font-weight: 800; color: var(--ptaexp-text); }
      .ptaexp-sak-body { margin-top: 8px; color: var(--ptaexp-text); }
      .ptaexp-sak-msg { font-size: 12px; line-height: 1.6; white-space: pre-wrap; }
      .ptaexp-sak-url { margin-top: 8px; font-size: 12px; color: var(--ptaexp-muted); word-break: break-word; }
      .ptaexp-sak-setting { margin-top: 10px; display: none; }
      .ptaexp-sak-setting.show { display: block; }
      .ptaexp-sak-input {
        width: 100%;
        height: 34px;
        padding: 0 10px;
        border: 1px solid var(--ptaexp-border);
        border-radius: 10px;
        background: var(--ptaexp-bg2);
        color: var(--ptaexp-text);
        font: inherit;
        font-size: 12px;
        outline: none;
      }
      .ptaexp-sak-input:focus { border-color: #0f766e; box-shadow: 0 0 0 3px rgba(15,118,110,0.12); }
      .ptaexp-sak-error { min-height: 18px; margin-top: 6px; color: #b91c1c; font-size: 12px; line-height: 1.5; }
      .ptaexp-sak-setting-actions { margin-top: 8px; display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
      .ptaexp-sak-actions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
      .ptaexp-sak-actions .ptaexp-action { flex: 1 1 auto; }

      .ptaexp-log {
        margin-top: 10px;
        border: 1px solid var(--ptaexp-border);
        background: var(--ptaexp-bg2);
        border-radius: 16px;
        overflow: hidden;
      }
      .ptaexp-log-body {
        padding: 10px 10px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 11px;
        line-height: 1.45;
        color: var(--ptaexp-text);
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 112px;
        overflow: auto;
        scrollbar-width: none;
        -ms-overflow-style: none;
      }
      .ptaexp-log-body::-webkit-scrollbar { width: 0; height: 0; }
      .ptaexp-log-body:empty::before { content: "暂无日志"; color: var(--ptaexp-muted); }

      .ptaexp-sak-notice {
        margin: 0 0 10px 0;
        padding: 8px 10px;
        border-radius: 12px;
        border: 1px solid rgba(185, 28, 28, 0.25);
        background: rgba(185, 28, 28, 0.06);
        color: #b91c1c;
        font-weight: 850;
        font-size: 12px;
        line-height: 1.6;
        white-space: pre-wrap;
      }

      @media (max-width: 380px) {
        .ptaexp-sub-row .ptaexp-sub { min-width: 100%; }
        .ptaexp-links { width: 100%; justify-content: flex-end; }
      }

      @media (max-width: 480px) {
        #${TOOL_ID} { left: 12px; right: 12px; bottom: 12px; }
        .ptaexp-fab { width: 100%; justify-content: center; }
        .ptaexp-panel { left: 0; right: 0; width: auto; }
      }

      @media (prefers-color-scheme: dark) {
        #${TOOL_ID} {
          --ptaexp-bg: rgba(18,18,18,0.78);
          --ptaexp-bg2: rgba(255,255,255,0.06);
          --ptaexp-border: rgba(255,255,255,0.16);
          --ptaexp-text: rgba(255,255,255,0.88);
          --ptaexp-muted: rgba(255,255,255,0.64);
          --ptaexp-shadow: 0 18px 55px rgba(0,0,0,0.70);
          --ptaexp-shadow-fab: 0 10px 30px rgba(0,0,0,0.55);
        }
        .ptaexp-fab { background: rgba(18,18,18,0.66); }
      }
    `;
    document.head.appendChild(style);
  }

  function mountUI() {
    if (document.getElementById(TOOL_ID)) return;
    injectStyle();

    const pageSupportState = getPageSupportState();
    const toolTitle = getToolTitle();
    const readyHintText = getReadyHintText();

    const root = document.createElement('div');
    root.id = TOOL_ID;
    root.innerHTML = `
      <button class="ptaexp-fab" type="button" aria-label="${toolTitle}" aria-haspopup="dialog" aria-expanded="false" data-el="fab">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 3v10m0 0 4-4m-4 4-4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          <path d="M4 17v3h16v-3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
        </svg>
        <span>导出</span>
      </button>
      <div class="ptaexp-panel" role="dialog" aria-modal="false" aria-label="${toolTitle}面板">
        <div class="ptaexp-head">
          <div>
            <div class="ptaexp-title-row">
              <div class="ptaexp-title">${toolTitle}</div>
              <span class="ptaexp-badge" aria-label="导出格式：PQF">PQF</span>
            </div>
            <div class="ptaexp-sub-row">
              <div class="ptaexp-sub" data-el="summary">未解析｜格式：PQF（固定）</div>
              <div class="ptaexp-links" aria-label="快捷入口">
                <button class="ptaexp-link" type="button" data-act="guide">指南</button>
                <button class="ptaexp-link" type="button" data-act="set-sak">设置站点</button>
              </div>
            </div>
          </div>
          <button class="ptaexp-icon-btn" type="button" data-act="close" aria-label="关闭">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            </svg>
          </button>
        </div>

        <div class="ptaexp-actions">
          <button class="ptaexp-action" data-act="parse" data-primary="1" type="button">${pageSupportState.parseLabel}</button>
          <button class="ptaexp-action" data-act="download" type="button" disabled>下载 JSON</button>
          <button class="ptaexp-action" data-act="import-bank" data-primary="1" type="button" disabled>一键导入题库</button>
          <button class="ptaexp-action" data-act="word" type="button" disabled>导出 Word</button>
          <button class="ptaexp-action" data-act="pdf" type="button" disabled>导出 PDF</button>
          <button class="ptaexp-action" data-act="unlock" type="button">解锁选项</button>
          <button class="ptaexp-action" data-act="open-sak" type="button">打开题库</button>
        </div>

        <div class="ptaexp-log" data-el="log">
          <div class="ptaexp-log-body" data-el="log-body" role="log" aria-label="运行日志"></div>
        </div>

        <div class="ptaexp-muted">${readyHintText}</div>
        <div class="ptaexp-status" data-el="status">${pageSupportState.initialStatus}</div>
      </div>

      <div class="ptaexp-sak-overlay" data-el="sak-overlay" aria-hidden="true">
        <div class="ptaexp-sak-card" role="dialog" aria-modal="true" aria-label="导出后提示">
          <div class="ptaexp-sak-head">
            <div class="ptaexp-sak-title" data-el="sak-title">导出完成</div>
            <button class="ptaexp-icon-btn" type="button" data-act="sak-close" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
              </svg>
            </button>
          </div>
          <div class="ptaexp-sak-body">
            <div class="ptaexp-sak-notice" data-el="sak-notice" role="alert" hidden></div>
            <div class="ptaexp-sak-msg" data-el="sak-msg"></div>
            <div class="ptaexp-sak-url" data-el="sak-url"></div>
            <div class="ptaexp-sak-setting" data-el="sak-setting-form">
              <input class="ptaexp-sak-input" type="url" data-el="sak-setting-input" placeholder="http://localhost:8000" />
              <div class="ptaexp-sak-error" data-el="sak-setting-error"></div>
              <div class="ptaexp-sak-setting-actions">
                <button class="ptaexp-action" type="button" data-act="sak-setting-cancel">取消</button>
                <button class="ptaexp-action" type="button" data-act="sak-setting-save" data-primary="1">保存</button>
              </div>
            </div>
          </div>
          <div class="ptaexp-sak-actions">
            <button class="ptaexp-action" type="button" data-act="sak-setting">设置站点</button>
            <button class="ptaexp-action" type="button" data-act="sak-copy">复制地址</button>
            <button class="ptaexp-action" type="button" data-act="sak-open" data-primary="1">打开题库</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(root);

    const btn = root.querySelector('[data-el=\"fab\"]');
    const panel = root.querySelector('.ptaexp-panel');
    const statusEl = root.querySelector('[data-el=\"status\"]');
    const summaryEl = root.querySelector('[data-el=\"summary\"]');

    const sakOverlay = root.querySelector('[data-el="sak-overlay"]');
    const sakTitleEl = root.querySelector('[data-el="sak-title"]');
    const sakNoticeEl = root.querySelector('[data-el="sak-notice"]');
    const sakMsgEl = root.querySelector('[data-el="sak-msg"]');
    const sakUrlEl = root.querySelector('[data-el="sak-url"]');
    const sakSettingFormEl = root.querySelector('[data-el="sak-setting-form"]');
    const sakSettingInputEl = root.querySelector('[data-el="sak-setting-input"]');
    const sakSettingErrorEl = root.querySelector('[data-el="sak-setting-error"]');

    const logBodyEl = root.querySelector('[data-el="log-body"]');
    const logLines = [];
    const MAX_LOG_LINES = 120;

    function formatTime(d) {
      const pad = (n) => String(n).padStart(2, '0');
      const dt = d instanceof Date ? d : new Date();
      return `${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`;
    }

    function pushLog(message) {
      const m = String(message || '').trim();
      const line = `[${formatTime(new Date())}] ${m || '—'}`;
      logLines.push(line);
      if (logLines.length > MAX_LOG_LINES) logLines.splice(0, logLines.length - MAX_LOG_LINES);
      if (logBodyEl) {
        logBodyEl.textContent = logLines.join('\n');
        logBodyEl.scrollTop = logBodyEl.scrollHeight;
      }
    }

    function hideSakPromoModal() {
      if (!sakOverlay) return;
      sakOverlay.classList.remove('show');
      sakOverlay.setAttribute('aria-hidden', 'true');
      closeSakSettingForm();
    }

    function closeSakSettingForm() {
      if (sakSettingFormEl) sakSettingFormEl.classList.remove('show');
      if (sakSettingErrorEl) sakSettingErrorEl.textContent = '';
    }

    function openSakSettingForm() {
      showSakPromoModal('settings', '', { title: '设置题库网站地址' });
      if (sakSettingInputEl) {
        sakSettingInputEl.value = getSakSiteUrl();
        setTimeout(() => {
          sakSettingInputEl.focus();
          sakSettingInputEl.select();
        }, 0);
      }
      if (sakSettingErrorEl) sakSettingErrorEl.textContent = '';
      if (sakSettingFormEl) sakSettingFormEl.classList.add('show');
    }

    function saveSakSiteUrlFromForm() {
      const raw = sakSettingInputEl ? sakSettingInputEl.value : '';
      const v = String(raw || '').trim().replace(/\/+$/g, '');
      if (!/^https?:\/\//i.test(v)) {
        if (sakSettingErrorEl) sakSettingErrorEl.textContent = '地址需以 http:// 或 https:// 开头';
        return;
      }
      try {
        localStorage.setItem(SAK_SITE_URL_KEY, v);
      } catch (e) {
        if (sakSettingErrorEl) sakSettingErrorEl.textContent = '保存失败，请检查浏览器存储权限';
        return;
      }
      if (sakUrlEl) sakUrlEl.textContent = v;
      closeSakSettingForm();
      setStatus('题库网站地址已更新');
      pushLog(`题库网站地址已更新：${v}`);
    }

    function showSakPromoModal(exportType, fileName, opts) {
      if (!sakOverlay) return;
      const o = opts && typeof opts === 'object' ? opts : {};
      const notice = String(o.notice || '').trim();
      const title = String(o.title || '').trim() || (exportType === 'help' ? '全流程指南' : '导出完成');
      if (sakTitleEl) sakTitleEl.textContent = title;
      if (sakNoticeEl) {
        sakNoticeEl.textContent = notice;
        sakNoticeEl.hidden = !notice;
      }
      if (sakMsgEl) sakMsgEl.textContent = buildSakPromoMessage(exportType, fileName);
      if (sakUrlEl) sakUrlEl.textContent = getSakSiteUrl();
      sakOverlay.classList.add('show');
      sakOverlay.setAttribute('aria-hidden', 'false');
      if (exportType !== 'settings') closeSakSettingForm();
    }

    let lastParsed = null;
    let needsReparse = false;
    let booleanFixedCount = 0;
    let hasShownBooleanFixNotice = false;

    const requiresParseButtons = Array.from(
      root.querySelectorAll('[data-act="download"], [data-act="import-bank"], [data-act="word"], [data-act="pdf"]')
    );
    const watchScope = document.querySelector('#exam-app') || document.body;

    pushLog(getReadyLogText());

    function markManualEdited(target) {
      if (!(target instanceof HTMLElement)) return false;
      if (!target.matches('input, textarea, select')) return false;
      if (target.closest(`#${TOOL_ID}`)) return false;
      const qBlock = target.closest('div.pc-x[id]');
      if (!qBlock) return false;
      qBlock.setAttribute(MANUAL_EDIT_ATTR, '1');
      needsReparse = true;
      return true;
    }

    function onEditableChanged(e) {
      const t = e.target;
      if (!(t instanceof HTMLElement)) return;
      markManualEdited(t);
    }

    watchScope.addEventListener('input', onEditableChanged, true);
    watchScope.addEventListener('change', onEditableChanged, true);

    function setStatus(msg) {
      statusEl.textContent = String(msg || '').trim() || '—';
    }

    function setSummary(text) {
      summaryEl.textContent = String(text || '').trim() || '—';
    }

    function setExportEnabled(enabled) {
      for (const b of requiresParseButtons) b.disabled = !enabled;
    }

    function normalizeIndexList(list) {
      const arr = Array.isArray(list) ? list : [];
      const nums = arr
        .map((x) => Number(x))
        .filter((n) => Number.isInteger(n) && n > 0)
        .sort((a, b) => a - b);
      const out = [];
      let last = null;
      for (const n of nums) {
        if (last === n) continue;
        out.push(n);
        last = n;
      }
      return out;
    }

    function formatIndexRanges(indices) {
      const list = normalizeIndexList(indices);
      if (!list.length) return '';
      const parts = [];
      let start = list[0];
      let prev = list[0];
      for (let i = 1; i < list.length; i++) {
        const cur = list[i];
        if (cur === prev + 1) {
          prev = cur;
          continue;
        }
        parts.push(start === prev ? String(start) : `${start}-${prev}`);
        start = cur;
        prev = cur;
      }
      parts.push(start === prev ? String(start) : `${start}-${prev}`);
      return parts.join('、');
    }

    function formatIndexPreview(indices, maxItems) {
      const list = normalizeIndexList(indices);
      const max = Number.isInteger(maxItems) && maxItems > 0 ? maxItems : 30;
      if (!list.length) return '';
      if (list.length <= max) return formatIndexRanges(list);
      const head = list.slice(0, max);
      return `${formatIndexRanges(head)}…（共${list.length}题）`;
    }

    function isMeaningfulAnswer(answer, type) {
      const t = String(type || '').trim();
      const a = Array.isArray(answer) ? answer : [];
      if (!a.length) return false;
      if (t === 'fill') {
        return a.some((blank) => Array.isArray(blank) && blank.some((x) => String(x || '').trim()));
      }
      return a.some((v) => {
        if (typeof v === 'boolean') return true;
        if (typeof v === 'number') return Number.isFinite(v);
        return String(v || '').trim() !== '';
      });
    }

    function collectExportIssues(parsed) {
      const list = Array.isArray(parsed?.questions) ? parsed.questions : [];
      const out = {
        booleanFixedIndices: [],
        needVerifyIndices: [],
        noAnswerIndices: [],
      };

      for (let i = 0; i < list.length; i++) {
        const q = list[i];
        const type = String(q?.type || '').trim();
        const idx = i + 1;

        if (type === 'boolean' && q?.__boolCorrected) out.booleanFixedIndices.push(idx);

        if (type === 'single_choice' || type === 'multi_choice' || type === 'fill') {
          if (q?.__answerCertain === false) out.needVerifyIndices.push(idx);
        }

        if (type === 'single_choice' || type === 'multi_choice' || type === 'boolean' || type === 'fill') {
          if (!isMeaningfulAnswer(q?.answer, type)) out.noAnswerIndices.push(idx);
        }
      }

      out.booleanFixedIndices = normalizeIndexList(out.booleanFixedIndices);
      out.needVerifyIndices = normalizeIndexList(out.needVerifyIndices);
      out.noAnswerIndices = normalizeIndexList(out.noAnswerIndices);
      return out;
    }

    function buildAnswerIssueNotice(issues) {
      const noAns = normalizeIndexList(issues?.noAnswerIndices);
      const needVerify = normalizeIndexList(issues?.needVerifyIndices);
      const noSet = new Set(noAns);
      const verifyOnly = needVerify.filter((n) => !noSet.has(n));

      const lines = [];
      if (verifyOnly.length) lines.push(`答案错误/需核对题号：${formatIndexPreview(verifyOnly, 30)}`);
      if (noAns.length) lines.push(`无答案题号：${formatIndexPreview(noAns, 30)}`);
      return lines.join('\n');
    }

    function consumeBooleanFixNotice(booleanFixedIndices) {
      if (hasShownBooleanFixNotice) return '';
      const n = Number(booleanFixedCount || 0);
      if (!n) return '';
      hasShownBooleanFixNotice = true;
      const idxText = Array.isArray(booleanFixedIndices) && booleanFixedIndices.length ? `（题号：${formatIndexPreview(booleanFixedIndices, 24)}）` : '';
      return n === 1
        ? `判断题：检测到 1 道“答案错误”，已自动修正导出答案${idxText}`
        : `判断题：检测到 ${n} 道“答案错误”，已自动修正导出答案${idxText}`;
    }

    function getParsedForCurrentSelection() {
      return lastParsed || { questions: [] };
    }

    function getCurrentPayload() {
      const parsed = getParsedForCurrentSelection();
      return buildExportPayload(parsed, { difficulty: DEFAULT_DIFFICULTY, exportMode: 'pqf' });
    }

    function getParseFailureMessage(error) {
      return String(error?.message || error || '未知错误').trim() || '未知错误';
    }

    function shouldShowParseFailureModal(message) {
      return /当前页面暂不支持导出|雨课堂登录态缺失或无权限|show_paper 拉取失败/.test(String(message || ''));
    }

    function buildParsedTypeLabel(stats) {
      const counts = (stats && typeof stats === 'object' && stats.type_counts) || {};
      const items = [
        { key: 'single_choice', label: '单选题', short: '单选' },
        { key: 'multi_choice', label: '多选题', short: '多选' },
        { key: 'boolean', label: '判断题', short: '判断' },
        { key: 'fill', label: '填空题', short: '填空' },
        { key: 'essay', label: '简答题', short: '简答' },
      ];

      const present = items
        .map((it) => ({ ...it, count: Number(counts[it.key] || 0) }))
        .filter((it) => Number.isFinite(it.count) && it.count > 0);

      if (!present.length) return '题目';

      present.sort((a, b) => {
        const d = b.count - a.count;
        if (d) return d;
        return items.findIndex((x) => x.key === a.key) - items.findIndex((x) => x.key === b.key);
      });

      if (present.length === 1) return present[0].label;

      const shorts = present.slice(0, 3).map((it) => it.short);
      if (present.length > 3) shorts.push('…');
      return `混合题（${shorts.join('/')}）`;
    }

    function updateSummary() {
      if (!lastParsed) {
        setSummary('未解析｜格式：PQF（固定）');
        setExportEnabled(false);
        return;
      }
      const st = lastParsed.stats || {};
      const parsed = getParsedForCurrentSelection();
      const payload = buildExportPayload(parsed, {
        difficulty: DEFAULT_DIFFICULTY,
        exportMode: 'pqf',
      });
      const parsedCount = typeof st.parsed === 'number' ? st.parsed : Array.isArray(lastParsed.questions) ? lastParsed.questions.length : 0;
      const exportCount = Array.isArray(payload.questions) ? payload.questions.length : 0;
      const needVerify = typeof st.need_verify === 'number' ? st.need_verify : 0;
      const typeLabel = buildParsedTypeLabel(st);
      setSummary(`解析 ${parsedCount} 道 ${typeLabel}｜需核对 ${needVerify}`);
      setExportEnabled(exportCount > 0);
    }

    async function doParse() {
      const currentSupportState = getPageSupportState();
      if (!currentSupportState.supported) {
        lastParsed = null;
        needsReparse = false;
        updateSummary();
        setStatus(currentSupportState.initialStatus);
        pushLog(currentSupportState.readyLog);
        showSakPromoModal('unsupported', '', {
          title: '暂不支持当前页面',
          notice: currentSupportState.initialStatus,
        });
        return null;
      }

      pushLog('开始解析题目…');
      setStatus('解析中…');
      setExportEnabled(false);
      try {
        const data = await exportPortableJson({});
        lastParsed = data;
        needsReparse = false;
        booleanFixedCount = Number(data?.stats?.boolean_corrected || 0);
        hasShownBooleanFixNotice = false;
        updateSummary();
        const parsedNum = Array.isArray(data.questions) ? data.questions.length : 0;
        setStatus(`已解析：${parsedNum} 题`);
        pushLog(`解析完成：${parsedNum} 题`);
        if (booleanFixedCount) pushLog(`判断题自动修正：${booleanFixedCount} 题`);
        const needVerify = Number(data?.stats?.need_verify || 0);
        if (needVerify) pushLog(`需要核对答案：${needVerify} 题`);
        return data;
      } catch (e) {
        lastParsed = null;
        needsReparse = false;
        updateSummary();
        const message = getParseFailureMessage(e);
        setStatus(`解析失败：${message}`);
        pushLog(`解析失败：${message}`);
        if (shouldShowParseFailureModal(message)) {
          showSakPromoModal('parse-error', '', {
            title: '解析失败',
            notice: message,
          });
        }
        console.warn('[PTA题目导出] 解析失败：', e);
        return null;
      }
    }

    function openPanel() {
      panel.classList.add('show');
      btn.setAttribute('aria-expanded', 'true');
      updateSummary();
    }

    function closePanel() {
      panel.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', () => {
      if (panel.classList.contains('show')) closePanel();
      else openPanel();
    });

    document.addEventListener(
      'click',
      (e) => {
        if (!panel.classList.contains('show')) return;
        const t = e.target;
        if (!(t instanceof Node)) return;
        if (root.contains(t)) return;
        closePanel();
      },
      true
    );

    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      if (sakOverlay && sakOverlay.classList.contains('show')) {
        hideSakPromoModal();
        return;
      }
      if (panel.classList.contains('show')) closePanel();
    });

    if (sakOverlay) {
      sakOverlay.addEventListener('click', (e) => {
        if (e.target === sakOverlay) hideSakPromoModal();
      });
    }

    root.addEventListener('click', async (e) => {
      const t = e.target;
      if (!(t instanceof HTMLElement)) return;
      const actEl = t.closest('[data-act]');
      const act = actEl ? actEl.getAttribute('data-act') : null;
      if (!act) return;

      if (act === 'sak-close') {
        hideSakPromoModal();
        return;
      }
      if (act === 'sak-open') {
        window.open(sakResolveUrl('/user/banks'), '_blank');
        hideSakPromoModal();
        pushLog('已从弹窗打开题库');
        return;
      }
      if (act === 'sak-copy') {
        const ok = await copyToClipboard(getSakSiteUrl());
        setStatus(ok ? '已复制题库网站地址' : '复制失败：请手动复制地址');
        if (ok) pushLog('已复制题库网站地址');
        return;
      }
      if (act === 'sak-setting' || act === 'set-sak') {
        openSakSettingForm();
        return;
      }
      if (act === 'sak-setting-save') {
        saveSakSiteUrlFromForm();
        return;
      }
      if (act === 'sak-setting-cancel') {
        closeSakSettingForm();
        return;
      }

      if (act === 'close') {
        closePanel();
        return;
      }
      if (act === 'parse') {
        await doParse();
        return;
      }
      if (act === 'unlock') {
        const count = unlockAllInputs();
        setStatus(count ? `已解锁：${count} 个输入控件` : '未找到可解锁的输入控件');
        pushLog(count ? `已解锁输入控件：${count} 个` : '未找到可解锁的输入控件');
        return;
      }
      if (act === 'open-sak') {
        window.open(sakResolveUrl('/user/banks'), '_blank');
        setStatus('已打开题库网站');
        pushLog('已打开题库网站');
        return;
      }
      if (act === 'guide') {
        showSakPromoModal('help', '');
        return;
      }

      if (!lastParsed) {
        setStatus('请先点击“解析题目”');
        return;
      }
      if (needsReparse) {
        const reparsed = await doParse();
        if (!reparsed) return;
      }
      const parsed = getParsedForCurrentSelection();
      const issues = collectExportIssues(parsed);

      if (act === 'download') {
        const notice = [consumeBooleanFixNotice(issues.booleanFixedIndices), buildAnswerIssueNotice(issues)].filter(Boolean).join('\n');
        const payload = getCurrentPayload();
        const text = JSON.stringify(payload, null, 2);
        const filename = buildDefaultFilename();
        downloadTextFile(filename, text);
        setStatus(`已下载：${payload.questions.length} 题`);
        pushLog(`已下载 JSON：${payload.questions.length} 题（${filename}）`);
        showSakPromoModal('json-download', filename, { notice });
        return;
      }
      if (act === 'import-bank') {
        const notice = [consumeBooleanFixNotice(issues.booleanFixedIndices), buildAnswerIssueNotice(issues)].filter(Boolean).join('\n');
        const payload = getCurrentPayload();
        setStatus('正在导入题库…');
        pushLog(`开始导入题库：${payload.questions.length} 题`);
        try {
          const imported = await importPayloadToSakBank(payload);
          if (!imported) {
            setStatus('已取消导入');
            pushLog('已取消导入题库');
            return;
          }
          const importedCount = Number(imported?.result?.data?.imported || payload.questions.length || 0);
          setStatus(`已导入题库：${importedCount} 题`);
          pushLog(`已导入个人题库 ${imported.bankId}：${importedCount} 题`);
          showSakPromoModal('bank-import', `ID ${imported.bankId}`, { notice });
        } catch (error) {
          const message = String(error?.message || error || '导入失败');
          setStatus(`导入失败：${message}`);
          pushLog(`导入失败：${message}`);
          showSakPromoModal('parse-error', '', { title: '导入失败', notice: message });
        }
        return;
      }
      if (act === 'word') {
        const notice = [consumeBooleanFixNotice(issues.booleanFixedIndices), buildAnswerIssueNotice(issues)].filter(Boolean).join('\n');
        const payload = buildLegacyExportPayload(parsed, {
          difficulty: DEFAULT_DIFFICULTY,
        });
        setStatus('导出 Word…');
        const docxName = buildDefaultDocxFilename().replace(/\.docx$/i, '_题库导入.docx');
        if (canExportDocx()) {
          try {
            await exportLegacyPayloadToDocx(payload, docxName);
            setStatus(`已导出 Word：${payload.questions.length} 题`);
            pushLog(`已导出 Word：${payload.questions.length} 题（${docxName}）`);
            showSakPromoModal('docx', docxName, { notice });
          } catch (e) {
            console.warn('[PTA题目导出] 导出 docx 失败，回退为 .doc：', e);
            const filename = buildDefaultWordFilename().replace(/\.doc$/i, '_题库导入.doc');
            const html = buildLegacyExportHtml(payload);
            downloadTextFile(filename, `\ufeff${html}`, 'application/msword;charset=utf-8');
            setStatus(`已导出 Word：${payload.questions.length} 题（.doc）`);
            pushLog(`已导出 Word（.doc）：${payload.questions.length} 题（${filename}）`);
            showSakPromoModal('doc', filename, { notice });
          }
          return;
        }

        const filename = buildDefaultWordFilename().replace(/\.doc$/i, '_题库导入.doc');
        const html = buildLegacyExportHtml(payload);
        downloadTextFile(filename, `\ufeff${html}`, 'application/msword;charset=utf-8');
        setStatus(`已导出 Word：${payload.questions.length} 题（.doc）`);
        pushLog(`已导出 Word（.doc）：${payload.questions.length} 题（${filename}）`);
        showSakPromoModal('doc', filename, { notice });
        return;
      }
      if (act === 'pdf') {
        const notice = [consumeBooleanFixNotice(issues.booleanFixedIndices), buildAnswerIssueNotice(issues)].filter(Boolean).join('\n');
        const payload = buildLegacyExportPayload(parsed, {
          difficulty: DEFAULT_DIFFICULTY,
        });
        const pdfName = buildDefaultPdfFilename().replace(/\.pdf$/i, '_题库导入.pdf');
        if (canExportPdf()) {
          setStatus('生成 PDF…');
          try {
            await exportLegacyPayloadToPdf(payload, pdfName);
            setStatus(`已导出 PDF：${payload.questions.length} 题`);
            pushLog(`已导出 PDF：${payload.questions.length} 题（${pdfName}）`);
            showSakPromoModal('pdf', pdfName, { notice });
          } catch (e) {
            console.warn('[PTA题目导出] 导出 PDF 失败，回退为打印：', e);
            setStatus('打开打印预览…');
            const ok = openPrintWindow(buildLegacyExportHtml(payload));
            setStatus(ok ? '已打开打印预览：请选择“另存为 PDF”' : '打开失败：浏览器拦截弹窗（允许弹窗后重试）');
            if (ok) showSakPromoModal('print', '', { notice });
          }
          return;
        }

        setStatus('打开打印预览…');
        const ok = openPrintWindow(buildLegacyExportHtml(payload));
        setStatus(ok ? '已打开打印预览：请选择“另存为 PDF”' : '打开失败：浏览器拦截弹窗（允许弹窗后重试）');
        if (ok) showSakPromoModal('print', '', { notice });
        return;
      }
    });

    // 便于手动调用
    window.__ptaExport = {
      exportPortableJson,
      buildExportPayload,
      buildLegacyExportPayload,
      getQuestionBlocks,
      getPageSupportState,
      fetchYuketangShowPaperPayload,
      buildYuketangShowPaperFetchErrorMessage,
      buildYuketangPortableJson,
      buildExportHtml,
      buildLegacyExportHtml,
      openPrintWindow,
      unlockAllInputs,
    };
  }

  function start() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => mountUI(), { once: true });
      return;
    }
    mountUI();
  }

  try {
    start();
  } catch (e) {
    console.error('[PTA题目导出] 初始化失败：', e);
  }
})();
