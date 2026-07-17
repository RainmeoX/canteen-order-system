# -*- coding: utf-8 -*-
"""
智能食堂预订系统 - 数据库初始化脚本
负责创建数据库文件、表结构和初始数据
"""

import sqlite3
import os

# 数据库文件路径
DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'canteen.db')


def init_database():
    """初始化数据库：创建表结构和初始数据"""
    # 确保数据库目录存在
    os.makedirs(DATABASE_DIR, exist_ok=True)

    # 连接数据库（不存在则自动创建）
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()

    # ============ 用户表 ============
    # 存储用户信息，包括管理员和普通用户
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            employee_id TEXT UNIQUE,
            role TEXT DEFAULT 'user',
            bind_status INTEGER DEFAULT 0,
            violation_count INTEGER DEFAULT 0
        )
    ''')

    # ============ 菜品表 ============
    # 存储菜品信息，支持库存管理和限购设置
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            remaining INTEGER NOT NULL,
            limit_per_person INTEGER DEFAULT 5,
            status TEXT DEFAULT '上架',
            initial_stock INTEGER,
            nutrition_info TEXT,
            allergy_tag TEXT,
            alias TEXT
        )
    ''')

    # ============ 订单表 ============
    # 存储订单信息，关联用户和菜品
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            dish_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            order_time DATETIME NOT NULL,
            take_deadline DATETIME NOT NULL,
            status TEXT DEFAULT 'pending',
            pickup_code TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # ============ 系统配置表 ============
    # 存储系统全局配置项
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============ 管理员操作日志表 ============
    # 记录管理员的所有操作
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users (user_id)
        )
    ''')

    # ============ 索引 ============
    # 优化订单查询性能
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders (user_id, DATE(order_time))
    ''')

    # 优化菜品查询性能
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_dishes_name_status ON dishes (name, status)
    ''')

    # ============ 初始数据 ============
    # 下单截止时间（每日10:00）
    cursor.execute('''
        INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('order_cutoff_time', '10:00')
    ''')
    # 取餐开始时间
    cursor.execute('''
        INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_start', '11:30')
    ''')
    # 取餐结束时间
    cursor.execute('''
        INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_end', '12:30')
    ''')

    # 默认管理员账户
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, name, employee_id, role, bind_status)
        VALUES ('admin_ma', '马静', '0001', 'admin', 1)
    ''')

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DATABASE_PATH}")


if __name__ == '__main__':
    init_database()