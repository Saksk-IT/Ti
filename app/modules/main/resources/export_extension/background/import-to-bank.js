const IMPORT_MESSAGE_TYPE = 'SAK_IMPORT_TO_BANK_REQUEST';

function normalizeBaseUrl(rawUrl) {
  const raw = String(rawUrl || '').trim();
  if (!raw) throw new Error('请先设置 Ti 题库网站地址');

  let url;
  try {
    url = new URL(raw);
  } catch (error) {
    throw new Error('题库网站地址格式不正确');
  }

  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('题库网站地址需以 http:// 或 https:// 开头');
  }

  url.hash = '';
  url.search = '';
  url.pathname = url.pathname.replace(/\/+$/g, '');
  return url;
}

function normalizeBankId(rawBankId) {
  const bankId = String(rawBankId || '').trim();
  if (!/^[1-9]\d*$/.test(bankId)) {
    throw new Error('个人题库 ID 需为正整数');
  }
  return bankId;
}

function buildImportUrl(siteUrl, bankId) {
  const base = normalizeBaseUrl(siteUrl);
  const id = normalizeBankId(bankId);
  base.pathname = `${base.pathname}/user/banks/api/${encodeURIComponent(id)}/questions/import/json`;
  return base.toString();
}

function normalizeQuestions(payload) {
  const questions = Array.isArray(payload?.questions) ? payload.questions : [];
  if (!questions.length) {
    throw new Error('没有可导入的题目');
  }
  return questions;
}

async function parseResponse(response) {
  const contentType = String(response.headers.get('content-type') || '').toLowerCase();
  if (contentType.includes('application/json')) {
    return response.json();
  }

  const text = await response.text();
  return {
    code: response.ok ? 0 : 1,
    message: text.slice(0, 300) || response.statusText || '导入请求失败',
  };
}

async function importQuestionsToBank(message) {
  const url = buildImportUrl(message?.siteUrl, message?.bankId);
  const questions = normalizeQuestions(message?.payload);

  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify({ questions }),
  });

  const body = await parseResponse(response);
  if (!response.ok || Number(body?.code || 0) !== 0) {
    const messageText = String(body?.message || response.statusText || '导入失败').trim();
    throw new Error(messageText || '导入失败');
  }

  return body;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== IMPORT_MESSAGE_TYPE) return false;

  importQuestionsToBank(message)
    .then((body) => {
      sendResponse({ ok: true, body });
    })
    .catch((error) => {
      sendResponse({
        ok: false,
        message: String(error?.message || error || '导入失败'),
      });
    });

  return true;
});
