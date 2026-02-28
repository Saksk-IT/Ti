# -*- coding: utf-8 -*-
"""
题目查重服务
负责计算题目相似度、查找重复题目
"""
from typing import Dict, List, Tuple, Any, Optional
import difflib
import re
import json

from app.core.extensions import db
from app.models.subject import Subject, Question as QuestionModel
from app.models.system import DuplicateCheckRecord


class DuplicateCheckService:
    """题目查重服务"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        标准化文本，用于相似度比较
        
        Args:
            text: 原始文本
            
        Returns:
            标准化后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除标点符号（可选，根据需求决定是否保留）
        # text = re.sub(r'[^\w\s]', '', text)
        # 转换为小写（对于中文可能不需要，但可以保留）
        return text.strip()
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（0-1之间）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度（0-1之间）
        """
        if not text1 or not text2:
            return 0.0
        
        # 标准化文本
        norm1 = DuplicateCheckService.normalize_text(text1)
        norm2 = DuplicateCheckService.normalize_text(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # 如果完全相同
        if norm1 == norm2:
            return 1.0
        
        # 使用SequenceMatcher计算相似度
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        
        return round(similarity, 4)
    
    @staticmethod
    def check_duplicates(subject_id: int, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """检查指定科目中的重复题目"""
        questions = QuestionModel.query.filter_by(subject_id=subject_id).order_by(QuestionModel.id).all()

        if len(questions) < 2:
            return []

        from app.core.utils.pqf_rows import pqf_row_to_internal

        question_list = []
        for q in questions:
            row_dict = {
                'id': q.id, 'subject_id': q.subject_id, 'type': q.type,
                'content': q.content, 'options': q.options, 'answer': q.answer,
                'analysis': q.analysis, 'tags': q.tags, 'difficulty': q.difficulty,
                'created_at': q.created_at, 'updated_at': q.updated_at,
            }
            question_list.append(pqf_row_to_internal(row_dict, scope="question_center"))
        
        # 计算所有题目对的相似度
        duplicates = []
        checked_pairs = set()  # 用于避免重复比较
        
        for i in range(len(question_list)):
            for j in range(i + 1, len(question_list)):
                q1 = question_list[i]
                q2 = question_list[j]
                
                # 跳过同一道题目
                if q1['id'] == q2['id']:
                    continue
                
                # 创建唯一标识符（避免重复比较）
                pair_key = tuple(sorted([q1['id'], q2['id']]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # 长度比剪枝：长度差异 > 50% 直接跳过（避免无效 SequenceMatcher 计算）
                text1 = DuplicateCheckService.normalize_text(q1.get('content', '') or '')
                text2 = DuplicateCheckService.normalize_text(q2.get('content', '') or '')
                if text1 and text2:
                    len1, len2 = len(text1), len(text2)
                    if max(len1, len2) > 2 * min(len1, len2):
                        continue

                # 计算题目内容的相似度
                similarity = DuplicateCheckService.calculate_similarity(
                    q1.get('content', '') or '',
                    q2.get('content', '') or ''
                )
                
                # 如果相似度超过阈值，添加到结果中
                if similarity >= similarity_threshold:
                    duplicates.append({
                        'question1': q1,
                        'question2': q2,
                        'similarity': similarity,
                        'similarity_percent': int(similarity * 100)
                    })
        
        # 按相似度降序排序
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        
        return duplicates
    
    @staticmethod
    def get_duplicate_check_results(
        subject_id: int,
        min_similarity: Optional[float] = None,
        max_similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """获取查重结果（支持相似度筛选）"""
        subject = Subject.query.get(subject_id)

        if not subject:
            return {
                'total_pairs': 0,
                'duplicates': [],
                'subject_id': subject_id,
                'subject_name': None
            }

        subject_name = subject.name
        
        # 执行查重
        duplicates = DuplicateCheckService.check_duplicates(subject_id)
        
        # 应用相似度筛选
        if min_similarity is not None or max_similarity is not None:
            filtered_duplicates = []
            for dup in duplicates:
                sim = dup['similarity']
                if min_similarity is not None and sim < min_similarity:
                    continue
                if max_similarity is not None and sim > max_similarity:
                    continue
                filtered_duplicates.append(dup)
            duplicates = filtered_duplicates
        
        return {
            'total_pairs': len(duplicates),
            'duplicates': duplicates,
            'subject_id': subject_id,
            'subject_name': subject_name
        }
    
    @staticmethod
    def save_duplicate_check_record(
        subject_id: int,
        duplicates: List[Dict[str, Any]],
        similarity_threshold: float = 0.8,
        created_by: Optional[int] = None
    ) -> int:
        """保存查重记录到数据库"""
        duplicates_json = json.dumps(duplicates, ensure_ascii=False, default=str)

        record = DuplicateCheckRecord(
            subject_id=subject_id,
            total_pairs=len(duplicates),
            duplicates_json=duplicates_json,
            similarity_threshold=similarity_threshold,
            created_by=created_by,
        )
        db.session.add(record)
        db.session.commit()

        return record.id

    @staticmethod
    def get_latest_duplicate_check_record(subject_id: int) -> Optional[Dict[str, Any]]:
        """获取指定科目的最新查重记录"""
        record = (
            DuplicateCheckRecord.query
            .filter_by(subject_id=subject_id)
            .order_by(DuplicateCheckRecord.created_at.desc())
            .first()
        )

        if not record:
            return None

        record_dict = {
            'id': record.id,
            'subject_id': record.subject_id,
            'total_pairs': record.total_pairs,
            'similarity_threshold': record.similarity_threshold,
            'created_by': record.created_by,
            'created_at': record.created_at,
        }

        try:
            record_dict['duplicates'] = json.loads(record.duplicates_json or '[]')
        except (json.JSONDecodeError, TypeError):
            record_dict['duplicates'] = []

        return record_dict
    
    @staticmethod
    def perform_and_save_duplicate_check(
        subject_id: int,
        similarity_threshold: float = 0.8,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行查重并保存记录
        
        Args:
            subject_id: 科目ID
            similarity_threshold: 相似度阈值
            created_by: 创建者用户ID（可选）
            
        Returns:
            包含查重结果和记录ID的字典
        """
        # 执行查重
        duplicates = DuplicateCheckService.check_duplicates(subject_id, similarity_threshold)
        
        # 获取科目信息
        subject = Subject.query.get(subject_id)
        subject_name = subject.name if subject else ''
        
        # 保存查重记录
        record_id = DuplicateCheckService.save_duplicate_check_record(
            subject_id=subject_id,
            duplicates=duplicates,
            similarity_threshold=similarity_threshold,
            created_by=created_by
        )
        
        return {
            'record_id': record_id,
            'total_pairs': len(duplicates),
            'duplicates': duplicates,
            'subject_id': subject_id,
            'subject_name': subject_name,
            'similarity_threshold': similarity_threshold
        }

