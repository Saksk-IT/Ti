type LastPracticeSession = {
  subject?: any;
  mode?: any;
  type?: any;
  source?: any;
  shuffleQuestions?: any;
  shuffleOptions?: any;
  shuffle_questions?: any;
  shuffle_options?: any;
  [k: string]: any;
};

function toBool(v: any): boolean {
  if (v === true) return true;
  if (v === false) return false;
  const s = String(v ?? '').trim().toLowerCase();
  if (!s) return false;
  return s === '1' || s === 'true' || s === 'yes' || s === 'on';
}

function safeParseStorage(raw: any): any | null {
  if (!raw) return null;
  if (typeof raw === 'object') return raw;
  const s = String(raw || '').trim();
  if (!s) return null;
  if (s.startsWith('{') || s.startsWith('[')) {
    try {
      return JSON.parse(s);
    } catch (e) {
      return null;
    }
  }
  return null;
}

export function buildLastPracticeUrl(): string | null {
  const raw = wx.getStorageSync('last_practice_session');
  const js = safeParseStorage(raw) as LastPracticeSession | null;
  if (!js || typeof js !== 'object' || Array.isArray(js)) return null;

  const subject = String(js.subject || '').trim();
  if (!subject) return null;

  const mode = String(js.mode || 'quiz').trim() || 'quiz';
  const type = String(js.type || 'all').trim() || 'all';
  const source = String(js.source || 'all').trim() || 'all';

  const shuffleQuestions = toBool(typeof js.shuffleQuestions !== 'undefined' ? js.shuffleQuestions : js.shuffle_questions);
  const shuffleOptions = toBool(typeof js.shuffleOptions !== 'undefined' ? js.shuffleOptions : js.shuffle_options);

  const params: string[] = [];
  params.push(`subject=${encodeURIComponent(subject)}`);
  params.push(`mode=${encodeURIComponent(mode)}`);
  if (type && type !== 'all') params.push(`type=${encodeURIComponent(type)}`);
  if (source && source !== 'all') params.push(`source=${encodeURIComponent(source)}`);
  if (shuffleQuestions) params.push('shuffle_questions=1');
  if (shuffleOptions) params.push('shuffle_options=1');

  return `/pages/quiz/quiz?${params.join('&')}`;
}

