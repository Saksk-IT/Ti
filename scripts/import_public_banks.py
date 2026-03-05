#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从备份数据库导入公共题库数据到当前开发环境

只导入公共题库相关数据，不导入任何用户数据
"""
import os
import sys
import subprocess
import tempfile
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.core.extensions import db
from app.models.user_bank import UserQuestionBank, UserBankQuestion
from app.models.user import User

BACKUP_FILE = "backups/ti_db_20260303_150642.dump"
DOCKER_CONTAINER = "ti-main-postgres-1"


def extract_table_data(table_name):
    """从备份文件中提取指定表的数据"""
    print(f"正在提取 {table_name} 表数据...")

    # 使用 pg_restore 提取数据到临时 SQL 文件
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as f:
        temp_file = f.name

    try:
        # 复制备份文件到容器（如果还没有）
        subprocess.run(
            ["docker", "cp", BACKUP_FILE, f"{DOCKER_CONTAINER}:/tmp/backup.dump"],
            check=True,
            capture_output=True
        )

        # 提取表数据到 SQL 文件
        result = subprocess.run(
            [
                "docker", "exec", DOCKER_CONTAINER,
                "pg_restore", "-U", "studyuser",
                "--data-only", "--table", table_name,
                "-f", f"/tmp/{table_name}.sql",
                "/tmp/backup.dump"
            ],
            capture_output=True,
            text=True
        )

        # 从容器复制 SQL 文件到本地
        subprocess.run(
            ["docker", "cp", f"{DOCKER_CONTAINER}:/tmp/{table_name}.sql", temp_file],
            check=True,
            capture_output=True
        )

        with open(temp_file, 'r', encoding='utf-8') as f:
            return f.read()
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def parse_copy_data(sql_content, table_name):
    """解析 COPY 语句中的数据"""
    lines = sql_content.split('\n')
    data_lines = []
    in_copy = False
    columns = []

    for line in lines:
        if line.startswith(f'COPY public.{table_name}'):
            in_copy = True
            # 提取列名
            cols_part = line.split('(')[1].split(')')[0]
            columns = [c.strip() for c in cols_part.split(',')]
            continue

        if in_copy and line == '\\.':
            break

        if in_copy and line.strip():
            data_lines.append(line)

    return columns, data_lines


def create_system_user(app):
    """创建系统用户用于公共题库"""
    with app.app_context():
        # 检查是否已存在系统用户
        system_user = User.query.filter_by(username='system_public').first()
        if not system_user:
            system_user = User(
                username='system_public',
                email='system@public.local',
                password_hash='',  # 系统用户不需要密码
                is_locked=True  # 禁用登录
            )
            db.session.add(system_user)
            db.session.commit()
            print(f"创建系统用户: id={system_user.id}")
        else:
            print(f"系统用户已存在: id={system_user.id}")

        return system_user.id


def import_public_banks(app, system_user_id):
    """导入公共题库数据"""
    print("\n开始导入公共题库...")

    # 提取 user_question_banks 数据
    sql_content = extract_table_data('user_question_banks')
    columns, data_lines = parse_copy_data(sql_content, 'user_question_banks')

    print(f"找到 {len(data_lines)} 条题库记录")

    # 解析列索引
    col_idx = {col: i for i, col in enumerate(columns)}

    imported_count = 0
    public_banks = []

    with app.app_context():
        for line in data_lines:
            parts = line.split('\t')

            # 检查是否为公共题库
            is_public_idx = col_idx.get('is_public')
            if is_public_idx is None or parts[is_public_idx] != 't':
                continue

            # 提取字段
            bank_id = int(parts[col_idx['id']])
            name = parts[col_idx['name']]
            description = parts[col_idx.get('description', -1)] if col_idx.get('description', -1) != -1 and parts[col_idx.get('description', -1)] != '\\N' else None
            question_count = int(parts[col_idx['question_count']]) if parts[col_idx['question_count']] != '\\N' else 0

            # 创建题库记录（使用系统用户ID）
            bank = UserQuestionBank(
                user_id=system_user_id,
                name=name,
                description=description,
                is_public=True,
                question_count=question_count,
                allow_copy=True,
                status=1
            )
            db.session.add(bank)
            db.session.flush()  # 获取新ID

            public_banks.append((bank_id, bank.id))  # 保存旧ID到新ID的映射
            imported_count += 1
            print(f"  导入题库: {name} (原ID={bank_id}, 新ID={bank.id}, 题目数={question_count})")

        db.session.commit()

    print(f"\n成功导入 {imported_count} 个公共题库")
    return dict(public_banks)


def import_bank_questions(app, bank_id_mapping, system_user_id):
    """导入公共题库的题目"""
    print("\n开始导入题库题目...")

    # 提取 user_bank_questions 数据
    sql_content = extract_table_data('user_bank_questions')
    columns, data_lines = parse_copy_data(sql_content, 'user_bank_questions')

    print(f"找到 {len(data_lines)} 条题目记录")

    col_idx = {col: i for i, col in enumerate(columns)}

    imported_count = 0

    with app.app_context():
        for line in data_lines:
            parts = line.split('\t')

            # 检查题目所属的题库是否为公共题库
            old_bank_id = int(parts[col_idx['bank_id']])
            if old_bank_id not in bank_id_mapping:
                continue

            new_bank_id = bank_id_mapping[old_bank_id]

            # 提取字段
            question_type = parts[col_idx['type']]
            content = parts[col_idx['content']]
            options = parts[col_idx['options']]
            answer = parts[col_idx['answer']]
            analysis = parts[col_idx.get('analysis', -1)] if col_idx.get('analysis', -1) != -1 and parts[col_idx.get('analysis', -1)] != '\\N' else None
            tags = parts[col_idx.get('tags', -1)] if col_idx.get('tags', -1) != -1 else '[]'
            difficulty = int(parts[col_idx.get('difficulty', -1)]) if col_idx.get('difficulty', -1) != -1 and parts[col_idx.get('difficulty', -1)] != '\\N' else 1

            # 创建题目记录
            question = UserBankQuestion(
                bank_id=new_bank_id,
                user_id=system_user_id,
                type=question_type,
                content=content,
                options=options,
                answer=answer,
                analysis=analysis,
                tags=tags,
                difficulty=difficulty,
                source_type='imported'
            )
            db.session.add(question)
            imported_count += 1

            if imported_count % 100 == 0:
                db.session.commit()
                print(f"  已导入 {imported_count} 道题目...")

        db.session.commit()

    print(f"\n成功导入 {imported_count} 道题目")


def main():
    """主函数"""
    print("=" * 60)
    print("公共题库数据导入工具")
    print("=" * 60)

    # 检查备份文件
    if not os.path.exists(BACKUP_FILE):
        print(f"错误: 备份文件不存在: {BACKUP_FILE}")
        return 1

    # 创建 Flask 应用
    app = create_app()

    try:
        # 1. 创建系统用户
        system_user_id = create_system_user(app)

        # 2. 导入公共题库
        bank_id_mapping = import_public_banks(app, system_user_id)

        # 3. 导入题库题目
        if bank_id_mapping:
            import_bank_questions(app, bank_id_mapping, system_user_id)

        print("\n" + "=" * 60)
        print("导入完成！")
        print("=" * 60)

        # 显示统计信息
        with app.app_context():
            bank_count = UserQuestionBank.query.filter_by(is_public=True).count()
            question_count = UserBankQuestion.query.filter_by(source_type='imported').count()
            print(f"\n统计信息:")
            print(f"  公共题库数量: {bank_count}")
            print(f"  导入题目数量: {question_count}")

        return 0

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
