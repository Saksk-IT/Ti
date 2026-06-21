const assert = require('node:assert/strict');
const test = require('node:test');

global.wx = {
  getStorageSync() {
    return {};
  }
};

const { api } = require('../miniprogram/utils/api');
const { BankQuizSource, PublicQuizSource } = require('../miniprogram/utils/quiz-source');

test('BankQuizSource full_load fetches every paged quiz question', async () => {
  const originalGetBankQuizQuestions = api.getBankQuizQuestions;
  const calls = [];
  const allQuestions = Array.from({ length: 55 }, (_, index) => ({
    id: index + 1,
    content: `题目 ${index + 1}`,
    q_type: '选择题'
  }));

  api.getBankQuizQuestions = async (_bankId, params = {}) => {
    calls.push(Object.assign({}, params));
    const page = Number(params.page || 1);
    const perPage = Number(params.per_page || params.limit || 20);
    const start = (page - 1) * perPage;
    return {
      questions: allQuestions.slice(start, start + perPage),
      total: allQuestions.length,
      page,
      per_page: perPage
    };
  };

  try {
    const source = new BankQuizSource(123);
    const result = await source.getQuestions({ full_load: true, per_page: 20 });

    assert.equal(result.total, 55);
    assert.equal(result.questions.length, 55);
    assert.deepEqual(
      result.questions.map((q) => q.id),
      allQuestions.map((q) => q.id)
    );
    assert.deepEqual(
      calls.map((params) => params.page),
      [1, 2, 3]
    );
  } finally {
    api.getBankQuizQuestions = originalGetBankQuizQuestions;
  }
});

test('PublicQuizSource full_load fetches every paged quiz question', async () => {
  const originalGetQuestions = api.getQuestions;
  const calls = [];
  const allQuestions = Array.from({ length: 45 }, (_, index) => ({
    id: index + 1,
    content: `公共题目 ${index + 1}`,
    q_type: '选择题'
  }));

  api.getQuestions = async (params = {}) => {
    calls.push(Object.assign({}, params));
    const page = Number(params.page || 1);
    const perPage = Number(params.per_page || 20);
    const start = (page - 1) * perPage;
    return {
      questions: allQuestions.slice(start, start + perPage),
      total: allQuestions.length,
      page,
      per_page: perPage
    };
  };

  try {
    const source = new PublicQuizSource('测试科目');
    const result = await source.getQuestions({ full_load: true, per_page: 20 });

    assert.equal(result.total, 45);
    assert.equal(result.questions.length, 45);
    assert.deepEqual(
      result.questions.map((q) => q.id),
      allQuestions.map((q) => q.id)
    );
    assert.deepEqual(
      calls.map((params) => params.page),
      [1, 2, 3]
    );
  } finally {
    api.getQuestions = originalGetQuestions;
  }
});
