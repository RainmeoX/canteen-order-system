# -*- coding: utf-8 -*-
"""
智能食堂预订系统 - 数据库初始化脚本 (v2 扩展)
功能：
  1. 保留原有 5 张核心表（users/dishes/orders/system_config/admin_logs）
  2. 新增领域表：wards(病区床位) / patients(患者主索引) /
     diet_charts(膳食处方) / diet_rules(医嘱规则) / deliveries(配送单) /
     nutrition_assess(营养评估)
  3. orders 表扩展字段：fulfillment_mode / patient_id / ward_id / meal_slot / diet_chart_id
  4. 灌入真实数据：8 大品类（大肉包/大馒头/红糖馒头/卤牛肉/柠檬鸡爪/
     凉拌猪耳朵/麻薯/水果双皮奶）+ 病区床位 + 患者档案 + 医嘱规则 + 演示订单
说明：清空 dishes/orders 以载入真实目录（示例数据不再保留）。
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta

# =========== 常量定义 ===========

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'canteen.db')


def init_database():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute("PRAGMA timezone='localtime'")  # 与 Python datetime.now() 本地时区对齐
    cursor = conn.cursor()

    # =========== 原有 5 张核心表（保留） ===========
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT NOT NULL,
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

    # =========== 新增领域表（v2） ===========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept TEXT NOT NULL,          -- 科室
            floor TEXT,                   -- 楼层
            bed_no TEXT,                 -- 床号
            bed_qr_token TEXT UNIQUE     -- 床头码（一床一码）
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,           -- P001
            name TEXT NOT NULL,
            ward_id INTEGER,
            dept TEXT,
            diseases TEXT,                -- JSON 数组
            allergies TEXT,               -- JSON 数组
            diet_type TEXT DEFAULT 'normal',
            height_cm REAL,
            weight_kg REAL,
            age INTEGER,
            sex TEXT,
            energy_target REAL,
            protein_target REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ward_id) REFERENCES wards (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            meal_slot TEXT,               -- 早餐/午餐/晚餐/加餐
            items TEXT,                   -- JSON [{dish_name,qty}]
            note TEXT,
            effective_date TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diet_type TEXT NOT NULL,
            dish_name TEXT NOT NULL,
            action TEXT NOT NULL           -- allow/deny/recommend
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT,
            ward_id INTEGER,
            courier TEXT,
            status TEXT DEFAULT 'ready',  -- ready/dispatching/delivered
            delivered_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ward_id) REFERENCES wards (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nutrition_assess (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            tool TEXT,                   -- NRS2002/MUST
            score REAL,
            risk_level TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    ''')

    # =========== orders 表扩展字段（向后兼容） ===========
    for col, ddl in [
        ('fulfillment_mode', "ALTER TABLE orders ADD COLUMN fulfillment_mode TEXT DEFAULT 'pickup'"),
        ('patient_id', "ALTER TABLE orders ADD COLUMN patient_id TEXT"),
        ('ward_id', "ALTER TABLE orders ADD COLUMN ward_id INTEGER"),
        ('meal_slot', "ALTER TABLE orders ADD COLUMN meal_slot TEXT"),
        ('diet_chart_id', "ALTER TABLE orders ADD COLUMN diet_chart_id INTEGER"),
    ]:
        try:
            cursor.execute(ddl)
        except sqlite3.OperationalError:
            pass  # 字段已存在

    # =========== 索引 ===========
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders (user_id, DATE(order_time))')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders (order_no)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dishes_name_status ON dishes (name, status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dishes_category ON dishes (category, status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_ward ON patients (ward_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries (status)')

    # =========== 初始配置 ===========
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('order_cutoff_time', '10:00')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_start', '11:30')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_end', '12:30')")
    cursor.execute("INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('canteen_name', '省医营养食堂')")

    # =========== 默认管理员 ===========
    cursor.execute('INSERT OR IGNORE INTO users (user_id, name, employee_id, role, bind_status) VALUES ("admin", "", "", "admin", 0)')

    # =========== 灌入真实数据 ===========
    _seed_real_data(conn, cursor)

    conn.commit()
    conn.close()
    print(f"[OK] 数据库初始化完成(v2): {DATABASE_PATH}")


def _seed_real_data(conn, cursor):
    """清空示例、载入真实目录 + 领域数据 + 演示订单"""
    cursor.execute('DELETE FROM orders')
    cursor.execute('DELETE FROM dishes')
    cursor.execute('DELETE FROM deliveries')
    cursor.execute('DELETE FROM diet_rules')
    cursor.execute('DELETE FROM patients')
    cursor.execute('DELETE FROM wards')
    cursor.execute('DELETE FROM diet_charts')
    cursor.execute('DELETE FROM nutrition_assess')
    cursor.execute('DELETE FROM users')  # 清掉历史脏数据（含 employee_id 唯一约束冲突），保证演示账号干净

    # ---- 8 大真实品类 ----
    real_dishes = [
        ('大肉包子', '主食', 3.5, 10, 3, '{"cal":250,"sugar":2,"protein":9,"fat":8}', '', '包子', '皮薄馅大，酱香浓郁', '🥟'),
        ('大馒头',   '主食', 1.5, 10, 5, '{"cal":220,"sugar":1,"protein":7}', '', '馒头', '手工发酵，松软麦香', '🍞'),
        ('红糖馒头', '主食', 1.8, 10, 5, '{"cal":240,"sugar":12,"protein":7}', '', '馒头', '红糖温润，补气暖身', '🍞'),
        ('卤牛肉',   '荤菜', 18.0, 5, 2, '{"cal":180,"sugar":1,"protein":26,"fat":8}', '', '牛肉', '牛腱卤香，优质蛋白', '🥩'),
        ('柠檬鸡爪', '小吃', 12.0, 10, 3, '{"cal":160,"sugar":2,"protein":15}', '', '鸡爪', '柠檬清爽，弹韧开胃', '🍗'),
        ('凉拌猪耳朵', '荤菜', 10.0, 6, 2, '{"cal":200,"sugar":1,"protein":14}', '', '猪耳', '脆爽卤香，佐餐佳品', '🐷'),
        ('麻薯',     '甜品', 6.0, 10, 3, '{"cal":300,"sugar":18,"protein":3}', '', '麻薯', '软糯拉丝，甜而不腻', '🍡'),
        ('水果双皮奶', '甜品', 8.0, 10, 3, '{"cal":150,"sugar":14,"protein":4}', '奶制品', '双皮', '嫩滑奶香，清甜果味', '🍮'),
    ]
    for name, cat, price, stock, limit, nutri, allergy, alias, desc, emoji in real_dishes:
        cursor.execute('''
            INSERT INTO dishes (name, category, price, remaining, limit_per_person, status, initial_stock, nutrition_info, allergy_tag, alias, description, image_emoji)
            VALUES (?, ?, ?, ?, ?, "上架", ?, ?, ?, ?, ?, ?)
        ''', (name, cat, price, stock, limit, stock, nutri, allergy, alias, desc, emoji))

    # ---- 病区 / 床位（一床一码） ----
    wards = [
        ('内分泌科', '8F', '床1', 'QR-END01'),
        ('心内科',   '9F', '床3', 'QR-CAR03'),
        ('普外科',   '7F', '床2', 'QR-SUR02'),
        ('肾内科',   '10F', '床5', 'QR-REN05'),
    ]
    ward_id_map = {}
    for dept, floor, bed, token in wards:
        cursor.execute('INSERT INTO wards (dept, floor, bed_no, bed_qr_token) VALUES (?, ?, ?, ?)',
                     (dept, floor, bed, token))
        cursor.execute('SELECT id FROM wards WHERE bed_qr_token = ?', (token,))
        ward_id_map[token] = cursor.fetchone()[0]

    # ---- 患者主索引（HIS stub 同步） ----
    patients = [
        ('P001', '张明', 'QR-END01', '内分泌科', ['2型糖尿病', '高血压'], ['海鲜'], 'diabetic', 170, 78, 56, '男'),
        ('P002', '李秀', 'QR-CAR03', '心内科',   ['冠心病', '高血压'], [], 'low_salt', 158, 64, 63, '女'),
        ('P003', '王强', 'QR-SUR02', '普外科',   ['阑尾术后'], [], 'liquid', 175, 70, 41, '男'),
        ('P004', '赵丽', 'QR-REN05', '肾内科',   ['慢性肾病'], ['青霉素'], 'renal_low_protein', 162, 58, 49, '女'),
    ]
    for pid, name, token, dept, dis, alg, dtype, h, w, age, sex in patients:
        cursor.execute('''
            INSERT INTO patients (id, name, ward_id, dept, diseases, allergies, diet_type, height_cm, weight_kg, age, sex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pid, name, ward_id_map[token], dept, json.dumps(dis, ensure_ascii=False),
              json.dumps(alg, ensure_ascii=False), dtype, h, w, age, sex))
    # 患者登录账号（床旁点餐用：user_id 直接用患者主索引 ID）
    for pid, name, *_ in patients:
        cursor.execute('INSERT INTO users (user_id, name, employee_id, role, bind_status) VALUES (?, ?, ?, "user", 1)',
                     (pid, name, pid))

    # ---- 医嘱规则引擎数据 ----
    rules = [
        # 糖尿病：拦截高糖，推荐优质蛋白/主食
        ('diabetic', '红糖馒头', 'deny'), ('diabetic', '麻薯', 'deny'), ('diabetic', '水果双皮奶', 'deny'),
        ('diabetic', '卤牛肉', 'recommend'), ('diabetic', '大肉包子', 'recommend'),
        # 低盐低脂：拦截酱卤腌制
        ('low_salt', '卤牛肉', 'deny'), ('low_salt', '凉拌猪耳朵', 'deny'),
        ('low_salt', '大馒头', 'recommend'), ('low_salt', '大肉包子', 'recommend'),
        # 流质：仅可流质，固体拦截
        ('liquid', '大肉包子', 'deny'), ('liquid', '大馒头', 'deny'), ('liquid', '红糖馒头', 'deny'),
        ('liquid', '卤牛肉', 'deny'), ('liquid', '柠檬鸡爪', 'deny'), ('liquid', '凉拌猪耳朵', 'deny'),
        ('liquid', '麻薯', 'deny'), ('liquid', '水果双皮奶', 'recommend'),
        # 肾病低蛋白：拦截高蛋白荤菜
        ('renal_low_protein', '卤牛肉', 'deny'), ('renal_low_protein', '柠檬鸡爪', 'deny'),
        ('renal_low_protein', '凉拌猪耳朵', 'deny'),
        ('renal_low_protein', '大馒头', 'recommend'), ('renal_low_protein', '大肉包子', 'recommend'),
        # 低嘌呤：拦截高嘌呤
        ('low_purine', '卤牛肉', 'deny'), ('low_purine', '柠檬鸡爪', 'deny'),
        ('low_purine', '大馒头', 'recommend'),
    ]
    for dtype, dish, action in rules:
        cursor.execute('INSERT INTO diet_rules (diet_type, dish_name, action) VALUES (?, ?, ?)',
                     (dtype, dish, action))

    # ---- 演示用户 + 历史订单（让"个人订单查询"开箱有数据） ----
    cursor.execute('INSERT OR IGNORE INTO users (user_id, name, employee_id, role, bind_status) VALUES ("U1001", "张三", "1001", "user", 1)')
    today = datetime.now().strftime('%Y-%m-%d')
    yest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    # 今日待取（order_time 用 sqlite 本地时区，避免与 DATE('now','localtime') 比对错位）
    cursor.execute('''
        INSERT INTO orders (order_no, user_id, dish_name, quantity, order_time, take_deadline, status, pickup_code, unit_price, total_price, fulfillment_mode, meal_slot)
        VALUES ('D' || strftime('%Y%m%d','now','localtime') || '0001', "U1001", "卤牛肉", 1, datetime('now','localtime'), ?, "pending", "1001+001", 18.0, 18.0, "pickup", "午餐")
    ''', (today + ' 12:30',))
    cursor.execute('''
        INSERT INTO orders (order_no, user_id, dish_name, quantity, order_time, take_deadline, status, pickup_code, unit_price, total_price, fulfillment_mode, meal_slot)
        VALUES ('D' || strftime('%Y%m%d','now','localtime') || '0001', "U1001", "水果双皮奶", 1, datetime('now','localtime'), ?, "pending", "1001+001", 8.0, 8.0, "pickup", "午餐")
    ''', (today + ' 12:30',))
    # 昨日已取
    cursor.execute('''
        INSERT INTO orders (order_no, user_id, dish_name, quantity, order_time, take_deadline, status, pickup_code, unit_price, total_price, fulfillment_mode, meal_slot)
        VALUES ('D' || strftime('%Y%m%d','now','-1 day','localtime') || '0001', "U1001", "大肉包子", 2, datetime('now','-1 day','localtime'), ?, "taken", "1001+001", 3.5, 7.0, "pickup", "午餐")
    ''', (yest + ' 12:30',))


if __name__ == '__main__':
    init_database()
