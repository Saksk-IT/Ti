# -*- coding: utf-8 -*-
"""
SQLAlchemy ORM 模型包。

所有模型从此处统一导出，供 Flask-Migrate 自动发现。
统一使用 db.session + ORM 模型进行数据库操作。
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
from .ai_chat import AIChatSession, AIChatMessage
from .ai_change_record import AIChangeRecord
from .notification import Notification, NotificationDismissal
from .popup import Popup, PopupDismissal, PopupView
from .plaza import PlazaBoard, PublicBankPlazaMetric, PublicSubjectUser
from .user_bank import (
    UserBankCategory, UserQuestionBank, UserBankQuestion,
    BankShare, BankShareRecord, UserBankAnswer,
    UserBankMistake, PublicBankUser, UserBankFavorite,
)
from .study import StudyLearning, StudyReview
from .forum import (
    ForumBoard, ForumPost, ForumComment, ForumLike, ForumFavorite,
    ForumReaction, ForumPollVote, ForumReport, ForumMention, ForumUserBan,
)
from .system import (
    SystemConfig, UserSubject, UserQuestionTagItem,
    DuplicateCheckRecord, ReinforceSimilarCache, SchemaMigration,
)
from .edu_schedule import EduGradeSnapshot, EduScheduleCredential, EduScheduleSnapshot

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
    'AIChatSession', 'AIChatMessage', 'AIChangeRecord',
    # notification
    'Notification', 'NotificationDismissal',
    # popup
    'Popup', 'PopupDismissal', 'PopupView',
    # plaza
    'PlazaBoard', 'PublicBankPlazaMetric', 'PublicSubjectUser',
    # user_bank
    'UserBankCategory', 'UserQuestionBank', 'UserBankQuestion',
    'BankShare', 'BankShareRecord', 'UserBankAnswer',
    'UserBankMistake', 'PublicBankUser', 'UserBankFavorite',
    # study
    'StudyLearning', 'StudyReview',
    # forum
    'ForumBoard', 'ForumPost', 'ForumComment', 'ForumLike', 'ForumFavorite',
    'ForumReaction', 'ForumPollVote', 'ForumReport', 'ForumMention', 'ForumUserBan',
    # system
    'SystemConfig', 'UserSubject', 'UserQuestionTagItem',
    'DuplicateCheckRecord', 'ReinforceSimilarCache', 'SchemaMigration',
    # edu schedule
    'EduScheduleCredential', 'EduScheduleSnapshot', 'EduGradeSnapshot',
]
