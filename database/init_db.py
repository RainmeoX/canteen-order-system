# -*- coding: utf-8 -*-
"""
智能食堂预订系统 - 数据库初始化脚本（redesign 版）
新增：菜品分类、价格、图片占位、订单备注
"""
import sqlite3
import os

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'canteen.db')


def init_database():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            employee_id TEXT UNIQUE,
            role TEXT DEFAULT 'user',
            bind_status INTEGER DEFAULT 0,
            violation_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 菜品表（新增 category, price, description, image_emoji）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT '热菜',
            price REAL DEFAULT 0,
            remaining INTEGER NOT NULL,
            limit_per_person INTEGER DEFAULT 5,
            status TEXT DEFAULT '上架',
            initial_stock INTEGER,
            nutrition_info TEXT,
            allergy_tag TEXT,
            alias TEXT,
            description TEXT,
            image_emoji TEXT DEFAULT '🍽️'
        )
    ''')

    # 订单表（新增 remark, total_price）
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
            remark TEXT,
            unit_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders (user_id, DATE(order_time))')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dishes_name_status ON dishes (name, status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dishes_category ON dishes (category, status)')

    # 初始配置
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('order_cutoff_time', '10:00')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_start', '11:30')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_end', '12:30')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('canteen_name', '智慧食堂')")

    # 管理员（需绑定）
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, name, employee_id, role, bind_status)
        VALUES ('admin', '', '', 'admin', 0)
    ''')

    # 示例菜品（带分类、价格、emoji）
    sample_dishes = [
        # 热菜
        ('红烧肉', '热菜', 18.0, 50, 2, '{"cal": 350, "sugar": 5}', '', '红烧', '肥而不腻，入口即化', '🍖'),
        ('宫保鸡丁', '热菜', 16.0, 40, 2, '{"cal": 280, "sugar": 8}', '花生', '宫保', '鸡丁花生，香辣下饭', '🍗'),
        ('鱼香肉丝', '热菜', 15.0, 35, 2, '{"cal": 300, "sugar": 10}', '', '鱼香', '酸甜微辣，经典川菜', '🥩'),
        ('麻婆豆腐', '热菜', 12.0, 45, 2, '{"cal": 250, "sugar": 3}', '', '麻婆', '麻辣鲜香，嫩滑入味', '🌶️'),
        ('清蒸鲈鱼', '热菜', 28.0, 25, 1, '{"cal": 220, "sugar": 2}', '鱼', '鲈鱼', '清蒸原味，鲜嫩可口', '🐟'),
        # 素菜
        ('番茄炒蛋', '素菜', 10.0, 60, 3, '{"cal": 200, "sugar": 6}', '蛋', '番茄鸡蛋', '酸甜开胃，家常味道', '🍅'),
        ('青椒土豆丝', '素菜', 8.0, 70, 3, '{"cal": 150, "sugar": 4}', '', '土豆', '清脆爽口，下饭神器', '🥔'),
        ('蒜蓉西兰花', '素菜', 9.0, 50, 3, '{"cal": 120, "sugar": 3}', '', '西兰花', '清淡健康，营养丰富', '🥦'),
        # 主食
        ('米饭', '主食', 2.0, 200, 10, '{"cal": 116, "sugar": 0}', '', '饭', '东北大米，软糯香甜', '🍚'),
        ('馒头', '主食', 1.5, 150, 10, '{"cal": 100, "sugar": 1}', '', '馍', '手工馒头，松软可口', '🍞'),
        ('炒面', '主食', 12.0, 40, 2, '{"cal": 320, "sugar": 4}', '', '面', '大火爆炒，香气四溢', '🍜'),
        # 汤
        ('紫菜蛋花汤', '汤', 5.0, 80, 5, '{"cal": 80, "sugar": 2}', '蛋', '汤', '清淡鲜美，暖胃佳品', '🍲'),
        ('番茄鸡蛋汤', '汤', 6.0, 60, 5, '{"cal": 90, "sugar": 5}', '蛋', '番茄汤', '酸甜可口，开胃下饭', '🥣'),
    ]
    for name, cat, price, stock, limit, nutrition, allergy, alias, desc, emoji in sample_dishes:
        cursor.execute('''
            INSERT OR IGNORE INTO dishes (name, category, price, remaining, limit_per_person, status, initial_stock, nutrition_info, allergy_tag, alias, description, image_emoji)
            VALUES (?, ?, ?, ?, ?, '上架', ?, ?, ?, ?, ?, ?)
        ''', (name, cat, price, stock, limit, stock, nutrition, allergy, alias, desc, emoji))

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DATABASE_PATH}")


if __name__ == '__main__':
    init_database()
