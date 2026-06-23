const assert = require('node:assert/strict');
const test = require('node:test');

const {
  getAnswerCardHidden,
  toggleAnswerCardHidden,
  resetAnswerCardHidden
} = require('../miniprogram/pages/quiz/modules/answer-card-state');

test('answer card is visible by default and toggles immutably per question', () => {
  const initial = {};

  assert.equal(getAnswerCardHidden(initial, 101), false);

  const hidden = toggleAnswerCardHidden(initial, 101);
  assert.equal(getAnswerCardHidden(hidden, 101), true);
  assert.equal(getAnswerCardHidden(initial, 101), false);

  const visible = toggleAnswerCardHidden(hidden, 101);
  assert.equal(getAnswerCardHidden(visible, 101), false);
  assert.notEqual(hidden, visible);
});

test('answer card hidden state resets for the next question', () => {
  const hidden = toggleAnswerCardHidden({}, 101);
  const reset = resetAnswerCardHidden(hidden, 101);

  assert.equal(getAnswerCardHidden(reset, 101), false);
  assert.deepEqual(reset, {});
  assert.equal(getAnswerCardHidden(hidden, 101), true);
});
