from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
import re
import random
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

DATABASE_PATH = os.environ.get('CANTEEN_DB_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'canteen.db'))

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

def get_config(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM system_config WHERE config_key = ?', (key,))
    row = cursor.fetchone()
    return row['value'] if row else None

def log_admin_action(admin_id, action, detail):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO admin_logs (admin_id, action, detail) VALUES (?, ?, ?)', 
                   (admin_id, action, detail))
    conn.commit()

@app.route('/api/bind', methods=['POST'])
def bind_user():
    data = request.get_json()
    user_id = data.get('user_id')
    name = data.get('name')
    employee_id = data.get('employee_id')
    
    if not user_id or not name or not employee_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('UPDATE users SET name = ?, employee_id = ?, bind_status = 1 WHERE user_id = ?',
                          (name, employee_id, user_id))
        else:
            cursor.execute('INSERT INTO users (user_id, name, employee_id, bind_status) VALUES (?, ?, ?, 1)',
                          (user_id, name, employee_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'绑定成功！欢迎 {name}'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '该工号已被绑定'}), 409
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/menu', methods=['GET'])
def get_menu():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, remaining, limit_per_person, nutrition_info, allergy_tag FROM dishes WHERE status = "上架"')
    dishes = []
    for row in cursor.fetchall():
        dish = {
            'name': row['name'],
            'remaining': row['remaining'],
            'limit_per_person': row['limit_per_person'],
            'nutrition_info': row['nutrition_info'],
            'allergy_tag': row['allergy_tag']
        }
        dishes.append(dish)
    return jsonify({'success': True, 'data': dishes})

@app.route('/api/search_dish', methods=['GET'])
def search_dish():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM dishes WHERE name = ? AND status = "上架"', (keyword,))
    exact_match = cursor.fetchone()
    
    if exact_match:
        return jsonify({'success': True, 'type': 'exact', 'dish': exact_match['name']})
    
    cursor.execute('SELECT name FROM dishes WHERE name LIKE ? AND status = "上架"', (f'%{keyword}%',))
    fuzzy_matches = [row['name'] for row in cursor.fetchall()]
    
    if len(fuzzy_matches) == 0:
        return jsonify({'success': False, 'message': f'❌ "{keyword}" 今日未供应，请发送"菜单"查看今日菜品'})
    elif len(fuzzy_matches) >= 2:
        return jsonify({'success': True, 'type': 'multiple', 'matches': fuzzy_matches})
    else:
        return jsonify({'success': True, 'type': 'single', 'dish': fuzzy_matches[0]})

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.get_json()
    user_id = data.get('user_id')
    dish_name = data.get('dish_name')
    quantity = data.get('quantity', 1)
    
    if not user_id or not dish_name:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({'success': False, 'message': '数量必须大于0'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user or user['bind_status'] == 0:
        return jsonify({'success': False, 'message': '🔗 您尚未绑定，请发送：绑定 姓名 工号'})
    
    cursor.execute('SELECT * FROM dishes WHERE name = ? AND status = "上架"', (dish_name,))
    dish = cursor.fetchone()
    
    if not dish:
        return jsonify({'success': False, 'message': f'❌ "{dish_name}" 今日未供应或已下架'})
    
    cutoff_time = get_config('order_cutoff_time')
    current_time = datetime.now().strftime('%H:%M')
    
    if current_time > cutoff_time:
        return jsonify({'success': False, 'message': f'⏰ 下单已截止（每日{cutoff_time}），明日请早'})
    
    if dish['remaining'] < quantity:
        return jsonify({'success': False, 'message': f'😅 "{dish_name}" 仅剩 {dish["remaining"]} 份，您要 {quantity} 份，请调整数量'})
    
    cursor.execute('''
        SELECT COALESCE(SUM(quantity), 0) as total 
        FROM orders 
        WHERE user_id = ? AND dish_name = ? AND status = 'pending' AND DATE(order_time) = DATE('now')
    ''', (user_id, dish_name))
    today_ordered = cursor.fetchone()['total']
    
    if today_ordered + quantity > dish['limit_per_person']:
        max_order = dish['limit_per_person'] - today_ordered
        return jsonify({'success': False, 
                       'message': f'🚫 每人限购 {dish["limit_per_person"]} 份，您已订 {today_ordered} 份，最多再订 {max_order} 份'})
    
    try:
        conn.execute('BEGIN')
        
        cursor.execute('''
            UPDATE dishes SET remaining = remaining - ? WHERE name = ? AND remaining >= ?
        ''', (quantity, dish_name, quantity))
        
        if cursor.rowcount == 0:
            raise Exception('库存被抢光')
        
        cursor.execute('SELECT COUNT(*) as count FROM orders WHERE DATE(order_time) = DATE("now")')
        order_count = cursor.fetchone()['count']
        order_id = f"D{datetime.now().strftime('%Y%m%d')}{str(order_count + 1).zfill(4)}"
        
        take_end = get_config('take_end')
        take_deadline = f"{datetime.now().strftime('%Y-%m-%d')} {take_end}"
        
        pickup_code = f"{user['employee_id'][-4:]}+{order_id[-3:]}"
        
        cursor.execute('''
            INSERT INTO orders (id, user_id, dish_name, quantity, order_time, take_deadline, status, pickup_code)
            VALUES (?, ?, ?, ?, datetime('now'), ?, 'pending', ?)
        ''', (order_id, user_id, dish_name, quantity, take_deadline, pickup_code))
        
        conn.commit()
        
        take_start = get_config('take_start')
        
        return jsonify({
            'success': True,
            'message': f'✅ 下单成功！\n您预订了：{dish_name} ×{quantity}\n取餐时间：今日 {take_start}-{take_end}\n取餐地点：食堂一楼大厅\n取餐凭证：{pickup_code}',
            'order_id': order_id,
            'pickup_code': pickup_code,
            'take_time': f'{take_start}-{take_end}'
        })
    
    except Exception as e:
        conn.execute('ROLLBACK')
        return jsonify({'success': False, 'message': f'😅 库存刚刚被抢光，请重新下单'})

@app.route('/api/user_orders', methods=['GET'])
def get_user_orders():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT o.id, o.dish_name, o.quantity, o.order_time, o.take_deadline, o.status, o.pickup_code, u.name
        FROM orders o JOIN users u ON o.user_id = u.user_id
        WHERE o.user_id = ? AND DATE(o.order_time) = DATE('now')
        ORDER BY o.order_time DESC
    ''', (user_id,))
    
    orders = []
    for row in cursor.fetchall():
        orders.append({
            'order_id': row['id'],
            'dish_name': row['dish_name'],
            'quantity': row['quantity'],
            'order_time': row['order_time'],
            'take_deadline': row['take_deadline'],
            'status': row['status'],
            'pickup_code': row['pickup_code']
        })
    
    return jsonify({'success': True, 'data': orders})

@app.route('/api/verify_order', methods=['POST'])
def verify_order():
    data = request.get_json()
    admin_id = data.get('admin_id')
    order_id = data.get('order_id')
    
    if not admin_id or not order_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('SELECT * FROM orders WHERE id = ? AND status = "pending"', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        return jsonify({'success': False, 'message': '订单不存在或已核销'}), 404
    
    cursor.execute('UPDATE orders SET status = "taken" WHERE id = ?', (order_id,))
    conn.commit()
    
    log_admin_action(admin_id, '核销订单', f'订单号: {order_id}, 菜品: {order["dish_name"]}, 数量: {order["quantity"]}')
    
    return jsonify({'success': True, 'message': f'✅ 核销成功！订单 {order_id} 已完成'})

@app.route('/api/admin/add_dish', methods=['POST'])
def add_dish():
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    stock = data.get('stock', 0)
    limit_per_person = data.get('limit_per_person', 5)
    
    if not admin_id or not name:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    try:
        cursor.execute('INSERT INTO dishes (name, remaining, limit_per_person, status, initial_stock) VALUES (?, ?, ?, "上架", ?)',
                      (name, stock, limit_per_person, stock))
        conn.commit()
        
        log_admin_action(admin_id, '上架', f'菜品: {name}, 库存: {stock}, 限购: {limit_per_person}')
        
        return jsonify({'success': True, 'message': f'✅ "{name}" 上架成功'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': f'❌ "{name}" 已存在'}), 409

@app.route('/api/admin/remove_dish', methods=['POST'])
def remove_dish():
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    
    if not admin_id or not name:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('UPDATE dishes SET status = "下架" WHERE name = ?', (name,))
    
    if cursor.rowcount == 0:
        return jsonify({'success': False, 'message': f'❌ "{name}" 不存在或已下架'}), 404
    
    conn.commit()
    
    log_admin_action(admin_id, '下架', f'菜品: {name}')
    
    return jsonify({'success': True, 'message': f'✅ "{name}" 已下架'})

@app.route('/api/admin/update_stock', methods=['POST'])
def update_stock():
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    new_stock = data.get('new_stock')
    
    if not admin_id or not name or new_stock is None:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('SELECT remaining FROM dishes WHERE name = ?', (name,))
    dish = cursor.fetchone()
    
    if not dish:
        return jsonify({'success': False, 'message': f'❌ "{name}" 不存在'}), 404
    
    old_stock = dish['remaining']
    cursor.execute('UPDATE dishes SET remaining = ? WHERE name = ?', (new_stock, name))
    conn.commit()
    
    log_admin_action(admin_id, '改库存', f'菜品: {name}, 原库存: {old_stock}, 新库存: {new_stock}')
    
    return jsonify({'success': True, 'message': f'✅ "{name}" 库存已更新为 {new_stock}'})

@app.route('/api/admin/restock', methods=['POST'])
def restock():
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    amount = data.get('amount')
    
    if not admin_id or not name or amount is None:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('SELECT remaining FROM dishes WHERE name = ?', (name,))
    dish = cursor.fetchone()
    
    if not dish:
        return jsonify({'success': False, 'message': f'❌ "{name}" 不存在'}), 404
    
    old_stock = dish['remaining']
    cursor.execute('UPDATE dishes SET remaining = remaining + ? WHERE name = ?', (amount, name))
    conn.commit()
    
    log_admin_action(admin_id, '补货', f'菜品: {name}, 原库存: {old_stock}, 补货量: {amount}, 新库存: {old_stock + amount}')
    
    return jsonify({'success': True, 'message': f'✅ "{name}" 已补货 {amount} 份'})

@app.route('/api/admin/update_limit', methods=['POST'])
def update_limit():
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    new_limit = data.get('new_limit')
    
    if not admin_id or not name or new_limit is None:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('SELECT limit_per_person FROM dishes WHERE name = ?', (name,))
    dish = cursor.fetchone()
    
    if not dish:
        return jsonify({'success': False, 'message': f'❌ "{name}" 不存在'}), 404
    
    old_limit = dish['limit_per_person']
    cursor.execute('UPDATE dishes SET limit_per_person = ? WHERE name = ?', (new_limit, name))
    conn.commit()
    
    log_admin_action(admin_id, '改限购', f'菜品: {name}, 原限购: {old_limit}, 新限购: {new_limit}')
    
    return jsonify({'success': True, 'message': f'✅ "{name}" 限购已更新为 {new_limit}'})

@app.route('/api/admin/update_cutoff', methods=['POST'])
def update_cutoff():
    data = request.get_json()
    admin_id = data.get('admin_id')
    cutoff_time = data.get('cutoff_time')
    
    if not admin_id or not cutoff_time:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    old_value = get_config('order_cutoff_time')
    cursor.execute('UPDATE system_config SET value = ?, updated_at = datetime("now") WHERE config_key = "order_cutoff_time"',
                  (cutoff_time,))
    conn.commit()
    
    log_admin_action(admin_id, '改截止时间', f'原时间: {old_value}, 新时间: {cutoff_time}')
    
    return jsonify({'success': True, 'message': f'✅ 下单截止时间已更新为 {cutoff_time}'})

@app.route('/api/admin/update_take_time', methods=['POST'])
def update_take_time():
    data = request.get_json()
    admin_id = data.get('admin_id')
    take_start = data.get('take_start')
    take_end = data.get('take_end')
    
    if not admin_id or not take_start or not take_end:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    old_start = get_config('take_start')
    old_end = get_config('take_end')
    
    cursor.execute('UPDATE system_config SET value = ?, updated_at = datetime("now") WHERE config_key = "take_start"',
                  (take_start,))
    cursor.execute('UPDATE system_config SET value = ?, updated_at = datetime("now") WHERE config_key = "take_end"',
                  (take_end,))
    conn.commit()
    
    log_admin_action(admin_id, '改取餐时段', f'原时段: {old_start}-{old_end}, 新时段: {take_start}-{take_end}')
    
    return jsonify({'success': True, 'message': f'✅ 取餐时段已更新为 {take_start}-{take_end}'})

@app.route('/api/admin/cancel_order', methods=['POST'])
def cancel_order():
    data = request.get_json()
    admin_id = data.get('admin_id')
    order_id = data.get('order_id')
    
    if not admin_id or not order_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('SELECT * FROM orders WHERE id = ? AND status = "pending"', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        return jsonify({'success': False, 'message': '订单不存在或已处理'}), 404
    
    cutoff_time = get_config('order_cutoff_time')
    current_time = datetime.now().strftime('%H:%M')
    
    if current_time > cutoff_time:
        return jsonify({'success': False, 'message': '已过截止时间，无法取消'}), 400
    
    try:
        conn.execute('BEGIN')
        
        cursor.execute('UPDATE orders SET status = "cancelled" WHERE id = ?', (order_id,))
        
        cursor.execute('UPDATE dishes SET remaining = remaining + ? WHERE name = ?',
                      (order['quantity'], order['dish_name']))
        
        conn.commit()
        
        log_admin_action(admin_id, '取消订单', f'订单号: {order_id}, 菜品: {order["dish_name"]}, 数量: {order["quantity"]}')
        
        return jsonify({'success': True, 'message': f'✅ 订单 {order_id} 已取消，库存已恢复'})
    except Exception as e:
        conn.execute('ROLLBACK')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
def get_stats():
    admin_id = request.args.get('admin_id')
    
    if not admin_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('SELECT COUNT(*) as total FROM orders WHERE DATE(order_time) = DATE("now")')
    total_orders = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as pending FROM orders WHERE DATE(order_time) = DATE("now") AND status = "pending"')
    pending_orders = cursor.fetchone()['pending']
    
    cursor.execute('SELECT COUNT(*) as taken FROM orders WHERE DATE(order_time) = DATE("now") AND status = "taken"')
    taken_orders = cursor.fetchone()['taken']
    
    cursor.execute('''
        SELECT o.dish_name, SUM(o.quantity) as total_qty 
        FROM orders o 
        WHERE DATE(o.order_time) = DATE("now")
        GROUP BY o.dish_name 
        ORDER BY total_qty DESC 
        LIMIT 5
    ''')
    top_dishes = []
    for row in cursor.fetchall():
        top_dishes.append({'name': row['dish_name'], 'quantity': row['total_qty']})
    
    cursor.execute('SELECT name, remaining FROM dishes WHERE status = "上架" ORDER BY remaining ASC LIMIT 3')
    low_stock = []
    for row in cursor.fetchall():
        low_stock.append({'name': row['name'], 'remaining': row['remaining']})
    
    stats = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'taken_orders': taken_orders,
        'top_dishes': top_dishes,
        'low_stock': low_stock
    }
    
    return jsonify({'success': True, 'data': stats})

@app.route('/api/admin/logs', methods=['GET'])
def get_admin_logs():
    admin_id = request.args.get('admin_id')
    
    if not admin_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
    
    cursor.execute('''
        SELECT a.action, a.detail, a.created_at, u.name
        FROM admin_logs a JOIN users u ON a.admin_id = u.user_id
        ORDER BY a.created_at DESC
        LIMIT 20
    ''')
    
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'action': row['action'],
            'detail': row['detail'],
            'created_at': row['created_at'],
            'admin_name': row['name']
        })
    
    return jsonify({'success': True, 'data': logs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)