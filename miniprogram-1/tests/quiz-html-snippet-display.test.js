const assert = require('node:assert/strict');
const test = require('node:test');

const {
  formatQuizTextForDisplay,
  normalizeOptionItems
} = require('../miniprogram/pages/quiz/modules/quiz-helpers');

test('quiz display text keeps HTML snippets literal', () => {
  assert.equal(
    formatQuizTextForDisplay('<a href="url" target="_blank">'),
    '<a href="url" target="_blank">'
  );
  assert.equal(
    formatQuizTextForDisplay('&lt;a href=&quot;https://www.w3schools.com&quot;&gt;W3Schools&lt;/a&gt;'),
    '<a href="https://www.w3schools.com">W3Schools</a>'
  );
});

test('choice option normalization preserves HTML snippet option values', () => {
  const options = normalizeOptionItems([
    '<a>https://www.w3schools.com</a>',
    '<a href="https://www.w3schools.com">W3Schools</a>',
    '<a href="url" target="_blank">'
  ], formatQuizTextForDisplay);

  assert.deepEqual(
    options.map((item) => item.value),
    [
      '<a>https://www.w3schools.com</a>',
      '<a href="https://www.w3schools.com">W3Schools</a>',
      '<a href="url" target="_blank">'
    ]
  );
  assert.deepEqual(options.map((item) => item.key), ['A', 'B', 'C']);
});
