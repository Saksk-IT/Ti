// ==UserScript==
// @name         学习通全能作业导出助手
// @version      1.1.0
// @description  none
// @author       Saksk
// @match      *://mooc1.chaoxing.com/mooc2/work/view*
// @match      *://mooc1.chaoxing.com/exam-ans/exam/test/reVersionPaperMarkContentNew*
// @match      *://mooc1.chaoxing.com/mooc-ans/mooc2/work/*
// @match      *://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu*
// @match      *://mobilelearn.chaoxing.com/page/quiz/stu/quizStudentQuestion*
// @grant        GM_addStyle
// @grant        GM_setClipboard
// @grant        GM_xmlhttpRequest
// @connect      mobilelearn.chaoxing.com
// @connect      mooc2-ans.chaoxing.com
// @require      https://unpkg.com/docx@7.1.1/build/index.js
// @require      https://unpkg.com/file-saver@2.0.5/dist/FileSaver.min.js
// @require      https://unpkg.com/xlsx@0.17.0/dist/xlsx.full.min.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js
// ==/UserScript==

(function() {
    'use strict';

    let parsedData = [];

    // =======================
    // 导出后引流到题库网站（可按需修改）
    // =======================
    const SAK_SITE_NAME = 'SAK 题库';
    const SAK_SITE_URL_KEY = 'sak_site_url_v1';
    const DEFAULT_SAK_SITE_URL = 'http://localhost:5000';

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

    // =============
    // 题库导入适配
    // =============
    function normalizeNewlines(text) {
        return String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    }

    // 修复部分页面“中文字符被空格打散”的情况（常见于简答题/解析的富文本转纯文本）
    // 仅在检测到明显异常（大量“中 文”形态）时才执行，避免误伤英文/数字空格。
    function maybeCompactCjkSpacing(text) {
        let t = normalizeNewlines(text);
        if (!t) return '';
        // 去掉常见不可见字符，统一空格类型
        t = t.replace(/[\u200B-\u200D\uFEFF]/g, '');
        t = t.replace(/\u00A0/g, ' ').replace(/\u3000/g, ' ');

        const cjkCount = (t.match(/[\u4E00-\u9FFF]/g) || []).length;
        const spacedPairs = (t.match(/[\u4E00-\u9FFF][ \t]+[\u4E00-\u9FFF]/g) || []).length;
        const looksBad = cjkCount && spacedPairs >= 6 && (spacedPairs / cjkCount) > 0.25;
        if (!looksBad) return t;

        // 移除“中文字符之间的空格”，保留英文/数字间正常空格
        t = t.replace(/([\u4E00-\u9FFF])[ \t]+(?=[\u4E00-\u9FFF])/g, '$1');
        // 清理中文标点附近多余空格
        t = t.replace(/[ \t]+([，。！？；：、）】》〉”’])/g, '$1');
        t = t.replace(/([（【《〈“‘])[ \t]+/g, '$1');
        return t;
    }

    function stripOptionPrefix(raw) {
        const line = String(raw || '').trim();
        return line.replace(/^\s*\(?[A-F]([\.、\s\)]|$)\s*/i, '');
    }

    function normalizeStemForBank(stem) {
        return normalizeNewlines(stem)
            .replace(/(\(\s*\)|（\s*）|_{2,})/g, '__')
            .replace(/\s+$/g, '');
    }

    function countStemBlanks(stem) {
        const s = String(stem || '');
        const m = s.match(/__/g);
        return m ? m.length : 0;
    }

    function stripFillLeadingIndex(text) {
        let t = normalizeNewlines(text);
        // 去掉填空题答案中的空序号，如：“(1) (1) ...” / “(1);...” / “（1）...”
        t = t.replace(/^[\s\u00A0]*(?:(?:\(\s*\d+\s*\)|（\s*\d+\s*）)[\s\u00A0]*)+/g, '');
        // 去掉序号后残留的分隔符
        t = t.replace(/^[\s\u00A0]*[;；:：]+[\s\u00A0]*/g, '');
        return t;
    }

    function splitFillAnswerByIndexMarkers(rawAnswer) {
        const s = normalizeNewlines(rawAnswer);
        const re = /(\(\s*(\d+)\s*\)|（\s*(\d+)\s*）)/g;
        const markers = [];
        let m;
        while ((m = re.exec(s)) !== null) {
            markers.push({
                idx: Number(m[2] || m[3] || 0),
                start: m.index,
                end: m.index + m[0].length
            });
        }
        if (!markers.length) return null;

        const segs = [];
        for (let i = 0; i < markers.length; i++) {
            const start = markers[i].end;
            const end = (i + 1 < markers.length) ? markers[i + 1].start : s.length;
            let chunk = s.slice(start, end);
            chunk = stripFillLeadingIndex(chunk).trim();
            if (!chunk) continue;
            segs.push({ idx: markers[i].idx || (segs.length + 1), text: chunk });
        }
        if (!segs.length) return null;

        // 合并连续重复序号（常见："(1) (1) 140;..."）
        const merged = [];
        segs.forEach((seg) => {
            const last = merged[merged.length - 1];
            if (last && last.idx === seg.idx) last.text = `${last.text}\n${seg.text}`;
            else merged.push({ ...seg });
        });
        return merged;
    }

    function normalizeFillBlankTextToStorage(text) {
        let t = stripFillLeadingIndex(text);
        t = normalizeNewlines(t).trim();
        if (!t) return '';
        // 将常见“同一空多答案”分隔符统一为 ";"（避免误伤 URL，如 "://"）
        t = t.replace(/\s*；\s*/g, ';'); // 全角分号
        t = t.replace(/\s*\|\s*/g, ';');
        t = t.replace(/\s+\/\s+/g, ';');
        t = t.replace(/\n+/g, ';'); // 多行答案
        // 统一分号间距
        t = t.replace(/\s*;\s*/g, ';').replace(/;{2,}/g, ';');
        return t.trim();
    }

    function guessBankQType(rawType, stem, options, rawAnswer) {
        const t = String(rawType || '').replace(/\s+/g, '');
        if (/多选/.test(t)) return '多选题';
        if (/单选|选择/.test(t)) return '选择题';
        if (/判断/.test(t)) return '判断题';
        if (/填空/.test(t)) return '填空题';
        if (/简答|主观|问答|论述|解答|计算/.test(t)) return '简答题';

        const opt = Array.isArray(options) ? options : [];
        const ans = String(rawAnswer || '');

        if (opt && opt.length) {
            const letters = (ans.toUpperCase().match(/[A-F]/g) || []);
            if (letters.length > 1) return '多选题';
            if (opt.length === 2 && /[对错√×TF]/i.test(ans)) return '判断题';
            return '选择题';
        }

        if (/__|\(\s*\)|（\s*）|_{2,}/.test(String(stem || ''))) return '填空题';
        if (/[;；]|\s{2,}|\n/.test(ans)) return '填空题';
        return '简答题';
    }

    function normalizeChoiceAnswer(rawAnswer, isMultiple) {
        const letters = (String(rawAnswer || '').toUpperCase().match(/[A-F]/g) || []);
        const uniq = Array.from(new Set(letters));
        uniq.sort();
        if (!uniq.length) return '';
        return isMultiple ? uniq.join('') : uniq[0];
    }

    function normalizeJudgeAnswerCanonical(rawAnswer, options) {
        const a = String(rawAnswer || '').replace(/\s+/g, '').toUpperCase();
        if (!a) return '';
        if (a === '正确' || a === '对' || a === 'T' || a === 'TRUE' || a === '√') return '正确';
        if (a === '错误' || a === '错' || a === 'F' || a === 'FALSE' || a === '×') return '错误';
        if (a === 'A' || a === 'B') {
            const first = String((options && options[0]) || '').toUpperCase();
            const firstLooksFalse = /错|错误|FALSE|×/.test(first);
            if (a === 'A') return firstLooksFalse ? '错误' : '正确';
            return firstLooksFalse ? '正确' : '错误';
        }
        return '';
    }

    function formatFillAnswerForStorage(rawAnswer) {
        return formatFillAnswerForStorageWithStem(rawAnswer, '');
    }

    function formatFillAnswerForStorageWithStem(rawAnswer, stem) {
        const raw = normalizeNewlines(rawAnswer).trim();
        if (!raw) return '';

        const blanksInStem = countStemBlanks(stem);
        const segs = splitFillAnswerByIndexMarkers(raw);
        if (segs) {
            const blanks = segs.map((s) => normalizeFillBlankTextToStorage(s.text)).filter(Boolean);
            if (!blanks.length) return '';
            if (blanks.length === 1) return blanks[0];
            return blanks.join(';;');
        }

        // 单空：保留“;”为同一空的多答案（后续导出 Word 会转为 “/”）
        if (blanksInStem <= 1) return normalizeFillBlankTextToStorage(raw);

        // 多空：优先按换行/多空格切分为空（避免与同空多答案 ";" 冲突）
        let parts = raw
            .split(/\s{2,}|\n/)
            .map((p) => String(p || '').trim())
            .filter(Boolean);

        if (parts.length > blanksInStem && parts.length % blanksInStem === 0) {
            const groupSize = parts.length / blanksInStem;
            const grouped = [];
            for (let i = 0; i < blanksInStem; i++) {
                grouped.push(parts.slice(i * groupSize, (i + 1) * groupSize).join('\n'));
            }
            parts = grouped;
        }

        // 若仍无法切分，再尝试把 ";/；" 当作“空与空”的分隔（有些页面会这样拼在一行）
        if (parts.length <= 1 && /[;；]/.test(raw)) {
            const semiParts = raw
                .split(/[;；]/)
                .map((p) => String(p || '').trim())
                .filter(Boolean);
            if (semiParts.length === blanksInStem) {
                parts = semiParts;
            } else if (semiParts.length > blanksInStem && semiParts.length % blanksInStem === 0) {
                const groupSize = semiParts.length / blanksInStem;
                const grouped = [];
                for (let i = 0; i < blanksInStem; i++) {
                    grouped.push(semiParts.slice(i * groupSize, (i + 1) * groupSize).join(';'));
                }
                parts = grouped;
            } else if (semiParts.length > 1) {
                parts = semiParts;
            }
        }
        return parts
            .map((p) => normalizeFillBlankTextToStorage(p))
            .filter(Boolean)
            .join(';;');
    }

    // Word 导入解析器会把“;”当作空与空之间的分隔符；把“/”或“|”当作同一空的多答案。
    // 因此：存储格式（;; 分隔空）需要转换成 Word 友好格式（; 分隔空，/ 分隔同空多答案）。
    function formatFillAnswerForWordFromStorage(storageAnswer) {
        const s = String(storageAnswer || '').trim();
        if (!s) return '';
        const blanks = s.split(';;').map((x) => String(x || '').trim()).filter(Boolean);
        const wordParts = blanks.map((b) => b.replace(/;/g, '/'));
        return wordParts.join(';');
    }

    function normalizeAnswerForBankStorage(qType, rawAnswer, options, stem) {
        const qt = String(qType || '').trim();
        const ans = normalizeNewlines(rawAnswer);
        if (qt === '选择题') return normalizeChoiceAnswer(ans, false);
        if (qt === '多选题') return normalizeChoiceAnswer(ans, true);
        if (qt === '判断题') return normalizeJudgeAnswerCanonical(ans, options);
        if (qt === '填空题') return formatFillAnswerForStorageWithStem(ans, stem);
        // 简答/其它：保留多行
        return maybeCompactCjkSpacing(String(ans || '').replace(/\s+$/g, ''));
    }

    // =========================
    // 统一 JSON 导入/导出格式
    // =========================
    function qTypeToPortableType(qType) {
        const t = String(qType || '').trim();
        if (t === '选择题') return 'single_choice';
        if (t === '多选题') return 'multi_choice';
        if (t === '判断题') return 'boolean';
        if (t === '填空题') return 'fill';
        return 'essay';
    }

    function fillContentInternalToPortable(content) {
        const text = normalizeNewlines(content).replace(/\s+$/g, '');
        if (!text.includes('__')) return text;
        const parts = text.split('__');
        if (parts.length <= 1) return text;
        let out = '';
        for (let i = 0; i < parts.length; i++) {
            out += parts[i];
            if (i < parts.length - 1) out += `{${i}}`;
        }
        return out;
    }

    function choiceLettersToIndices(rawAnswer) {
        const letters = (String(rawAnswer || '').toUpperCase().match(/[A-Z]/g) || []);
        const uniq = Array.from(new Set(letters));
        uniq.sort();
        return uniq
            .map((c) => c.charCodeAt(0) - 'A'.charCodeAt(0))
            .filter((n) => Number.isInteger(n) && n >= 0 && n < 26);
    }

    function booleanStorageToPortable(rawAnswer) {
        const a = String(rawAnswer || '').replace(/\s+/g, '').toUpperCase();
        if (!a) return [];
        if (a === '正确' || a === '对' || a === 'T' || a === 'TRUE' || a === '√') return [true];
        if (a === '错误' || a === '错' || a === 'F' || a === 'FALSE' || a === '×') return [false];
        return [];
    }

    function fillStorageToPortable(storageAnswer) {
        const s = String(storageAnswer || '').trim();
        if (!s) return [];
        const blanks = s.split(';;').map((x) => String(x || '').trim());
        return blanks.map((b) => b ? b.split(';').map((x) => String(x || '').trim()).filter(Boolean) : []);
    }

    function buildPortableExportJson(questions, defaultDifficulty) {
        let diff = Number(defaultDifficulty || 3) || 3;
        diff = Math.max(1, Math.min(5, diff));
        const list = Array.isArray(questions) ? questions : [];
        return {
            questions: list.map((q) => {
                const qType = String(q.q_type || '').trim();
                const type = qTypeToPortableType(qType);
                const rawStem = normalizeNewlines(String(q.stem || '')).replace(/\s+$/g, '');
                const content = (type === 'fill') ? fillContentInternalToPortable(rawStem) : rawStem;

                let options = [];
                if (type === 'single_choice' || type === 'multi_choice') {
                    options = Array.isArray(q.options) ? q.options : [];
                } else if (type === 'boolean') {
                    options = ['正确', '错误'];
                }

                const storageAnswer = normalizeNewlines(String(q.answer || '')).replace(/\s+$/g, '');
                let answer = [];
                if (storageAnswer) {
                    if (type === 'single_choice') {
                        const idxs = choiceLettersToIndices(storageAnswer);
                        answer = idxs.length ? [idxs[0]] : [];
                    } else if (type === 'multi_choice') {
                        answer = choiceLettersToIndices(storageAnswer);
                    } else if (type === 'boolean') {
                        answer = booleanStorageToPortable(storageAnswer);
                    } else if (type === 'fill') {
                        answer = fillStorageToPortable(storageAnswer);
                    } else {
                        answer = [storageAnswer];
                    }
                }

                return {
                    id: Number(q.id) || null,
                    type,
                    content,
                    options,
                    answer,
                    analysis: String(q.analysis || '').trim(),
                    tags: [],
                    difficulty: diff
                };
            })
        };
    }

    // 1. UI 样式表
    GM_addStyle(`
        #menu-trigger {
            position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px;
            background: #fff; border: 2px solid #ff9a9e; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; box-shadow: 0 8px 24px rgba(255,154,158,0.25); z-index: 10002;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        #menu-trigger:hover { transform: scale(1.15) rotate(10deg); }
        #menu-trigger:active { transform: scale(0.9); }
        #menu-trigger .icon { font-size: 28px; }

        #export-panel {
            position: fixed; bottom: 105px; right: 30px; width: 280px;
            background: #fff; border-radius: 26px; box-shadow: 0 20px 60px rgba(0,0,0,0.12);
            z-index: 10001; padding: 24px; display: none; border: 1px solid #fdf2f2;
            transform-origin: bottom right; overflow: hidden;
        }
        .panel-show { display: block !important; animation: dropletIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }

        @keyframes dropletIn {
            0% { transform: scale(0.3) translateY(60px); opacity: 0; }
            100% { transform: scale(1) translateY(0); opacity: 1; }
        }

        /* 按钮通用样式 */
        .btn-stack button {
            position: relative; overflow: hidden;
            width: 100%; padding: 12px; border-radius: 14px; cursor: pointer;
            font-size: 13px; border: 1.5px solid #ffe4e6; background: transparent;
            color: #ff9a9e; font-weight: 500;
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }

        /* 悬停放大效果 */
        .btn-stack button:hover:not(:disabled) {
            transform: translateY(-2px) scale(1.04);
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }

        /* 按压瞬间反馈 */
        .btn-stack button:active:not(:disabled) { transform: scale(0.96); }

        /* 流光渐变动画 */
        @keyframes flow { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }

        .word-btn:hover:not(:disabled) { background: linear-gradient(90deg, #2b579a, #4a90e2, #2b579a) !important; background-size: 200% !important; animation: flow 2s infinite linear !important; color: white !important; border-color: transparent !important; }
        .pdf-btn:hover:not(:disabled) { background: linear-gradient(90deg, #f56c6c, #ff9a9e, #f56c6c) !important; background-size: 200% !important; animation: flow 2s infinite linear !important; color: white !important; border-color: transparent !important; }
        .xlsx-btn:hover:not(:disabled) { background: linear-gradient(90deg, #217346, #34a853, #217346) !important; background-size: 200% !important; animation: flow 2s infinite linear !important; color: white !important; border-color: transparent !important; }
        .md-btn:hover:not(:disabled) { background: linear-gradient(90deg, #444, #888, #444) !important; background-size: 200% !important; animation: flow 2s infinite linear !important; color: white !important; border-color: transparent !important; }
        .json-btn:hover:not(:disabled) { background: linear-gradient(90deg, #0f766e, #14b8a6, #0f766e) !important; background-size: 200% !important; animation: flow 2s infinite linear !important; color: white !important; border-color: transparent !important; }

        /* 初始高亮状态 (红色系) */
        .highlight-red { background: linear-gradient(135deg, #ff9a9e, #fecfef) !important; color: white !important; border: none !important; }

        /* 解析成功后的绿色状态 */
        .success-green {
            background: #f0fdf4 !important;
            color: #22c55e !important;
            border-color: #22c55e !important;
            font-weight: bold;
        }

        /* 水滴波纹 */
        .ripple {
            position: absolute; background: rgba(255, 255, 255, 0.5);
            border-radius: 50%; transform: scale(0); animation: rippleEffect 0.6s ease-out;
            pointer-events: none;
        }
        @keyframes rippleEffect { to { transform: scale(4); opacity: 0; } }

        #log-area {
            background: #fdf2f2; border-radius: 12px; padding: 10px; font-size: 11px;
            color: #ff9a9e; margin-bottom: 15px; font-family: monospace;
            max-height: 60px; overflow-y: auto; border: 1px solid #ffe4e6;
        }
        .btn-stack { display: flex; flex-direction: column; gap: 10px; }
        button:disabled { opacity: 0.3 !important; cursor: not-allowed !important; filter: grayscale(1); transform: none !important; }

        /* PDF 导出渲染区：尽量隔离页面样式，避免文字重叠，并保留换行/缩进 */
        #pdf-render-area {
            position: absolute;
            left: -9999px;
            top: 0;
            width: 800px;
            background: #fff;
            padding: 44px 50px;
            color: #111;
            font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "SimSun", Arial, sans-serif;
            font-size: 14px;
            line-height: 1.65;
            letter-spacing: 0;
            word-break: break-word;
            overflow-wrap: anywhere;
        }
        /* 覆盖学习通页面的全局样式，避免 line-height/font 造成的重叠 */
        #pdf-render-area, #pdf-render-area * {
            box-sizing: border-box;
            font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "SimSun", Arial, sans-serif !important;
            letter-spacing: 0 !important;
            line-height: 1.65 !important;
            tab-size: 4;
        }
        #pdf-render-area .sak-pdf-title {
            margin: 0 0 6px 0;
            text-align: center;
            font-size: 22px;
            font-weight: 800;
            line-height: 1.25 !important;
        }
        #pdf-render-area .sak-pdf-promo {
            margin: 0 0 16px 0;
            text-align: center;
            font-size: 12px;
            color: #0f766e;
            line-height: 1.35 !important;
        }
        #pdf-render-area .sak-pdf-item {
            margin: 0 0 14px 0;
            padding: 10px 0 14px;
            border-bottom: 1px solid #eee;
        }
        #pdf-render-area .sak-pdf-qtitle,
        #pdf-render-area .sak-pdf-options,
        #pdf-render-area .sak-pdf-answer,
        #pdf-render-area .sak-pdf-analysis {
            white-space: pre-wrap;
        }
        #pdf-render-area .sak-pdf-qtitle { font-weight: 700; }
        #pdf-render-area .sak-pdf-options { margin-top: 6px; color: #222; }
        #pdf-render-area .sak-pdf-answer { margin-top: 6px; color: #1a73e8; }
        #pdf-render-area .sak-pdf-analysis { margin-top: 6px; color: #555; }

        /* 导出后提醒弹窗（引导回到题库网站） */
        #sak-promo-overlay {
            position: fixed; inset: 0;
            display: none; align-items: flex-end; justify-content: center;
            padding: 14px 14px calc(14px + env(safe-area-inset-bottom));
            background: rgba(0,0,0,0.45);
            z-index: 10003;
        }
        #sak-promo-overlay.show { display: flex; }
        @media (min-width: 560px) {
            #sak-promo-overlay { align-items: center; }
        }
        #sak-promo-card {
            width: min(520px, 100%);
            background: #fff;
            border-radius: 22px;
            border: 1px solid #fdf2f2;
            box-shadow: 0 20px 60px rgba(0,0,0,0.18);
            padding: 16px;
        }
        #sak-promo-head { display:flex; align-items:flex-start; justify-content:space-between; gap: 12px; }
        #sak-promo-title { font-size: 16px; font-weight: 700; color:#333; margin:0; }
        #sak-promo-close { border: 0; background: transparent; color:#999; cursor:pointer; font-size: 20px; line-height: 1; padding: 4px 6px; }
        #sak-promo-close:hover { color:#555; }
        #sak-promo-body { margin-top: 10px; }
        #sak-promo-msg { font-size: 13px; line-height: 1.6; color:#666; white-space: pre-wrap; }
        #sak-promo-urlrow { margin-top: 10px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
        #sak-promo-url { font-size: 12px; color:#0f766e; font-weight: 600; word-break: break-all; }
        #sak-promo-actions { margin-top: 14px; display:flex; gap:10px; justify-content:flex-end; flex-wrap:wrap; }
        .sak-promo-btn {
            height: 36px; padding: 0 12px; border-radius: 999px;
            border: 1.5px solid #ffe4e6; background: transparent;
            color: #ff9a9e; cursor:pointer; font-size: 12px; font-weight: 600;
            transition: all 0.2s ease;
        }
        .sak-promo-btn:hover { box-shadow: 0 5px 15px rgba(0,0,0,0.08); transform: translateY(-1px); }
        .sak-promo-btn:active { transform: scale(0.98); }
        .sak-promo-btn.primary { background: linear-gradient(135deg, #ff9a9e, #fecfef); color: #fff; border: none; }
    `);

    // 水滴反馈函数
    function createRipple(event) {
        const btn = event.currentTarget;
        const circle = document.createElement("span");
        const diameter = Math.max(btn.clientWidth, btn.clientHeight);
        const radius = diameter / 2;
        const rect = btn.getBoundingClientRect();
        circle.style.width = circle.style.height = `${diameter}px`;
        circle.style.left = `${event.clientX - rect.left - radius}px`;
        circle.style.top = `${event.clientY - rect.top - radius}px`;
        circle.classList.add("ripple");
        const oldRipple = btn.getElementsByClassName("ripple")[0];
        if (oldRipple) oldRipple.remove();
        btn.appendChild(circle);
    }

    function addLog(msg) {
        const logArea = document.getElementById('log-area');
        const line = document.createElement('div');
        line.innerText = `> ${msg}`;
        logArea.appendChild(line);
        logArea.scrollTop = logArea.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = String(text || '');
        return div.innerHTML;
    }

    function sakResolveUrl(path) {
        const base = String(getSakSiteUrl() || '').trim().replace(/\/+$/g, '') || DEFAULT_SAK_SITE_URL;
        const p = String(path || '').trim();
        if (!p) return base;
        if (/^https?:\/\//i.test(p)) return p;
        return p.startsWith('/') ? (base + p) : (base + '/' + p);
    }

    function buildSakPromoMessage(exportType, fileName) {
        const f = fileName ? `（${fileName}）` : '';
        if (exportType === 'help') {
            return `全流程（学习通 → ${SAK_SITE_NAME}）：\n1) 点击「解析本页题目」。\n2) 推荐导出 JSON（*_题库导入.json）。\n3) 打开 ${SAK_SITE_NAME} → 个人题库 → 新建题库。\n4) 进入题库 → 题目管理 → 导入 JSON。\n5) 抽查 3–5 题；异常题在题目编辑里修正。\n6) 回到题库详情开始刷题（错题/收藏会自动沉淀）。`;
        }
        if (exportType === 'json') {
            return `已导出 JSON${f}。\n下一步：打开 ${SAK_SITE_NAME} → 个人题库 → 进入题库 → 题目管理 → 导入 JSON。`;
        }
        if (exportType === 'docx') {
            return `已导出 Word${f}。\n提示：Word 更适合编辑/复习；如需导入刷题，建议再导出 JSON。`;
        }
        if (exportType === 'pdf') {
            return `已导出 PDF${f}。\n提示：PDF 更适合打印/复习；如需导入刷题，建议再导出 JSON。`;
        }
        if (exportType === 'xlsx') {
            return `已导出 Excel${f}。\n你也可以在 ${SAK_SITE_NAME} 的题目管理里选择 Excel 导入（模板）。`;
        }
        if (exportType === 'copy-md') {
            return `已复制 Markdown。\n如需导入刷题，建议导出 JSON 再导入 ${SAK_SITE_NAME}。`;
        }
        return `导出完成。\n下一步：打开 ${SAK_SITE_NAME} 导入并开始刷题。`;
    }

    let sakPromoOverlay = null;
    let sakPromoMsgEl = null;
    let sakPromoUrlEl = null;
    let sakPromoTitleEl = null;

    function ensureSakPromoModal() {
        if (sakPromoOverlay) return;
        sakPromoOverlay = document.createElement('div');
        sakPromoOverlay.id = 'sak-promo-overlay';
        sakPromoOverlay.innerHTML = `
          <div id="sak-promo-card" role="dialog" aria-modal="true" aria-label="导出后提示">
            <div id="sak-promo-head">
              <h3 id="sak-promo-title">导出完成</h3>
              <button id="sak-promo-close" type="button" aria-label="关闭">✕</button>
            </div>
            <div id="sak-promo-body">
              <div id="sak-promo-msg"></div>
              <div id="sak-promo-urlrow">
                <span id="sak-promo-url"></span>
              </div>
            </div>
            <div id="sak-promo-actions">
              <button class="sak-promo-btn" type="button" id="sak-promo-setting">设置站点</button>
              <button class="sak-promo-btn" type="button" id="sak-promo-copy">复制地址</button>
              <button class="sak-promo-btn primary" type="button" id="sak-promo-open">打开 SAK</button>
            </div>
          </div>
        `;
        document.body.appendChild(sakPromoOverlay);

        sakPromoTitleEl = document.getElementById('sak-promo-title');
        sakPromoMsgEl = document.getElementById('sak-promo-msg');
        sakPromoUrlEl = document.getElementById('sak-promo-url');

        const closeBtn = document.getElementById('sak-promo-close');
        const openBtn = document.getElementById('sak-promo-open');
        const copyBtn = document.getElementById('sak-promo-copy');
        const settingBtn = document.getElementById('sak-promo-setting');

        const hide = () => sakPromoOverlay && sakPromoOverlay.classList.remove('show');
        if (closeBtn) closeBtn.onclick = hide;
        if (sakPromoOverlay) sakPromoOverlay.addEventListener('click', (e) => { if (e.target === sakPromoOverlay) hide(); });

        if (openBtn) openBtn.onclick = () => {
            window.open(sakResolveUrl('/user/banks'), '_blank');
            hide();
        };

        if (copyBtn) copyBtn.onclick = () => {
            GM_setClipboard(getSakSiteUrl());
            addLog('已复制题库网站地址');
        };

        if (settingBtn) settingBtn.onclick = () => {
            const cur = getSakSiteUrl();
            const next = window.prompt('请输入题库网站地址（例如：http://localhost:5000 或 https://your-domain.com）', cur);
            if (!next) return;
            const v = String(next || '').trim().replace(/\/+$/g, '');
            if (!/^https?:\/\//i.test(v)) {
                window.alert('地址需以 http:// 或 https:// 开头');
                return;
            }
            try {
                localStorage.setItem(SAK_SITE_URL_KEY, v);
            } catch (e) {}
            if (sakPromoUrlEl) sakPromoUrlEl.textContent = v;
            addLog('题库网站地址已更新');
        };
    }

    function showSakPromoModal(exportType, fileName) {
        ensureSakPromoModal();
        const url = getSakSiteUrl();
        const msg = buildSakPromoMessage(exportType, fileName);
        if (sakPromoTitleEl) sakPromoTitleEl.textContent = exportType === 'help' ? '全流程指南' : '导出完成';
        if (sakPromoMsgEl) sakPromoMsgEl.textContent = msg;
        if (sakPromoUrlEl) sakPromoUrlEl.textContent = url;
        if (sakPromoOverlay) sakPromoOverlay.classList.add('show');
    }

    function getExportFileName() {
        const candidates = [
            document.querySelector('.mark_title')?.innerText,
            document.querySelector('.course-name')?.innerText,
            document.querySelector('.courseName')?.innerText,
            document.querySelector('.coursename')?.innerText,
            document.querySelector('h1')?.innerText,
            document.title
        ];
        const raw = candidates.map((x) => String(x || '').trim()).find(Boolean) || '作业导出';
        return raw.replace(/\s*[-_]\s*学习通.*$/g, '').replace(/[\\/:\*\?\"<>\|]/g, '_') || '作业导出';
    }

    function htmlToPlainText(value) {
        if (value === null || value === undefined) return '';
        if (Array.isArray(value)) {
            return value.map((x) => htmlToPlainText(x)).filter(Boolean).join('\n');
        }
        if (typeof value === 'object') {
            const nested = getFirstValueByKeys(value, [
                'text', 'content', 'html', 'title', 'name', 'value', 'optionContent',
                'answerContent', 'questionContent', 'questionTitle'
            ]);
            return nested === undefined ? '' : htmlToPlainText(nested);
        }

        const source = String(value || '').replace(/\\n/g, '\n');
        if (!source) return '';
        const textarea = document.createElement('textarea');
        textarea.innerHTML = source;
        const decoded = textarea.value;
        if (!/[<&][a-zA-Z/#?!]/.test(decoded)) {
            return maybeCompactCjkSpacing(decoded).replace(/[ \t]+\n/g, '\n').trim();
        }

        const box = document.createElement('div');
        box.innerHTML = decoded
            .replace(/<br\s*\/?>/gi, '\n')
            .replace(/<\/(p|div|li|tr|h[1-6])>/gi, '\n');
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

    function getStemCandidate(obj) {
        return htmlToPlainText(getFirstValueByKeys(obj, [
            'questionContent', 'questionTitle', 'questionName', 'quesName',
            'questionStem', 'stem', 'topic', 'subject', 'title', 'name',
            'content', 'description', 'question', 'questionText'
        ])).replace(/^\s*\d+\s*[\.、]\s*/g, '');
    }

    function getAnswerCandidate(obj) {
        return getFirstValueByKeys(obj, [
            'rightAnswer', 'rightAnswers', 'correctAnswer', 'correctAnswers',
            'standardAnswer', 'standardAnswers', 'referenceAnswer', 'referenceAnswers',
            'answer', 'answers', 'answerContent', 'rightAnswerContent',
            'stuAnswer', 'studentAnswer', 'myAnswer', 'userAnswer', 'resultAnswer'
        ]);
    }

    function getAnalysisCandidate(obj) {
        return htmlToPlainText(getFirstValueByKeys(obj, [
            'analysis', '解析', 'explanation', 'explain', 'answerAnalysis',
            'analysisContent', 'remark', 'remarks'
        ]));
    }

    function extractOptionItems(obj) {
        const optionArray = getFirstValueByKeys(obj, [
            'optionList', 'options', 'optionDtos', 'optionArray', 'choiceList',
            'choices', 'questionOptions', 'answerOptions', 'items'
        ]);
        const fromArray = Array.isArray(optionArray) ? optionArray.map((item, idx) => {
            const label = String(getFirstValueByKeys(item, ['option', 'optionNo', 'optionName', 'label', 'key', 'prefix', 'sort']) || '').trim();
            const id = String(getFirstValueByKeys(item, ['id', 'optionId', 'answerId', 'itemId', 'oid', 'value']) || '').trim();
            const text = htmlToPlainText(typeof item === 'object' ? getFirstValueByKeys(item, [
                'optionContent', 'content', 'text', 'name', 'title', 'answer', 'value'
            ]) : item);
            return {
                label: label || String.fromCharCode(65 + idx),
                id,
                text: stripOptionPrefix(text)
            };
        }).filter((item) => item.text) : [];

        if (fromArray.length) return fromArray;

        const directOptions = [];
        Object.keys(obj || {}).forEach((key) => {
            const m = String(key).match(/^option[_-]?([A-H]|\d{1,2})$/i);
            if (!m) return;
            const rawLabel = m[1];
            const idx = /^\d+$/.test(rawLabel) ? Math.max(0, Number(rawLabel) - 1) : rawLabel.toUpperCase().charCodeAt(0) - 65;
            const text = stripOptionPrefix(htmlToPlainText(obj[key]));
            if (text) {
                directOptions.push({
                    label: String.fromCharCode(65 + idx),
                    id: '',
                    text
                });
            }
        });

        return directOptions.sort((a, b) => String(a.label).localeCompare(String(b.label)));
    }

    function stringifyAnswerValue(value) {
        if (value === null || value === undefined) return '';
        if (Array.isArray(value)) {
            return value.map((item) => stringifyAnswerValue(item)).filter(Boolean).join('\n');
        }
        if (typeof value === 'object') {
            const nested = getFirstValueByKeys(value, [
                'answer', 'rightAnswer', 'correctAnswer', 'content', 'text',
                'name', 'value', 'option', 'optionName', 'optionContent'
            ]);
            return nested === undefined ? '' : stringifyAnswerValue(nested);
        }
        return htmlToPlainText(value);
    }

    function mapAnswerToLetters(rawAnswer, optionItems) {
        const raw = stringifyAnswerValue(rawAnswer).trim();
        if (!raw || !Array.isArray(optionItems) || !optionItems.length) return raw;

        const tokens = raw.split(/[\s,，;；|、]+/).map((x) => x.trim()).filter(Boolean);
        const mapped = tokens.map((token) => {
            const plainToken = stripOptionPrefix(token).trim();
            const matched = optionItems.find((opt) => {
                const label = String(opt.label || '').trim().toUpperCase();
                const id = String(opt.id || '').trim();
                const text = String(opt.text || '').trim();
                return token.toUpperCase() === label || (!!id && token === id) || (!!text && plainToken === text);
            });
            return matched ? String(matched.label || '').trim().toUpperCase() : token;
        });

        const allMappedToLetters = mapped.length && mapped.every((token) => /^[A-Z]$/.test(token));
        return allMappedToLetters ? mapped.join('') : raw;
    }

    function guessChaoxingQType(rawType, stem, options, rawAnswer) {
        const typeText = String(rawType || '').replace(/\s+/g, '');
        const direct = guessBankQType(typeText, stem, options, rawAnswer);
        if (!/^\d+$/.test(typeText)) return direct;

        if (typeText === '0') return '选择题';
        if (typeText === '1') return '多选题';
        if (typeText === '4' || typeText === '5') return '简答题';

        const ans = String(rawAnswer || '').replace(/\s+/g, '');
        if ((typeText === '2' || typeText === '3') && /^(正确|错误|对|错|√|×|TRUE|FALSE|T|F)$/i.test(ans)) {
            return '判断题';
        }
        if ((typeText === '2' || typeText === '3') && /__|\(\s*\)|（\s*）|_{2,}/.test(String(stem || ''))) {
            return '填空题';
        }
        if (typeText === '2') return options.length ? direct : '填空题';
        if (typeText === '3') return options.length ? direct : '判断题';
        return direct;
    }

    function looksLikeQuestionObject(obj) {
        if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return false;
        const stem = getStemCandidate(obj);
        if (stem.length < 2) return false;
        const optionItems = extractOptionItems(obj);
        const rawType = getFirstValueByKeys(obj, ['typeName', 'questionTypeName', 'questionType', 'qType', 'type']);
        const rawAnswer = getAnswerCandidate(obj);
        const keys = Object.keys(obj).map((key) => String(key).toLowerCase());
        const hasStemKey = keys.some((key) => [
            'questioncontent', 'questiontitle', 'questionname', 'quesname',
            'questionstem', 'stem', 'topic', 'question', 'questiontext'
        ].includes(key));
        return hasStemKey || optionItems.length > 0 || rawAnswer !== undefined || rawType !== undefined;
    }

    function collectQuestionObjects(root) {
        const found = [];
        const seen = new WeakSet();
        const walk = (node, depth) => {
            if (!node || depth > 12) return;
            if (typeof node !== 'object') return;
            if (seen.has(node)) return;
            seen.add(node);

            if (Array.isArray(node)) {
                node.forEach((item) => walk(item, depth + 1));
                return;
            }

            if (looksLikeQuestionObject(node)) found.push(node);
            Object.keys(node).forEach((key) => walk(node[key], depth + 1));
        };
        walk(root, 0);
        return found;
    }

    function normalizeChaoxingQuestion(obj, index, keepAns) {
        const stem = normalizeStemForBank(getStemCandidate(obj));
        if (!stem) return null;

        const rawType = htmlToPlainText(getFirstValueByKeys(obj, [
            'typeName', 'questionTypeName', 'questionTypeText', 'questionType',
            'qType', 'type', 'quesType'
        ]));
        const optionItems = extractOptionItems(obj);
        const optionTexts = optionItems.map((item) => item.text).filter(Boolean);
        const rawAnsValue = getAnswerCandidate(obj);
        const rawAns = keepAns ? mapAnswerToLetters(rawAnsValue, optionItems) : '';
        const qType = guessChaoxingQType(rawType, stem, optionTexts, rawAns);
        const storageAnswer = keepAns ? normalizeAnswerForBankStorage(qType, rawAns, optionTexts, stem) : '';
        const storageOptions = (qType === '选择题' || qType === '多选题') ? optionTexts : [];

        return {
            id: index + 1,
            raw_type: rawType || '',
            q_type: qType,
            stem,
            options: storageOptions,
            answer: storageAnswer,
            analysis: getAnalysisCandidate(obj)
        };
    }

    function dedupeQuestions(questions) {
        const seen = new Set();
        return (questions || []).filter((q) => {
            const key = [
                String(q.q_type || ''),
                String(q.stem || '').replace(/\s+/g, ''),
                (q.options || []).join('|').replace(/\s+/g, ''),
                String(q.answer || '').replace(/\s+/g, '')
            ].join('::');
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        }).map((q, idx) => ({ ...q, id: idx + 1 }));
    }

    function collectActiveIdsFromText(text) {
        const ids = new Set();
        const rawSource = String(text || '');
        const sources = [rawSource];
        try {
            const decoded = decodeURIComponent(rawSource);
            if (decoded && decoded !== rawSource) sources.push(decoded);
        } catch (e) {}
        try {
            const textarea = document.createElement('textarea');
            textarea.innerHTML = rawSource;
            if (textarea.value && textarea.value !== rawSource) sources.push(textarea.value);
        } catch (e) {}
        const patterns = [
            /(?:activeId|activeid)\s*[=:]\s*["']?(\d{6,})/g,
            /(?:activeId|activeid)=["']?(\d{6,})/g,
            /quizStudentQuestion\?[^"'<>]*?(?:activeId|activeid)=(\d{6,})/g
        ];
        sources.forEach((source) => {
            patterns.forEach((re) => {
                re.lastIndex = 0;
                let m;
                while ((m = re.exec(source)) !== null) ids.add(m[1]);
            });
        });
        return Array.from(ids);
    }

    function collectActiveIdsFromJson(root) {
        const ids = new Set();
        const seen = new WeakSet();
        const walk = (node, depth) => {
            if (!node || depth > 10) return;
            if (typeof node === 'string') {
                collectActiveIdsFromText(node).forEach((id) => ids.add(id));
                return;
            }
            if (typeof node !== 'object') return;
            if (seen.has(node)) return;
            seen.add(node);

            if (Array.isArray(node)) {
                node.forEach((item) => walk(item, depth + 1));
                return;
            }

            Object.keys(node).forEach((key) => {
                const value = node[key];
                const lower = String(key).toLowerCase();
                if (lower === 'activeid' && /^\d{6,}$/.test(String(value || ''))) {
                    ids.add(String(value));
                }
                if (lower === 'id' && (node.activeType !== undefined || node.activeName !== undefined) && /^\d{6,}$/.test(String(value || ''))) {
                    ids.add(String(value));
                }
                walk(value, depth + 1);
            });
        };
        walk(root, 0);
        return Array.from(ids);
    }

    function collectActiveIdsFromPage() {
        const ids = new Set();
        collectActiveIdsFromText(window.location.href).forEach((id) => ids.add(id));
        collectActiveIdsFromText(document.documentElement ? document.documentElement.innerHTML : '').forEach((id) => ids.add(id));

        document.querySelectorAll('a[href], iframe[src], frame[src], [onclick], [data], [data-activeid], [data-active-id]').forEach((el) => {
            ['href', 'src', 'onclick', 'data', 'data-activeid', 'data-active-id'].forEach((attr) => {
                collectActiveIdsFromText(el.getAttribute(attr) || '').forEach((id) => ids.add(id));
            });
        });

        return Array.from(ids);
    }

    function requestJson(url) {
        return new Promise((resolve, reject) => {
            const onText = (text, status) => {
                if (status && (status < 200 || status >= 300)) {
                    reject(new Error(`HTTP ${status}`));
                    return;
                }
                try {
                    resolve(JSON.parse(text));
                } catch (err) {
                    reject(new Error('接口返回不是 JSON'));
                }
            };

            if (typeof GM_xmlhttpRequest === 'function') {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url,
                    anonymous: false,
                    withCredentials: true,
                    headers: {
                        Accept: 'application/json, text/javascript, */*; q=0.01',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    onload: (res) => onText(res.responseText || '', res.status),
                    onerror: () => reject(new Error('网络请求失败')),
                    ontimeout: () => reject(new Error('网络请求超时'))
                });
                return;
            }

            fetch(url, {
                credentials: 'include',
                headers: {
                    Accept: 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then((res) => res.text().then((text) => onText(text, res.status)))
                .catch(() => reject(new Error('网络请求失败')));
        });
    }

    function buildActivityListUrls() {
        const params = new URLSearchParams(window.location.search);
        const courseId = params.get('courseid') || params.get('courseId');
        const classId = params.get('clazzid') || params.get('classId') || params.get('clazzId');
        const fid = params.get('fid') || '';
        if (!courseId || !classId) return [];
        const baseParams = new URLSearchParams({
            courseId,
            classId,
            showNotStartedActive: '1'
        });
        if (fid) baseParams.set('fid', fid);
        return [
            `https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist?${baseParams.toString()}`,
            `https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist?${baseParams.toString()}&page=1&pageSize=200`
        ];
    }

    async function collectActiveIdsFromRemoteList(addLog) {
        const ids = new Set();
        const urls = buildActivityListUrls();
        for (const url of urls) {
            try {
                const json = await requestJson(url);
                collectActiveIdsFromJson(json).forEach((id) => ids.add(id));
            } catch (err) {
                addLog(`活动列表接口跳过：${err.message || err}`);
            }
        }
        return Array.from(ids);
    }

    async function fetchQuestionsByActiveId(activeId, keepAns) {
        const url = `https://mobilelearn.chaoxing.com/v2/apis/studentQuestion/getAnswerResult?activeId=${encodeURIComponent(activeId)}`;
        const json = await requestJson(url);
        const objects = collectQuestionObjects(json);
        return objects
            .map((obj, index) => normalizeChaoxingQuestion(obj, index, keepAns))
            .filter((q) => q && q.stem);
    }

    function parseDomQuestionItems(items, keepAns) {
        return Array.from(items).map((el, i) => {
            const rawType = (el.querySelector('.colorShallow')?.innerText || '').replace(/[()（）]/g, '').trim();
            let stem = (el.querySelector('.qtContent')?.innerText || '');
            if (!stem) stem = el.querySelector('.mark_name')?.innerText.replace(/^\d+\.\s*/, '') || '';
            stem = normalizeStemForBank(stem);

            const options = [];
            el.querySelectorAll('.mark_letter li').forEach(li => options.push(stripOptionPrefix(li.innerText)));

            let rawAns = '';
            if (keepAns) {
                rawAns = Array.from(el.querySelectorAll('.rightAnswerContent'))
                    .map((n) => String(n && n.innerText ? n.innerText : '').trim())
                    .filter(Boolean)
                    .join('\n');
                if (!rawAns) {
                    rawAns = Array.from(el.querySelectorAll('.stuAnswerContent'))
                        .map((n) => String(n && n.innerText ? n.innerText : '').trim())
                        .filter(Boolean)
                        .join('\n');
                }
                if (!rawAns) rawAns = (el.querySelector('.colorGreen')?.innerText || '');
                rawAns = normalizeNewlines(rawAns)
                    .replace(/^(正确答案|参考答案|答案|我的答案)[:：\s]*/g, '')
                    .replace(/\s+$/g, '');
            }

            const qType = guessBankQType(rawType, stem, options, rawAns);
            const storageAnswer = keepAns ? normalizeAnswerForBankStorage(qType, rawAns, options, stem) : '';
            const storageOptions = (qType === '选择题' || qType === '多选题') ? options.filter(Boolean) : [];

            return {
                id: i + 1,
                raw_type: rawType || '',
                q_type: qType,
                stem,
                options: storageOptions,
                answer: storageAnswer,
                analysis: ''
            };
        }).filter((q) => q.stem);
    }

    async function parseChaoxingCommonPage(keepAns, addLog) {
        const localIds = collectActiveIdsFromPage();
        const remoteIds = await collectActiveIdsFromRemoteList(addLog);
        const activeIds = Array.from(new Set([...localIds, ...remoteIds])).slice(0, 80);

        if (!activeIds.length) {
            throw new Error('未在当前课程页找到 activeId，请先展开/进入具体作业或题目活动后重试');
        }

        addLog(`找到 ${activeIds.length} 个活动，正在请求题目结果...`);
        let questions = [];
        for (const activeId of activeIds) {
            try {
                const one = await fetchQuestionsByActiveId(activeId, keepAns);
                if (one.length) addLog(`activeId ${activeId}：${one.length} 题`);
                questions = questions.concat(one);
            } catch (err) {
                addLog(`activeId ${activeId} 跳过：${err.message || err}`);
            }
        }

        return dedupeQuestions(questions);
    }

    function finishParseSuccess(pBtn, eBtns) {
        addLog(`提取完毕！共 ${parsedData.length} 道题目`);
        const over6 = (parsedData || []).filter((q) => (q.q_type === '选择题' || q.q_type === '多选题') && Array.isArray(q.options) && q.options.length > 6);
        if (over6.length) addLog(`提示：检测到 ${over6.length} 题选项超过 6 个（Word 导入仅识别 A-F），建议使用 JSON 导入`);
        pBtn.disabled = false;
        pBtn.innerText = '✅ 解析成功';
        pBtn.classList.remove('highlight-red');
        pBtn.classList.add('success-green');
        eBtns.forEach(b => b.disabled = false);
    }

    // 核心解析逻辑
    async function parsePage(e) {
        createRipple(e);
        parsedData = [];
        const pBtn = document.getElementById('p-btn');
        const eBtns = document.querySelectorAll('.e-btn');

        addLog("正在提取页面题目...");
        pBtn.innerText = "正在解析...";
        pBtn.disabled = true;

        const keepAns = document.getElementById('c-ans').checked;
        const items = document.querySelectorAll('.questionLi');

        try {
            if (items.length > 0) {
                parsedData = parseDomQuestionItems(items, keepAns);
            } else {
                addLog('未找到作业详情 DOM，尝试通过通用课程页接口抓取...');
                parsedData = await parseChaoxingCommonPage(keepAns, addLog);
            }

            if (!parsedData.length) throw new Error('未解析到题目');
            finishParseSuccess(pBtn, eBtns);
        } catch (err) {
            addLog(`解析失败：${err.message || err}`);
            pBtn.disabled = false;
            pBtn.innerText = "1. 解析本页题目";
            pBtn.classList.remove('success-green');
            pBtn.classList.add('highlight-red');
            eBtns.forEach(b => b.disabled = true);
        }
    }

    // 构建 UI
    const trigger = document.createElement('div');
    trigger.id = 'menu-trigger';
    trigger.innerHTML = '<span class="icon">🐱</span>';
    document.body.appendChild(trigger);

    const panel = document.createElement('div');
    panel.id = 'export-panel';
    panel.innerHTML = `
        <h3 style="text-align:center;margin:0 0 10px 0;color:#666;font-size:15px">学习通作业导出助手</h3>
        <div id="log-area">等待指令...</div>
        <div style="text-align:center;margin-bottom:12px;font-size:12px;color:#888">
            <input type="checkbox" id="c-ans" checked> <label for="c-ans" style="cursor:pointer">包含答案</label>
        </div>
        <div class="btn-stack">
            <button id="p-btn" class="highlight-red">1. 解析本页题目</button>
            <button class="e-btn word-btn" data-type="docx" disabled>导出 Word (.docx)</button>
            <button class="e-btn json-btn" data-type="json" disabled>导出 JSON (.json)</button>
            <button class="e-btn xlsx-btn" data-type="xlsx" disabled>导出 Excel (.xlsx)</button>
            <button class="e-btn pdf-btn" data-type="pdf" disabled>导出 PDF (.pdf)</button>
            <button class="e-btn md-btn" data-type="copy-md" disabled>复制 Markdown</button>
            <button id="sak-guide-btn" class="sak-guide-btn" type="button">全流程：导出 → 导入 → 刷题指南</button>
            <button id="goto-top" style="border:none;background:none;color:#ccc;font-size:11px;margin-top:5px;cursor:pointer">回到顶部 ↑</button>
        </div>
        <div id="pdf-render-area"></div>
    `;
    document.body.appendChild(panel);

    // 交互事件
    trigger.onclick = () => {
        const isShow = panel.classList.contains('panel-show');
        panel.classList.toggle('panel-show');
        trigger.querySelector('.icon').innerText = isShow ? "🐱" : "✖";
    };

    document.getElementById('p-btn').onclick = parsePage;
    document.getElementById('goto-top').onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    const sakGuideBtn = document.getElementById('sak-guide-btn');
    if (sakGuideBtn) {
        sakGuideBtn.onclick = (e) => {
            createRipple(e);
            showSakPromoModal('help', '');
        };
    }

    document.getElementById('c-ans').onchange = () => {
        document.querySelectorAll('.e-btn').forEach(b => b.disabled = true);
        const pBtn = document.getElementById('p-btn');
        pBtn.innerText = "选项改变，请重新解析";
        pBtn.classList.remove('success-green');
        pBtn.classList.add('highlight-red');
    };

    panel.onclick = async (e) => {
        const type = e.target.getAttribute('data-type');
        if (!type || e.target.disabled) return;
        createRipple(e);

        const fName = getExportFileName();
        const hasAnswer = parsedData.some((q) => String(q && q.answer ? q.answer : '').trim());
        if (!hasAnswer) addLog("提示：当前未包含答案，导入题库可能会提示“缺少答案”");

        if (type === 'copy-md') {
            let mdText = `# ${fName}\n\n`;
            parsedData.forEach(q => {
                mdText += `### ${q.id}. [${q.q_type}] ${q.stem}\n`;
                (q.options || []).forEach(opt => mdText += `- ${opt}\n`);
                let mdAns = String(q.answer || '').trim();
                if (mdAns && String(q.q_type || '').trim() === '填空题') mdAns = formatFillAnswerForWordFromStorage(mdAns);
                if (mdAns) mdText += `\n> **正确答案：${mdAns}**\n\n---\n`;
                else mdText += `\n---\n`;
            });
            GM_setClipboard(mdText);
            addLog("Markdown 复制成功！");
            showSakPromoModal('copy-md', '');
            return;
        }

        addLog(`正在生成 ${type.toUpperCase()}...`);

        if (type === 'docx') {
            const { Document, Packer, Paragraph, TextRun, AlignmentType } = window.docx;
            const children = [
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    spacing: { after: 200 },
                    children: [new TextRun({ text: `标题：${fName}`, bold: true, font: "SimHei", size: 28 })]
                }),
                new Paragraph({ children: [new TextRun({ text: '（本文件已按题库 Word 导入解析规则排版）', font: "SimSun", size: 18, color: "666666" })] }),
                new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: getSakPromoLine(), font: "SimSun", size: 18, color: "0F766E" })] }),
                new Paragraph('')
            ];

            const labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            parsedData.forEach(q => {
                const qt = String(q.q_type || '').trim();
                const stem = normalizeNewlines(String(q.stem || '')).replace(/\s+$/g, '');
                const stemLines = stem.split('\n');
                const stemRuns = [];
                stemLines.forEach((line, idx) => {
                    const text = (idx === 0) ? `${q.id}. ${line}` : line;
                    const run = { text, font: "SimSun", size: 22 };
                    if (idx > 0) run.break = 1;
                    stemRuns.push(new TextRun(run));
                });
                if (!stemRuns.length) stemRuns.push(new TextRun({ text: `${q.id}. `, font: "SimSun", size: 22 }));

                children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 80, line: 240 }, children: stemRuns }));

                if (qt === '选择题' || qt === '多选题') {
                    (q.options || []).slice(0, 6).forEach((opt, idx) => {
                        const label = labels[idx] || String.fromCharCode(65 + idx);
                        children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { line: 240 }, children: [new TextRun({ text: `${label}. ${opt}`, font: "SimSun", size: 20 })] }));
                    });
                }

                let wordAnswer = String(q.answer || '');
                if (qt === '判断题') {
                    if (wordAnswer === '正确') wordAnswer = '对';
                    else if (wordAnswer === '错误') wordAnswer = '错';
                } else if (qt === '填空题') {
                    wordAnswer = formatFillAnswerForWordFromStorage(wordAnswer);
                }

                const answerText = normalizeNewlines(String(wordAnswer || '')).replace(/\s+$/g, '');
                const answerLines = answerText.split('\n');
                const answerRuns = [];
                answerLines.forEach((line, idx) => {
                    const text = (idx === 0) ? `答案：${line}` : line;
                    const run = { text, font: "SimSun", size: 20 };
                    if (idx > 0) run.break = 1;
                    answerRuns.push(new TextRun(run));
                });
                children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { line: 240 }, children: answerRuns }));

                const analysisText = normalizeNewlines(String(q.analysis || '')).replace(/\s+$/g, '');
                if (analysisText) {
                    const analysisLines = analysisText.split('\n');
                    const analysisRuns = [];
                    analysisLines.forEach((line, idx) => {
                        const text = (idx === 0) ? `解析：${line}` : line;
                        const run = { text, font: "SimSun", size: 20 };
                        if (idx > 0) run.break = 1;
                        analysisRuns.push(new TextRun(run));
                    });
                    children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { line: 240 }, children: analysisRuns }));
                }
                children.push(new Paragraph(''));
            });

            saveAs(await Packer.toBlob(new Document({ sections: [{ children }] })), `${fName}_题库导入.docx`);
            addLog("Word 下载已启动");
            showSakPromoModal('docx', `${fName}_题库导入.docx`);
        } else if (type === 'json') {
            const payload = buildPortableExportJson(parsedData, 3);
            const jsonStr = JSON.stringify(payload, null, 2);
            saveAs(new Blob([jsonStr], { type: 'application/json;charset=utf-8' }), `${fName}_题库导入.json`);
            addLog("JSON 下载已启动");
            showSakPromoModal('json', `${fName}_题库导入.json`);
        } else if (type === 'xlsx') {
            // Excel 导出统一为题库模板格式（instance/question_import_template.xlsx）
            const seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            const normalizeExcelQType = (qt) => {
                const t = String(qt || '').trim();
                return t === ('问' + '答题') ? '简答题' : t;
            };

            // 统计最大选项数 / 最大空数（与模板一致：至少 option_A..option_E、blank_1..blank_2）
            let maxOptions = 0;
            let maxBlanks = 0;
            (parsedData || []).forEach((d) => {
                const qt = normalizeExcelQType(d && d.q_type ? d.q_type : '');
                if ((qt === '选择题' || qt === '多选题') && Array.isArray(d.options)) {
                    maxOptions = Math.max(maxOptions, d.options.length);
                }
                if (qt === '填空题') {
                    const ans = String(d && d.answer ? d.answer : '').trim();
                    if (ans) {
                        const blanks = ans.split(';;').map((x) => String(x || '').trim()).filter(Boolean);
                        maxBlanks = Math.max(maxBlanks, blanks.length);
                    }
                }
            });
            maxOptions = Math.max(5, maxOptions);
            maxBlanks = Math.max(2, maxBlanks);

            const optionCols = [];
            for (let i = 0; i < maxOptions; i++) {
                const col = (i < seed.length) ? `option_${seed[i]}` : `option_${i + 1}`;
                optionCols.push(col);
            }
            const blankCols = [];
            for (let i = 0; i < maxBlanks; i++) blankCols.push(`blank_${i + 1}`);

            const headers = ['subject', 'q_type', 'content', ...optionCols, 'answer', ...blankCols, 'explanation'];

            const rows = (parsedData || []).map((d) => {
                const qt = normalizeExcelQType(d && d.q_type ? d.q_type : '');
                const row = {
                    subject: fName,
                    q_type: qt,
                    content: d && d.stem ? String(d.stem) : '',
                    answer: '',
                    explanation: d && d.analysis ? String(d.analysis) : '',
                };

                // 选择题/多选题：填充 option_A...，answer 写字母（如 C / ABC）
                if (qt === '选择题' || qt === '多选题') {
                    const opts = Array.isArray(d.options) ? d.options : [];
                    for (let i = 0; i < optionCols.length; i++) {
                        row[optionCols[i]] = opts[i] ? String(opts[i]) : '';
                    }
                    row.answer = String(d && d.answer ? d.answer : '').trim();
                }

                // 判断题/简答题：answer 写文本；填空题：answer 留空，使用 blank_*
                if (qt === '判断题' || qt === '简答题') {
                    row.answer = String(d && d.answer ? d.answer : '').trim();
                } else if (qt === '填空题') {
                    const ans = String(d && d.answer ? d.answer : '').trim();
                    const blanks = ans ? ans.split(';;').map((x) => String(x || '').trim()) : [];
                    for (let i = 0; i < blankCols.length; i++) {
                        row[blankCols[i]] = blanks[i] ? blanks[i] : '';
                    }
                }
                return row;
            });

            const ws = XLSX.utils.json_to_sheet(rows, { header: headers, skipHeader: false });
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, "题目示例");

            // 附带“填写说明”sheet，方便用户理解模板（不影响导入）
            const helpAoa = [
                ['列名', '说明'],
                ['subject (科目)', '必填。题目的所属科目，如“计算机网络”。如果科目不存在，系统将自动创建。'],
                ['q_type (题型)', '必填。题型必须是“选择题”、“多选题”、“判断题”、“填空题”、“简答题”之一。'],
                ['content (题干)', '必填。题目的具体内容。对于填空题，请使用两个下划线 "__" 表示一个填空位。'],
                ['option_A, option_B, ...', '仅对“选择题”和“多选题”有效。请将每个选项的文本分别填入对应的 option_A, option_B, option_C... 列中。无需填写 "A." 等前缀。'],
                ['answer (答案)', '对于“选择题”、“多选题”、“判断题”、“简答题”为必填。\\n- 选择题: 对应的正确选项字母，如 "C"。\\n- 多选题: 对应的所有正确选项字母，连续书写，如 "ABC"。\\n- 判断题: "正确" 或 "错误"。\\n- 简答题: 参考答案文本。\\n- 填空题: 此列留空。'],
                ['blank_1, blank_2, ...', '仅对“填空题”有效。请将每个空的答案分别填入对应的 blank_1, blank_2... 列中。如果一个空有多个可能答案，用一个分号 ";" 隔开。'],
                ['explanation (解析)', '选填。对题目的详细解释。'],
            ];
            const wsHelp = XLSX.utils.aoa_to_sheet(helpAoa);
            XLSX.utils.book_append_sheet(wb, wsHelp, "填写说明");

            XLSX.writeFile(wb, `${fName}_题库导入.xlsx`);
            addLog("Excel 下载已启动");
            showSakPromoModal('xlsx', `${fName}_题库导入.xlsx`);
        } else if (type === 'pdf') {
            const renderArea = document.getElementById('pdf-render-area');
            renderArea.innerHTML = '';

            const titleEl = document.createElement('div');
            titleEl.className = 'sak-pdf-title';
            titleEl.textContent = String(fName || '');
            renderArea.appendChild(titleEl);

            const promoEl = document.createElement('div');
            promoEl.className = 'sak-pdf-promo';
            promoEl.textContent = getSakPromoLine();
            renderArea.appendChild(promoEl);

            (parsedData || []).forEach((q) => {
                const qt = String(q && q.q_type ? q.q_type : '').trim();
                const itemEl = document.createElement('div');
                itemEl.className = 'sak-pdf-item';

                const stemText = normalizeNewlines(String(q && q.stem ? q.stem : '')).replace(/\s+$/g, '');
                const qTitleEl = document.createElement('div');
                qTitleEl.className = 'sak-pdf-qtitle';
                const qIdNum = Number(q && q.id ? q.id : 0) || 0;
                const qIdText = qIdNum ? `${qIdNum}. ` : '';
                qTitleEl.textContent = `${qIdText}（${qt}） ${stemText}`.trim();
                itemEl.appendChild(qTitleEl);

                const opts = Array.isArray(q && q.options ? q.options : null) ? q.options : [];
                if (opts.length) {
                    const optsEl = document.createElement('div');
                    optsEl.className = 'sak-pdf-options';
                    optsEl.textContent = opts.map((x) => String(x || '')).join('\n');
                    itemEl.appendChild(optsEl);
                }

                const ans = String(q && q.answer ? q.answer : '').trim();
                let displayAns = ans;
                if (qt === '填空题') displayAns = formatFillAnswerForWordFromStorage(ans);
                const ansEl = document.createElement('div');
                ansEl.className = 'sak-pdf-answer';
                ansEl.textContent = displayAns ? `答案：${displayAns}` : '答案：';
                itemEl.appendChild(ansEl);

                const analysisText = normalizeNewlines(String(q && q.analysis ? q.analysis : '')).replace(/\s+$/g, '');
                if (analysisText) {
                    const analysisEl = document.createElement('div');
                    analysisEl.className = 'sak-pdf-analysis';
                    analysisEl.textContent = `解析：${analysisText}`;
                    itemEl.appendChild(analysisEl);
                }

                renderArea.appendChild(itemEl);
            });

            if (document.fonts && document.fonts.ready) {
                try { await document.fonts.ready; } catch (e) {}
            }

            const canvas = await html2canvas(renderArea, { scale: 2, backgroundColor: '#ffffff' });
            const doc = new window.jspdf.jsPDF('p', 'mm', [210, (canvas.height * 210) / canvas.width]);
            doc.addImage(canvas.toDataURL('image/jpeg'), 'JPEG', 0, 0, 210, (canvas.height * 210) / canvas.width);
            doc.save(`${fName}.pdf`);
            addLog("PDF 下载已启动");
            showSakPromoModal('pdf', `${fName}.pdf`);
        }
    };
})();
