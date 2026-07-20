# -*- coding: utf-8 -*-
"""
智能食堂预订系统 - 数据库初始化脚本
功能：创建表结构、索引、系统配置及示例菜品数据
支持特性：菜品分类、价格、库存管理、营养信息、过敏标签、订单备注
"""

import sqlite3
import os

# ============ 常量定义 ============

# 数据库文件所在目录
DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 数据库文件完整路径
DATABASE_PATH = os.path.join(DATABASE_DIR, 'canteen.db')


# ============ 核心函数 ============

def init_database():
    """
    初始化数据库：
    1. 创建数据库目录（不存在时）
    2. 连接数据库并启用WAL模式提升并发性能
    3. 创建5张核心数据表
    4. 创建4个索引优化查询
    5. 初始化系统配置参数
    6. 创建默认管理员账户
    7. 插入13道示例菜品数据
    """
    # 创建数据库目录
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    # 连接SQLite数据库，启用WAL模式
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()

    # ============ 用户表 ============
    # 存储用户信息，区分普通用户和管理员
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,        -- 用户唯一标识
            name TEXT NOT NULL DEFAULT '',   -- 姓名
            employee_id TEXT UNIQUE,         -- 工号（唯一）
            role TEXT DEFAULT 'user',        -- 角色：user/admin
            bind_status INTEGER DEFAULT 0,   -- 绑定状态：0未绑定/1已绑定
            violation_count INTEGER DEFAULT 0,  -- 违规次数
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============ 菜品表 ============
    # 存储菜品信息，支持分类、价格、库存、营养标签
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,             -- 菜品名称（唯一）
            category TEXT DEFAULT '热菜',           -- 分类：热菜/素菜/主食/汤
            price REAL DEFAULT 0,                  -- 价格（元）
            remaining INTEGER NOT NULL,            -- 剩余库存
            limit_per_person INTEGER DEFAULT 5,    -- 每人限购数量
            status TEXT DEFAULT '上架',            -- 状态：上架/下架
            initial_stock INTEGER,                 -- 初始库存
            nutrition_info TEXT,                   -- 营养信息JSON
            allergy_tag TEXT,                      -- 过敏标签
            alias TEXT,                           -- 别名（搜索用）
            description TEXT,                      -- 描述
            image_emoji TEXT DEFAULT '🍽️'         -- 图标
        )
    ''')

    # ============ 订单表 ============
    # 存储订单信息，支持批量下单（同一order_no包含多菜品）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT NOT NULL,                -- 订单号（D+日期+序号）
            user_id TEXT NOT NULL,                 -- 下单用户
            dish_name TEXT NOT NULL,               -- 菜品名称
            quantity INTEGER NOT NULL,             -- 数量
            order_time DATETIME NOT NULL,          -- 下单时间
            take_deadline DATETIME NOT NULL,       -- 取餐截止时间
            status TEXT DEFAULT 'pending',         -- 状态：pending/taken/cancelled/overtime
            pickup_code TEXT NOT NULL,             -- 取餐码
            remark TEXT,                           -- 备注
            unit_price REAL DEFAULT 0,             -- 单价
            total_price REAL DEFAULT 0,            -- 小计
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # ============ 系统配置表 ============
    # 存储动态配置参数，支持运行时修改
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,       -- 配置键
            value TEXT NOT NULL,                   -- 配置值
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============ 管理员日志表 ============
    # 记录管理员操作，用于审计追溯
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT NOT NULL,                -- 管理员ID
            action TEXT NOT NULL,                  -- 操作类型
            detail TEXT,                           -- 操作详情
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users (user_id)
        )
    ''')

    # ============ 创建索引 ============
    # 用户订单查询：按用户+日期
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders (user_id, DATE(order_time))')
    # 订单号查询：用于核销、取消
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders (order_no)')
    # 菜品查询：按名称+状态
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dishes_name_status ON dishes (name, status)')
    # 分类查询：按分类+状态
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dishes_category ON dishes (category, status)')

    # ============ 初始配置 ============
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('order_cutoff_time', '10:00')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_start', '11:30')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_end', '12:30')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('canteen_name', '智慧食堂')")

    # ============ 默认管理员 ============
    cursor.execute('INSERT OR IGNORE INTO users (user_id, name, employee_id, role, bind_status) VALUES ("admin", "", "", "admin", 0)')

    # ============ 示例菜品数据 ============
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
            VALUES (?, ?, ?, ?, ?, "上架", ?, ?, ?, ?, ?, ?)
        ''', (name, cat, price, stock, limit, stock, nutrition, allergy, alias, desc, emoji))

    conn.commit()
    conn.close()
    print(f"[OK] 数据库初始化完成: {DATABASE_PATH}")


if __name__ == '__main__':
    init_database()