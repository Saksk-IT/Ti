# -*- coding: utf-8 -*-
"""
数据库索引创建和管理。

从 database.py 拆分而来，包含所有索引定义。
"""

__all__ = [
    "_create_indexes",
]


def _create_indexes(conn):
    """创建数据库索引"""
    # 检查表是否存在，只对存在的表创建索引
    cur = conn.cursor()
    existing_tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    indexes = []

    # 用户相关索引（只对存在的表创建）
    if 'favorites' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_favorites_user_question ON favorites(user_id, question_id)')
    if 'mistakes' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_mistakes_user_question ON mistakes(user_id, question_id)')
    if 'user_answers' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_user_answers_user ON user_answers(user_id, created_at)',
            'CREATE INDEX IF NOT EXISTS idx_user_answers_question ON user_answers(question_id)',
        ])

    # 题目相关索引（只对存在的表创建）
    if 'questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject_id)',
            'CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(type)',
            'CREATE INDEX IF NOT EXISTS idx_questions_subject_type ON questions(subject_id, type)',
        ])

    # 查重记录相关索引
    if 'duplicate_check_records' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_duplicate_check_subject ON duplicate_check_records(subject_id, created_at DESC)',
        ])
    # 加强训练：相似题缓存索引
    if 'reinforce_similar_cache' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_reinforce_similar_cache_updated ON reinforce_similar_cache(updated_at)')

    # 考试相关索引（只对存在的表创建）
    if 'exams' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exams_user_status ON exams(user_id, status)',
            'CREATE INDEX IF NOT EXISTS idx_exams_submitted ON exams(submitted_at)',
        ])
    if 'exam_questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exam_questions_exam ON exam_questions(exam_id)',
            'CREATE INDEX IF NOT EXISTS idx_exam_questions_question ON exam_questions(question_id)',
        ])
    if 'exam_templates' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exam_templates_user ON exam_templates(user_id, updated_at DESC)',
        ])

    # 用户进度索引（只对存在的表创建）
    if 'user_progress' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_progress_key ON user_progress(user_id, p_key)')

    if 'user_checkins' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_checkins_user_date ON user_checkins(user_id, checkin_date DESC)')

    # 用户题目标签（按用户维度）索引
    if 'user_question_tag_items' in existing_tables:
        indexes.extend([
            "CREATE INDEX IF NOT EXISTS idx_uqti_user_scope_scopeid_tag ON user_question_tag_items(user_id, scope, scope_id, tag)",
            "CREATE INDEX IF NOT EXISTS idx_uqti_user_scope_scopeid_qid ON user_question_tag_items(user_id, scope, scope_id, question_id)",
        ])

    # 聊天相关索引（只对存在的表创建）
    if 'chat_members' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_chat_members_user ON chat_members(user_id, conversation_id)')
    if 'chat_messages' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id, id DESC)')
    if 'chat_conversations' in existing_tables:
        indexes.append("CREATE UNIQUE INDEX IF NOT EXISTS ux_chat_direct_pair ON chat_conversations(direct_pair_key) WHERE c_type='direct' AND direct_pair_key IS NOT NULL")
    if 'user_remarks' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_remarks_owner ON user_remarks(owner_user_id, target_user_id)')
    # 通知相关索引（只对存在的表创建）
    if 'notifications' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_notifications_time ON notifications(start_at, end_at)',
        ])
    if 'notification_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_notification_dismissals_user ON notification_dismissals(user_id, notification_id)')

    # 弹窗相关索引（只对存在的表创建）
    if 'popups' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popups_active ON popups(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_popups_time ON popups(start_at, end_at)',
            'CREATE INDEX IF NOT EXISTS idx_popups_type ON popups(popup_type)',
        ])
    if 'popup_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_popup_dismissals_user ON popup_dismissals(user_id, popup_id)')
    if 'popup_views' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popup_views_popup ON popup_views(popup_id, viewed_at)',
            'CREATE INDEX IF NOT EXISTS idx_popup_views_user ON popup_views(user_id, viewed_at)',
        ])

    # 代码提交相关索引（只对存在的表创建）
    if 'code_submissions' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_submissions_user_question ON code_submissions(user_id, question_id, submitted_at DESC)')

    # 代码草稿相关索引
    if 'code_drafts' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_drafts_user_question ON code_drafts(user_id, question_id)')

    # 用户-科目限制表索引
    if 'user_subjects' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_user_id ON user_subjects(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_subject_id ON user_subjects(subject_id)'
        ])

    # 系统配置表索引
    if 'system_config' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key)')

    # 用户刷题统计表索引
    if 'user_quiz_stats' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_quiz_stats_user_id ON user_quiz_stats(user_id)')

    # 邮箱验证码表索引
    if 'email_verification_codes' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_email_codes_email ON email_verification_codes(email, code_type, is_used)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_expires ON email_verification_codes(expires_at)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_user ON email_verification_codes(user_id)',
        ])
    # ============================================
    # 用户私人题库功能相关索引
    # ============================================

    # 用户题库分类表索引
    if 'user_bank_categories' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_ubc_user_id ON user_bank_categories(user_id)')

    # 用户题库表索引
    if 'user_question_banks' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_uqb_user_id ON user_question_banks(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_uqb_category_id ON user_question_banks(category_id)',
            'CREATE INDEX IF NOT EXISTS idx_uqb_status ON user_question_banks(status)',
            'CREATE INDEX IF NOT EXISTS idx_uqb_is_public ON user_question_banks(is_public, status)',
        ])

    # 用户题库题目表索引
    if 'user_bank_questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_ubq_bank_id ON user_bank_questions(bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_ubq_user_id ON user_bank_questions(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_ubq_source ON user_bank_questions(source_type, source_question_id)',
            'CREATE INDEX IF NOT EXISTS idx_ubq_type ON user_bank_questions(type)',
        ])

    # 题库分享表索引
    if 'bank_shares' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_bs_bank_id ON bank_shares(bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_bs_owner_id ON bank_shares(owner_id)',
        ])

    # 分享记录表索引
    if 'bank_share_records' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_bsr_user_id ON bank_share_records(user_id, status)',
            'CREATE INDEX IF NOT EXISTS idx_bsr_bank_id ON bank_share_records(bank_id)',
        ])

    # 用户题库答题记录表索引
    if 'user_bank_answers' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_uba_user_bank ON user_bank_answers(user_id, bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_uba_user_question ON user_bank_answers(user_id, question_id)',
        ])

    # 用户题库错题表索引
    if 'user_bank_mistakes' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_ubm_user_bank ON user_bank_mistakes(user_id, bank_id)')

    # 公开题库使用记录表索引
    if 'public_bank_users' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_pbu_bank_id ON public_bank_users(bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_pbu_user_id ON public_bank_users(user_id)',
        ])

    # 用户题库收藏表索引
    if 'user_bank_favorites' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_ubf_user_id ON user_bank_favorites(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_ubf_bank_id ON user_bank_favorites(bank_id)',
        ])

    # Study 学习/复习索引
    if 'study_learning' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_study_learning_user_scope ON study_learning(user_id, source, scope_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_learning_user_question ON study_learning(user_id, source, scope_id, question_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_learning_learned ON study_learning(user_id, source, scope_id, is_learned)',
        ])
    if 'study_review' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_study_review_user_scope ON study_review(user_id, source, scope_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_review_user_question ON study_review(user_id, source, scope_id, question_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_review_due ON study_review(user_id, source, scope_id, is_mastered, next_due_at)',
        ])

    for index_sql in indexes:
        conn.execute(index_sql)
