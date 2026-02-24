# -*- coding: utf-8 -*-
"""
ORM 辅助工具函数。

替代旧 database.py 中的 safe_in_clause() 和 get_table_columns()。
"""
from typing import List, Any

from sqlalchemy.orm import Query


def chunked_in_filter(query: Query, column, values: List[Any], chunk_size: int = 900) -> Query:
    """替代 safe_in_clause()，用 SQLAlchemy .in_() 实现。

    当 values 超过 chunk_size 时，分批 OR 拼接，避免数据库参数上限。

    用法::

        query = chunked_in_filter(Question.query, Question.id, id_list)
    """
    if not values:
        # 返回空结果集
        return query.filter(column == None, column != None)  # noqa: E711

    from sqlalchemy import or_

    if len(values) <= chunk_size:
        return query.filter(column.in_(values))

    conditions = []
    for i in range(0, len(values), chunk_size):
        chunk = values[i:i + chunk_size]
        conditions.append(column.in_(chunk))
    return query.filter(or_(*conditions))


def orm_has_column(model_class, column_name: str) -> bool:
    """检查 ORM 模型是否定义了某个字段。

    替代旧的 get_table_columns() + PRAGMA table_info 动态检查。
    ORM 模型已静态定义所有字段，此函数仅用于过渡期兼容。
    """
    mapper = model_class.__mapper__ if hasattr(model_class, '__mapper__') else None
    if mapper is None:
        return False
    return column_name in mapper.column_attrs
