import sqlite3
import os

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'canteen.db')

def init_database():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            remaining INTEGER NOT NULL,
            limit_per_person INTEGER DEFAULT 5,
            status TEXT DEFAULT '上架',
            initial_stock INTEGER,
            nutrition_info TEXT,
            allergy_tag TEXT
        )
    ''')
    
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
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders (user_id, DATE(order_time))
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_dishes_name_status ON dishes (name, status)
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('order_cutoff_time', '10:00')
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_start', '11:30')
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO system_config (config_key, value) VALUES ('take_end', '12:30')
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, name, employee_id, role, bind_status) 
        VALUES ('admin_ma', '马静', '0001', 'admin', 1)
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DATABASE_PATH}")

if __name__ == '__main__':
    init_database()