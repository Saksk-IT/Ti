# -*- coding: utf-8 -*-
"""
SQLAlchemy ORM 模型包。

所有模型从此处统一导出，供 Flask-Migrate 自动发现。
旧代码仍可使用 get_db() 访问原始连接；新代码推荐使用 db.session + ORM 模型。
"""
from app.core.extensions import db

from .user import User, EmailVerificationCode
from .subject import Subject, Question
from .quiz import Favorite, Mistake, UserAnswer, UserProgress, UserCheckin, UserQuizStats
from .exam import Exam, ExamQuestion, ExamTemplate
from .coding import (
    CodingSubject, CodingQuestion, CodeSubmission,
    CodingStatistics, UserCodingStats, CodeDraft,
)
from .chat import ChatConversation, ChatMember, ChatMessage, UserRemark
from .notification import Notification, NotificationDismissal
from .popup import Popup, PopupDismissal, PopupView
from .user_bank import (
    UserBankCategory, UserQuestionBank, UserBankQuestion,
    BankShare, BankShareRecord, UserBankAnswer,
    UserBankMistake, PublicBankUser, UserBankFavorite,
)
from .study import StudyLearning, StudyReview
from .system import (
    SystemConfig, UserSubject, UserQuestionTagItem,
    DuplicateCheckRecord, ReinforceSimilarCache, SchemaMigration,
)

__all__ = [
    'db',
    # user
    'User', 'EmailVerificationCode',
    # subject
    'Subject', 'Question',
    # quiz
    'Favorite', 'Mistake', 'UserAnswer', 'UserProgress', 'UserCheckin', 'UserQuizStats',
    # exam
    'Exam', 'ExamQuestion', 'ExamTemplate',
    # coding
    'CodingSubject', 'CodingQuestion', 'CodeSubmission',
    'CodingStatistics', 'UserCodingStats', 'CodeDraft',
    # chat
    'ChatConversation', 'ChatMember', 'ChatMessage', 'UserRemark',
    # notification
    'Notification', 'NotificationDismissal',
    # popup
    'Popup', 'PopupDismissal', 'PopupView',
    # user_bank
    'UserBankCategory', 'UserQuestionBank', 'UserBankQuestion',
    'BankShare', 'BankShareRecord', 'UserBankAnswer',
    'UserBankMistake', 'PublicBankUser', 'UserBankFavorite',
    # study
    'StudyLearning', 'StudyReview',
    # system
    'SystemConfig', 'UserSubject', 'UserQuestionTagItem',
    'DuplicateCheckRecord', 'ReinforceSimilarCache', 'SchemaMigration',
]
