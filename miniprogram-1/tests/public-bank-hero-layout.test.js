const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const pageDir = path.join(__dirname, '..', 'miniprogram', 'pages', 'public-bank-v2');
const wxml = fs.readFileSync(path.join(pageDir, 'public-bank-v2.wxml'), 'utf8');
const less = fs.readFileSync(path.join(pageDir, 'public-bank-v2.less'), 'utf8');

test('public bank hero keeps the count pill in the title row like personal banks', () => {
  assert.match(
    wxml,
    /<view class="pb-hero-left">[\s\S]*?<view class="pb-title-row">[\s\S]*?<text class="pb-title">题库广场<\/text>[\s\S]*?<view class="pill pb-count"><text>\{\{total\}\} 个题库<\/text><\/view>[\s\S]*?<\/view>[\s\S]*?<text class="pb-sub">/,
    '题库数目应使用个人题库同款标题行数量徽标与“个题库”文案'
  );

  assert.match(
    less,
    /\.pb-title-row\s*\{[\s\S]*?display:\s*flex;[\s\S]*?justify-content:\s*space-between;[\s\S]*?\}/,
    'pb-title-row 需要用一行两端布局对齐标题和数量'
  );

  assert.match(
    less,
    /\.pb-count\s*\{[\s\S]*?flex:\s*0 0 auto;[\s\S]*?\}/,
    'pb-count 需要与个人题库 mb-count 一样保持内容宽度'
  );

  assert.match(
    less,
    /\.pb-count\s*\{[\s\S]*?white-space:\s*nowrap;[\s\S]*?line-height:\s*1;[\s\S]*?\}/,
    'pb-count 需要禁止文字换行，避免数量徽标被撑成长框'
  );
});
