# -*- coding: utf-8 -*-
"""
数据库访问层 (DAO)
集中管理连接、配置读取、操作日志、权限校验。
业务路由从本模块导入，避免在 app.py 里重复堆砌底层细节。
"""

import sqlite3
from flask import g


def get_db():
    """获取数据库连接，使用 Flask 的 g 对象实现请求级连接复用"""
    if 'db' not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config['DATABASE_PATH'])
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute("PRAGMA timezone='localtime'")  # 与 Python datetime.now() 本地时区对齐
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error):
    """请求结束时自动关闭数据库连接"""
    if hasattr(g, 'db'):
        g.db.close()


def get_config(key):
    """获取系统配置项"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM system_config WHERE config_key = ?', (key,))
    row = cursor.fetchone()
    return row['value'] if row else None


def set_config(key, value):
    """设置系统配置项并记录更新时间"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE system_config SET value = ?, updated_at = datetime("now") WHERE config_key = ?',
        (value, key)
    )
    conn.commit()


def log_admin_action(admin_id, action, detail):
    """记录管理员操作日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO admin_logs (admin_id, action, detail) VALUES (?, ?, ?)',
        (admin_id, action, detail)
    )
    conn.commit()


def check_admin_bind(admin_id):
    """检查管理员是否已绑定信息，返回 (admin_row, error_response)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ? AND role = "admin"', (admin_id,))
    admin = cursor.fetchone()
    if not admin:
        return None, {'success': False, 'message': '管理员账号不存在', 'need_bind': False}, 403
    if admin['bind_status'] == 0 or not admin['name']:
        return admin, {'success': False, 'message': '管理员尚未绑定信息', 'need_bind': True}, 403
    return admin, None, None
