# -*- coding: utf-8 -*-
"""数据中心扩展上下文 — 标签与洞察段（从 data_center_context_extra.py 拆分）"""
from flask import current_app
from sqlalchemy import text

from app.core.extensions import db


def compute_extra_tags_insights(uid: int, window_days: int, subject_ids: list,
                                bank_ids_active: list,
                                answered_count: int, correct_count: int,
                                mistakes_count: int, favorites_count: int,
                                weakness_rows: list, health_score: float,
                                hourly: dict, heatmap: dict,
                                _pt_to_qt, _safe_int, _chunks) -> dict:
    """计算标签/标签图/全局洞察数据。"""
    tags_public = []
    tags_banks = []
    tags_all = []
    tags_graph = {'nodes': [], 'links': []}
    tags_kpis = {
        'public_tag_count': 0,
        'banks_tag_count': 0,
        'all_tag_count': 0,
        'public_tagged_questions': 0,
        'banks_tagged_questions': 0,
        'all_tagged_questions': 0,
        'tagged_answered_coverage': 0.0,
    }
    global_insights = []
    pub_tagged_answered = 0
    banks_tagged_answered = 0

    # ---------- 标签：公共题库（用户私有标签系统） ----------
    try:
        from app.modules.quiz.services import question_tags_service as _qts

        store = _qts.load_store(db.session, int(uid))
        bindings = store.get('bindings') if isinstance(store.get('bindings'), dict) else {}

        qid_to_tags = {}
        raw_qids = []
        for qid, tag_list in (bindings or {}).items():
            if not isinstance(tag_list, list) or not tag_list:
                continue
            try:
                qid_i = int(qid)
            except Exception:
                continue
            tags = []
            for t in tag_list:
                name = (t or '').strip()
                if not name or name.lower() == 'all':
                    continue
                if name not in tags:
                    tags.append(name)
            if not tags:
                continue
            qid_to_tags[qid_i] = tags
            raw_qids.append(qid_i)

        raw_qids = sorted(set(raw_qids))

        # 过滤锁定/无权限科目
        pub_qids = []
        if raw_qids:
            for chunk in _chunks(raw_qids):
                chunk_params = {f"qid_{i}": v for i, v in enumerate(chunk)}
                sql = f"""
                    SELECT q.id AS id
                    FROM questions q
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE q.id IN ({','.join(f':qid_{i}' for i in range(len(chunk)))})
                      AND (s.is_locked=false OR s.is_locked IS NULL)
                """
                params = dict(chunk_params)
                if subject_ids:
                    sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                    sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                    params.update(sid_params)
                rows = db.session.execute(text(sql), params).fetchall()
                for r in rows or []:
                    if r and r._mapping['id'] is not None:
                        pub_qids.append(int(r._mapping['id']))

        pub_qids = sorted(set(pub_qids))
        pub_qid_set = set(pub_qids)

        # 预加载：答题/收藏/错题（按 question_id）
        ua_map = {}
        fav_set = set()
        mis_times = {}

        if pub_qids:
            for chunk in _chunks(pub_qids):
                chunk_params = {f"p_{i}": v for i, v in enumerate(chunk)}
                chunk_params["uid"] = int(uid)
                chunk_in = ",".join(f":p_{i}" for i in range(len(chunk)))

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid, is_correct AS is_correct FROM user_answers WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        ua_map[int(r._mapping["qid"])] = 1 if int(r._mapping["is_correct"] or 0) == 1 else 0

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid FROM favorites WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        fav_set.add(int(r._mapping["qid"]))

                if mistakes_has_wrong_count:
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid, wrong_count AS wrong_count FROM mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                mis_times[int(r._mapping["qid"])] = _safe_int(r._mapping["wrong_count"], 1)
                else:
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid FROM mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                mis_times[int(r._mapping["qid"])] = 1

        # 聚合标签
        pub_stats = {}
        pub_tagged_questions = 0
        pub_tagged_answered = 0
        for qid, tags in qid_to_tags.items():
            if qid not in pub_qid_set:
                continue
            pub_tagged_questions += 1
            answered = qid in ua_map
            if answered:
                pub_tagged_answered += 1
            is_correct = ua_map.get(qid)
            is_fav = qid in fav_set
            wrong_times = int(mis_times.get(qid) or 0)

            for t in tags:
                it = pub_stats.get(t)
                if not it:
                    it = {'tag': t, 'count': 0, 'answered': 0, 'correct': 0, 'favorites': 0, 'mistakes': 0, 'mistakes_times': 0}
                    pub_stats[t] = it
                it['count'] += 1
                if answered:
                    it['answered'] += 1
                    if int(is_correct or 0) == 1:
                        it['correct'] += 1
                if is_fav:
                    it['favorites'] += 1
                if wrong_times:
                    it['mistakes'] += 1
                    it['mistakes_times'] += wrong_times

        tags_public = []
        for it in pub_stats.values():
            ans = int(it.get('answered') or 0)
            cor = int(it.get('correct') or 0)
            it['accuracy'] = round(cor * 100.0 / ans, 1) if ans > 0 else 0.0
            tags_public.append(it)
        tags_public.sort(key=lambda x: (int(x.get('count') or 0), int(x.get('answered') or 0)), reverse=True)

        tags_kpis['public_tag_count'] = int(len([t for t in tags_public if int(t.get('count') or 0) > 0]))
        tags_kpis['public_tagged_questions'] = int(pub_tagged_questions)
        answered_total = int(all_summary.get('answered') or 0)
        tags_kpis['tagged_answered_coverage'] = round(int(pub_tagged_answered) * 100.0 / answered_total, 1) if answered_total > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"data portal public tags failed: {e}")
        tags_public = []

    # ---------- 标签：个人题库（bank_<id>_tags）+ 合并 ----------
    try:
        bank_qid_to_tags = {}
        bank_raw_qids = set()

        if bank_ids_active:
            from app.modules.user_bank.routes.api import _load_bank_tag_store as _load_bank_store

            for bid in bank_ids_active:
                try:
                    store2 = _load_bank_store(db.session, int(bid), int(uid)) or {}
                except Exception:
                    store2 = {}
                qtags = store2.get('question_tags') if isinstance(store2.get('question_tags'), dict) else {}
                for qid, tag_list in (qtags or {}).items():
                    if not isinstance(tag_list, list) or not tag_list:
                        continue
                    try:
                        qid_i = int(qid)
                    except Exception:
                        continue
                    tags = []
                    for t in tag_list:
                        name = (t or '').strip()
                        if not name or name.lower() == 'all':
                            continue
                        if name not in tags:
                            tags.append(name)
                    if not tags:
                        continue
                    bank_qid_to_tags[qid_i] = tags
                    bank_raw_qids.add(qid_i)

        bank_raw_qids = sorted(bank_raw_qids)
        bank_qids = []
        if bank_raw_qids and bank_ids_active:
            for chunk in _chunks(bank_raw_qids):
                chunk_params = {f"p_{i}": v for i, v in enumerate(chunk)}
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                chunk_params.update(bid_params)
                chunk_in = ",".join(f":p_{i}" for i in range(len(chunk)))
                bid_in = ",".join(f":bid_{i}" for i in range(len(bank_ids_active)))
                sql = f"SELECT id FROM user_bank_questions WHERE id IN ({chunk_in}) AND bank_id IN ({bid_in})"
                rows = db.session.execute(text(sql), chunk_params).fetchall()
                for r in rows or []:
                    if r and r._mapping['id'] is not None:
                        bank_qids.append(int(r._mapping['id']))

        bank_qids = sorted(set(bank_qids))
        bank_qid_set = set(bank_qids)

        ub_ans_map = {}
        ub_fav_set = set()
        ub_mis_times = {}

        if bank_qids:
            for chunk in _chunks(bank_qids):
                chunk_params = {f"p_{i}": v for i, v in enumerate(chunk)}
                chunk_params["uid"] = int(uid)
                chunk_in = ",".join(f":p_{i}" for i in range(len(chunk)))

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid, is_correct AS is_correct FROM user_bank_answers WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        ub_ans_map[int(r._mapping["qid"])] = 1 if int(r._mapping["is_correct"] or 0) == 1 else 0

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid FROM user_bank_favorites WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        ub_fav_set.add(int(r._mapping["qid"]))

                if _column_exists("user_bank_mistakes", "wrong_count"):
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid, wrong_count AS wrong_count FROM user_bank_mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                ub_mis_times[int(r._mapping["qid"])] = _safe_int(r._mapping["wrong_count"], 1)
                else:
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid FROM user_bank_mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                ub_mis_times[int(r._mapping["qid"])] = 1

        bank_stats = {}
        banks_tagged_questions = 0
        banks_tagged_answered = 0
        for qid, tags in bank_qid_to_tags.items():
            if qid not in bank_qid_set:
                continue
            banks_tagged_questions += 1
            answered = qid in ub_ans_map
            if answered:
                banks_tagged_answered += 1
            is_correct = ub_ans_map.get(qid)
            is_fav = qid in ub_fav_set
            wrong_times = int(ub_mis_times.get(qid) or 0)

            for t in tags:
                it = bank_stats.get(t)
                if not it:
                    it = {'tag': t, 'count': 0, 'answered': 0, 'correct': 0, 'favorites': 0, 'mistakes': 0, 'mistakes_times': 0}
                    bank_stats[t] = it
                it['count'] += 1
                if answered:
                    it['answered'] += 1
                    if int(is_correct or 0) == 1:
                        it['correct'] += 1
                if is_fav:
                    it['favorites'] += 1
                if wrong_times:
                    it['mistakes'] += 1
                    it['mistakes_times'] += wrong_times

        tags_banks = []
        for it in bank_stats.values():
            ans = int(it.get('answered') or 0)
            cor = int(it.get('correct') or 0)
            it['accuracy'] = round(cor * 100.0 / ans, 1) if ans > 0 else 0.0
            tags_banks.append(it)
        tags_banks.sort(key=lambda x: (int(x.get('count') or 0), int(x.get('answered') or 0)), reverse=True)

        # 合并公共+个人
        all_stats = {}
        for src in (tags_public or []):
            t = src.get('tag')
            if t:
                all_stats[t] = dict(src)
        for src in (tags_banks or []):
            t = src.get('tag')
            if not t:
                continue
            it = all_stats.get(t)
            if not it:
                all_stats[t] = dict(src)
                continue
            for k in ('count', 'answered', 'correct', 'favorites', 'mistakes', 'mistakes_times'):
                it[k] = int(it.get(k) or 0) + int(src.get(k) or 0)
            ans = int(it.get('answered') or 0)
            cor = int(it.get('correct') or 0)
            it['accuracy'] = round(cor * 100.0 / ans, 1) if ans > 0 else 0.0
        tags_all = list(all_stats.values())
        tags_all.sort(key=lambda x: (int(x.get('count') or 0), int(x.get('answered') or 0)), reverse=True)

        # KPI
        tags_kpis['banks_tag_count'] = int(len([t for t in tags_banks if int(t.get('count') or 0) > 0]))
        tags_kpis['all_tag_count'] = int(len([t for t in tags_all if int(t.get('count') or 0) > 0]))
        tags_kpis['banks_tagged_questions'] = int(banks_tagged_questions)
        tags_kpis['all_tagged_questions'] = int(tags_kpis.get('public_tagged_questions') or 0) + int(banks_tagged_questions)

        answered_total = int(all_summary.get('answered') or 0)
        tags_kpis['tagged_answered_coverage'] = round((int(pub_tagged_answered) + int(banks_tagged_answered)) * 100.0 / answered_total, 1) if answered_total > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"data portal bank tags failed: {e}")
        tags_banks = []
        tags_all = []

    # ---------- 标签图：共现网络（高端可视化） ----------
    try:
        _qid_to_tags = locals().get('qid_to_tags') if isinstance(locals().get('qid_to_tags'), dict) else {}
        _pub_qid_set = locals().get('pub_qid_set') if isinstance(locals().get('pub_qid_set'), set) else set()
        _bank_qid_to_tags = locals().get('bank_qid_to_tags') if isinstance(locals().get('bank_qid_to_tags'), dict) else {}
        _bank_qid_set = locals().get('bank_qid_set') if isinstance(locals().get('bank_qid_set'), set) else set()

        cooc_map = {}
        for qid, tl in (_qid_to_tags or {}).items():
            if _pub_qid_set and qid not in _pub_qid_set:
                continue
            if isinstance(tl, list) and tl:
                cooc_map[f'p{qid}'] = tl
        for qid, tl in (_bank_qid_to_tags or {}).items():
            if _bank_qid_set and qid not in _bank_qid_set:
                continue
            if isinstance(tl, list) and tl:
                cooc_map[f'b{qid}'] = tl

        pair = {}
        for _k, tl in (cooc_map or {}).items():
            if not isinstance(tl, list):
                continue
            uniq = []
            for t in tl:
                if t and t not in uniq:
                    uniq.append(t)
            if len(uniq) < 2:
                continue
            uniq = sorted(uniq)[:12]
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    kk = (uniq[i], uniq[j])
                    pair[kk] = pair.get(kk, 0) + 1

        links = [{'source': a, 'target': b, 'value': int(v)} for (a, b), v in pair.items() if int(v) > 0]
        links.sort(key=lambda x: int(x.get('value') or 0), reverse=True)
        links = links[:56]

        node_names = set()
        for l in links:
            node_names.add(l['source'])
            node_names.add(l['target'])

        count_map = {t.get('tag'): int(t.get('count') or 0) for t in (tags_all or []) if t.get('tag')}
        nodes = [{'name': name, 'value': int(count_map.get(name) or 1)} for name in node_names]
        nodes.sort(key=lambda x: int(x.get('value') or 0), reverse=True)
        tags_graph = {'nodes': nodes[:40], 'links': links}
    except Exception as e:
        current_app.logger.warning(f"data portal tag graph failed: {e}")
        tags_graph = {'nodes': [], 'links': []}

    # ---------- 全局洞察：大局观摘要（用于全局子页面） ----------
    try:
        insights = []

        # 近窗最活跃小时
        try:
            best = None
            for it in (hourly.get('all') or []):
                if not it:
                    continue
                if best is None or int(it.get('total') or 0) > int(best.get('total') or 0):
                    best = it
            if best and int(best.get('total') or 0) > 0:
                h = int(best.get('hour') or 0)
                insights.append({'title': '最活跃时段', 'value': f'{h:02d}:00', 'hint': f"近 {window_days} 天答题 {int(best.get('total') or 0)}"})
        except Exception:
            pass

        # 近窗最活跃周几
        try:
            wk = [0] * 7
            for cell in (heatmap.get('all') or []):
                if not cell or len(cell) < 3:
                    continue
                wd = int(cell[0] or 0)
                wk[wd] += int(cell[2] or 0)
            max_wd = max(range(7), key=lambda i: wk[i])
            if wk[max_wd] > 0:
                names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
                insights.append({'title': '高频日', 'value': names[max_wd], 'hint': f"近 {window_days} 天答题 {wk[max_wd]}"})
        except Exception:
            pass

        # 最大风险点
        try:
            w0 = (weakness_rows or [None])[0]
            if w0:
                insights.append({'title': '优先补短板', 'value': f"{w0.get('subject')}·{w0.get('q_type')}", 'hint': f"正确率 {w0.get('accuracy')}% · 错题 {w0.get('mistakes')}"})
        except Exception:
            pass

        # 进度 / 健康
        insights.append({'title': '学习健康分', 'value': f'{health_score} / 100', 'hint': '覆盖×正确×连续×错题治理'})

        global_insights = insights[:4]
    except Exception:
        global_insights = []

return {
    'tags_public': tags_public,
    'tags_banks': tags_banks,
    'tags_all': tags_all,
    'tags_graph': tags_graph,
    'tags_kpis': tags_kpis,
    'global_insights': global_insights,
}
