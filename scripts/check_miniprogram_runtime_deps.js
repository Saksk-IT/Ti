#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const miniprogramRoot = path.join(root, 'miniprogram-1', 'miniprogram');
const projectConfigPath = path.join(root, 'miniprogram-1', 'project.config.json');

const requiredIncludes = [
  { type: 'folder', value: 'pages/bank-detail/behaviors' },
  { type: 'folder', value: 'pages/bank-detail/components' },
  { type: 'folder', value: 'pages/bank-detail/modules' },
  { type: 'folder', value: 'pages/bank-detail/utils' },
  { type: 'folder', value: 'pages/quiz/behaviors' },
  { type: 'folder', value: 'pages/quiz/modules' },
  { type: 'folder', value: 'pages/quiz/utils' },
];

const requiredComponentRefs = [
  {
    owner: 'pages/bank-detail/bank-detail.json',
    component: 'v2-subject-data-ubd',
    value: './components/v2-subject-data-ubd/v2-subject-data-ubd',
  },
  {
    owner: 'pages/bank-detail/components/v2-subject-data-ubd/v2-subject-data-ubd.json',
    component: 'ec-canvas',
    value: '../ec-canvas/ec-canvas',
  },
];

const componentStyleFiles = [
  'components/v2-exam-builder/v2-exam-builder.less',
];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function fail(message, detail) {
  const suffix = detail ? `\n  ${detail}` : '';
  return `${message}${suffix}`;
}

function normalizeInclude(entry) {
  if (!entry || typeof entry !== 'object') return null;
  const type = String(entry.type || '').trim();
  const value = String(entry.value || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
  return type && value ? `${type}:${value}` : null;
}

function checkPackIncludes(errors) {
  const config = readJson(projectConfigPath);
  const includes = Array.isArray(config.packOptions && config.packOptions.include)
    ? config.packOptions.include
    : [];
  const includeKeys = new Set(includes.map(normalizeInclude).filter(Boolean));

  for (const required of requiredIncludes) {
    const key = normalizeInclude(required);
    if (!includeKeys.has(key)) {
      errors.push(fail('小程序打包 include 缺少分包运行依赖', JSON.stringify(required)));
    }

    const abs = path.join(miniprogramRoot, required.value);
    if (!fs.existsSync(abs)) {
      errors.push(fail('小程序打包 include 指向的目录不存在', required.value));
    }
  }
}

function checkComponentRef(errors, ref) {
  const ownerAbs = path.join(miniprogramRoot, ref.owner);
  const owner = readJson(ownerAbs);
  const actual = owner.usingComponents && owner.usingComponents[ref.component];
  if (actual !== ref.value) {
    errors.push(fail(
      '小程序组件引用路径不符合预期',
      `${ref.owner} -> ${ref.component}: expected ${ref.value}, got ${actual || '(missing)'}`,
    ));
    return;
  }

  const baseAbs = path.resolve(path.dirname(ownerAbs), ref.value);
  const componentFiles = ['.js', '.json', '.wxml'];
  for (const ext of componentFiles) {
    if (!fs.existsSync(`${baseAbs}${ext}`)) {
      errors.push(fail('小程序组件运行文件缺失', `${ref.value}${ext}`));
    }
  }
  if (!fs.existsSync(`${baseAbs}.wxss`) && !fs.existsSync(`${baseAbs}.less`)) {
    errors.push(fail('小程序组件样式文件缺失', `${ref.value}.wxss/.less`));
  }
}

function selectorChunks(source) {
  const chunks = [];
  let pending = '';
  source.split(/\r?\n/).forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith('/*')) return;
    pending = pending ? `${pending} ${trimmed}` : trimmed;
    if (trimmed.includes('{')) {
      const selector = pending.slice(0, pending.indexOf('{')).trim();
      if (selector && !selector.startsWith('@')) {
        chunks.push({ line: index + 1, selector });
      }
      pending = '';
    }
    if (trimmed.includes('}')) {
      pending = '';
    }
  });
  return chunks;
}

function selectorHasTagName(selector) {
  return selector.split(',').some((part) => {
    const withoutClasses = part.replace(/\.[A-Za-z_][\w-]*/g, ' ');
    return /(^|[\s>+~])([a-zA-Z][\w-]*)(?=($|[\s.#:[>+~]))/.test(withoutClasses);
  });
}

function checkComponentSelectors(errors) {
  for (const rel of componentStyleFiles) {
    const abs = path.join(miniprogramRoot, rel);
    const source = fs.readFileSync(abs, 'utf8');
    for (const { line, selector } of selectorChunks(source)) {
      if (selector.includes('::')) {
        errors.push(fail('组件样式不允许使用伪元素选择器', `${rel}:${line} ${selector}`));
      }
      if (selector.includes(':')) {
        errors.push(fail('组件样式不允许使用伪类选择器', `${rel}:${line} ${selector}`));
      }
      if (selector.includes('[') || selector.includes(']')) {
        errors.push(fail('组件样式不允许使用属性选择器', `${rel}:${line} ${selector}`));
      }
      if (selector.includes('#')) {
        errors.push(fail('组件样式不允许使用 ID 选择器', `${rel}:${line} ${selector}`));
      }
      if (selectorHasTagName(selector)) {
        errors.push(fail('组件样式不允许使用标签名选择器', `${rel}:${line} ${selector}`));
      }
    }
  }
}

function main() {
  const errors = [];
  checkPackIncludes(errors);
  for (const ref of requiredComponentRefs) {
    checkComponentRef(errors, ref);
  }
  checkComponentSelectors(errors);

  if (errors.length) {
    console.error(errors.join('\n'));
    process.exit(1);
  }

  console.log('miniprogram runtime dependency checks passed');
}

main();
