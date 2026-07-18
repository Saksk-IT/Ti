import type {
  BoardsResponse,
  DetailResponse,
  HotResponse,
  PlazaListResponse,
  PublicBankBoard,
  PublicBankCard,
  SummaryResponse,
  SystemPublicBankDetail,
  UserPublicBankDetail,
} from '../api/generated/phase4aPublicBank/types.gen';

export const fixtureRequestId = 'web-foundation-fixture-request-id';

const boardSeeds = [
  { id: 1, slug: 'computer-science', name: '计算机科学', description: '计算机基础与工程实践' },
  { id: 2, slug: 'mathematics', name: '数学', description: '高等数学与离散数学' },
  { id: 3, slug: 'algorithms', name: '算法与数据结构', description: '算法、数据结构与复杂度' },
  { id: 4, slug: 'database', name: '数据库', description: '数据库系统与查询优化' },
] as const;

const names = [
  'CS 自学指南 · 题库',
  '算法与数据结构进阶题库',
  '离散数学题库',
  '数据库系统原理题库',
  '计算机网络核心题库',
  '操作系统基础题库',
  '高等数学精选题库',
  '线性代数练习集',
  '程序设计基础题库',
  '软件工程知识库',
  '编译原理核心题库',
  '概率论与数理统计',
] as const;

function makeCard(index: number): PublicBankCard {
  const board = boardSeeds[index % boardSeeds.length]!;
  const sourceType = index % 3 === 0 ? 'user_public' : 'system';
  const id = 101 + index;
  return {
    id,
    source_type: sourceType,
    name: names[index]!,
    description: `覆盖${board.name}核心概念、典型题型与阶段性复习内容，适合按知识结构持续巩固。`,
    cover_image: null,
    owner_label: sourceType === 'system' ? 'SAK 教研组' : `公开作者 ${index + 1}`,
    owner_avatar: null,
    question_count: 4800 - index * 173,
    participants_total: 6400 - index * 197,
    join_users_7d: 340 - index * 11,
    answer_users_7d: 1200 - index * 49,
    answer_count_7d: 4200 - index * 107,
    hot_score: 1000 - index * 37,
    active_score: 900 - index * 29,
    recommended_score: 800 - index * 19,
    published_at: `2025-05-${String(20 - index).padStart(2, '0')} 09:30:00`,
    last_activity_at: `2025-06-${String(20 - index).padStart(2, '0')} 18:20:00`,
    is_featured: index < 3,
    featured_weight: index < 3 ? 10 - index : 0,
    board: { id: board.id, slug: board.slug, name: board.name },
    detail_url: `/public/banks/card/${sourceType === 'system' ? 'system' : 'user'}/${id}`,
    practice_url: sourceType === 'system' ? `/subjects/${id}` : `/user/banks/${id}/practice`,
    source_label: sourceType === 'system' ? '系统题库' : '用户公开',
    join_mode: 'free',
    join_note: sourceType === 'system' ? '系统题库当前支持免费加入。' : '公开题库可免费加入。',
    allow_copy: sourceType === 'user_public',
    relation: { joined_via: 'none', is_joined: false },
  };
}

export const publicBankCards: PublicBankCard[] = names.map((_, index) => makeCard(index));

export const publicBankBoards: PublicBankBoard[] = boardSeeds.map((board) => ({
  ...board,
  bank_count: publicBankCards.filter((bank) => bank.board.id === board.id).length,
}));

function filteredCards(keyword: string, boardId: string): PublicBankCard[] {
  const normalizedKeyword = keyword.trim().toLocaleLowerCase('zh-CN');
  return publicBankCards.filter((bank) => {
    const boardMatches = !boardId || String(bank.board.id) === boardId;
    const keywordMatches =
      !normalizedKeyword ||
      [bank.name, bank.description, bank.owner_label]
        .join(' ')
        .toLocaleLowerCase('zh-CN')
        .includes(normalizedKeyword);
    return boardMatches && keywordMatches;
  });
}

export function makePlazaListResponse(search: URLSearchParams): PlazaListResponse {
  const keyword = search.get('keyword') ?? '';
  const boardId = search.get('board_id') ?? '';
  const tab = search.get('tab') ?? 'latest';
  const page = Math.max(1, Number.parseInt(search.get('page') ?? '1', 10) || 1);
  const perPage = Math.min(50, Math.max(1, Number.parseInt(search.get('per_page') ?? '10', 10) || 10));
  const sorted = [...filteredCards(keyword, boardId)].sort((left, right) => {
    if (tab === 'hot') return right.hot_score - left.hot_score;
    if (tab === 'active') return right.active_score - left.active_score;
    if (tab === 'featured') return right.featured_weight - left.featured_weight;
    return String(right.published_at).localeCompare(String(left.published_at));
  });
  const start = (page - 1) * perPage;
  return {
    status: 'success',
    code: 0,
    data: {
      items: sorted.slice(start, start + perPage),
      total: sorted.length,
      page,
      per_page: perPage,
      tab: ['latest', 'hot', 'active', 'featured', 'questions'].includes(tab)
        ? (tab as PlazaListResponse['data']['tab'])
        : 'latest',
      keyword,
      board_id: boardId ? Number(boardId) : null,
      available_tabs: ['latest', 'hot', 'active', 'featured'],
    },
    message: '',
    request_id: fixtureRequestId,
  };
}

export function makeBoardsResponse(search: URLSearchParams): BoardsResponse {
  const keyword = (search.get('keyword') ?? '').toLocaleLowerCase('zh-CN');
  return {
    status: 'success',
    code: 0,
    data: {
      items: keyword
        ? publicBankBoards.filter((board) => board.name.toLocaleLowerCase('zh-CN').includes(keyword))
        : publicBankBoards,
    },
    message: '',
    request_id: fixtureRequestId,
  };
}

export function makeHotResponse(search: URLSearchParams): HotResponse {
  const cards = filteredCards(search.get('keyword') ?? '', search.get('board_id') ?? '');
  const limit = Math.min(10, Math.max(1, Number.parseInt(search.get('limit') ?? '5', 10) || 5));
  return {
    status: 'success',
    code: 0,
    data: { items: [...cards].sort((a, b) => b.hot_score - a.hot_score).slice(0, limit) },
    message: '',
    request_id: fixtureRequestId,
  };
}

export function makeSummaryResponse(search: URLSearchParams): SummaryResponse {
  const cards = filteredCards(search.get('keyword') ?? '', search.get('board_id') ?? '');
  return {
    status: 'success',
    code: 0,
    data: {
      total_banks: cards.length,
      total_questions: cards.reduce((total, bank) => total + bank.question_count, 0),
      total_boards: new Set(cards.map((bank) => bank.board.id)).size,
      new_banks_7d: Math.min(3, cards.length),
      active_users_7d: cards.reduce((total, bank) => total + bank.answer_users_7d, 0),
      source_breakdown: {
        system: cards.filter((bank) => bank.source_type === 'system').length,
        user_public: cards.filter((bank) => bank.source_type === 'user_public').length,
      },
    },
    message: '',
    request_id: fixtureRequestId,
  };
}

export function makeDetailResponse(sourceType: string, bankId: string): DetailResponse | undefined {
  const card = publicBankCards.find(
    (bank) => String(bank.id) === bankId &&
      bank.source_type === (sourceType === 'system' ? 'system' : 'user_public'),
  );
  if (!card) return undefined;

  const detail: SystemPublicBankDetail | UserPublicBankDetail = card.source_type === 'system'
    ? {
        ...card,
        source_type: 'system',
        source_label: '系统题库',
        bank_type: 'system',
        join_mode: 'free',
        join_note: '系统题库当前支持免费加入。',
        allow_copy: false,
      }
    : {
        ...card,
        source_type: 'user_public',
        source_label: '用户公开',
        bank_type: 'user',
        share_count: 12,
        author_id: 9001,
        is_owner: false,
      };
  return {
    status: 'success',
    code: 0,
    data: detail,
    message: '',
    request_id: fixtureRequestId,
  };
}
