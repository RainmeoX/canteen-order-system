# -*- coding: utf-8 -*-
"""
智能食堂预订系统 - Flask 后端服务
提供用户端和管理端的 REST API 接口
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime

# ============ 初始化与配置 ============

# 项目根目录 & 客户端目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(PROJECT_ROOT, 'client')

# 数据库路径，优先从环境变量获取，否则使用默认路径
DATABASE_PATH = os.environ.get(
    'CANTEEN_DB_PATH',
    os.path.join(PROJECT_ROOT, 'database', 'canteen.db')
)

# 启动时自动初始化数据库（确保 admin_ma 等基础数据存在）
# 放在 Flask 初始化之前，避免 import 时数据库未就绪
import sys as _sys
_sys.path.insert(0, PROJECT_ROOT)
try:
    from database.init_db import init_database
    init_database()
except Exception as _e:
    print(f'[WARN] 数据库初始化失败: {_e}')

# Flask 初始化时直接指定静态目录，避免运行时修改 static_folder 不生效
app = Flask(__name__, static_folder=CLIENT_DIR, static_url_path='')
CORS(app)

# ============ 数据库操作工具 ============

def get_db():
    """获取数据库连接，使用 Flask 的 g 对象实现请求级连接复用"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
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
        return None, jsonify({'success': False, 'message': '管理员账号不存在', 'need_bind': False}), 403
    if admin['bind_status'] == 0 or not admin['name']:
        return admin, jsonify({'success': False, 'message': '管理员尚未绑定信息', 'need_bind': True}), 403
    return admin, None


# ============ 管理员绑定/信息 API ============

@app.route('/api/admin/bind', methods=['POST'])
def bind_admin():
    """管理员首次绑定：设置姓名和工号"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    employee_id = data.get('employee_id')

    if not admin_id or not name or not employee_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ? AND role = "admin"', (admin_id,))
    admin = cursor.fetchone()
    if not admin:
        return jsonify({'success': False, 'message': '管理员账号不存在'}), 404

    # 检查工号是否已被其他用户占用
    cursor.execute('SELECT user_id FROM users WHERE employee_id = ? AND user_id != ?', (employee_id, admin_id))
    if cursor.fetchone():
        return jsonify({'success': False, 'message': '该工号已被占用'}), 400

    cursor.execute(
        'UPDATE users SET name = ?, employee_id = ?, bind_status = 1 WHERE user_id = ?',
        (name, employee_id, admin_id)
    )
    conn.commit()
    log_admin_action(admin_id, '管理员绑定', f'姓名: {name}, 工号: {employee_id}')
    return jsonify({'success': True, 'message': f'绑定成功！欢迎管理员 {name}'})


@app.route('/api/admin/info', methods=['GET'])
def admin_info():
    """获取管理员信息（是否已绑定、姓名）"""
    admin_id = request.args.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ? AND role = "admin"', (admin_id,))
    admin = cursor.fetchone()
    if not admin:
        return jsonify({'success': False, 'message': '管理员账号不存在', 'need_bind': False}), 404

    return jsonify({
        'success': True,
        'data': {
            'admin_id': admin['user_id'],
            'name': admin['name'],
            'employee_id': admin['employee_id'],
            'bind_status': admin['bind_status'],
            'need_bind': admin['bind_status'] == 0 or not admin['name']
        }
    })


# ============ 用户端 API ============

@app.route('/api/bind', methods=['POST'])
def bind_user():
    """用户绑定接口：绑定用户ID、姓名和工号"""
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
            # 更新已有用户信息
            cursor.execute(
                'UPDATE users SET name = ?, employee_id = ?, bind_status = 1 WHERE user_id = ?',
                (name, employee_id, user_id)
            )
        else:
            # 插入新用户
            cursor.execute(
                'INSERT INTO users (user_id, name, employee_id, bind_status) VALUES (?, ?, ?, 1)',
                (user_id, name, employee_id)
            )

        conn.commit()
        return jsonify({'success': True, 'message': f'绑定成功！欢迎 {name}'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '该工号已被绑定'}), 409
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/menu', methods=['GET'])
def get_menu():
    """获取今日菜单：返回所有上架状态的菜品，支持按分类筛选"""
    category = request.args.get('category')
    conn = get_db()
    cursor = conn.cursor()
    if category and category != '全部':
        cursor.execute(
            'SELECT name, category, price, remaining, limit_per_person, nutrition_info, allergy_tag, alias, description, image_emoji FROM dishes WHERE status = "上架" AND category = ? ORDER BY category, name',
            (category,)
        )
    else:
        cursor.execute(
            'SELECT name, category, price, remaining, limit_per_person, nutrition_info, allergy_tag, alias, description, image_emoji FROM dishes WHERE status = "上架" ORDER BY category, name'
        )
    dishes = []
    for row in cursor.fetchall():
        dishes.append({
            'name': row['name'],
            'category': row['category'],
            'price': row['price'],
            'remaining': row['remaining'],
            'limit_per_person': row['limit_per_person'],
            'nutrition_info': row['nutrition_info'],
            'allergy_tag': row['allergy_tag'],
            'alias': row['alias'],
            'description': row['description'],
            'image_emoji': row['image_emoji']
        })
    return jsonify({'success': True, 'data': dishes})


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有菜品分类"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM dishes WHERE status = "上架" ORDER BY category')
    cats = [row['category'] for row in cursor.fetchall()]
    return jsonify({'success': True, 'data': cats})


@app.route('/api/search_dish', methods=['GET'])
def search_dish():
    """菜品搜索：支持精确匹配和模糊匹配（名称、别名）"""
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 先尝试精确匹配
    cursor.execute('SELECT name FROM dishes WHERE name = ? AND status = "上架"', (keyword,))
    exact_match = cursor.fetchone()

    if exact_match:
        return jsonify({'success': True, 'type': 'exact', 'dish': exact_match['name']})

    # 模糊匹配（名称或别名）
    cursor.execute(
        'SELECT name FROM dishes WHERE (name LIKE ? OR alias LIKE ?) AND status = "上架"',
        (f'%{keyword}%', f'%{keyword}%')
    )
    fuzzy_matches = [row['name'] for row in cursor.fetchall()]

    if len(fuzzy_matches) == 0:
        return jsonify({'success': False, 'message': f'❌ "{keyword}" 今日未供应，请发送"菜单"查看今日菜品'})
    elif len(fuzzy_matches) >= 2:
        return jsonify({'success': True, 'type': 'multiple', 'matches': fuzzy_matches})
    else:
        return jsonify({'success': True, 'type': 'single', 'dish': fuzzy_matches[0]})


@app.route('/api/order', methods=['POST'])
def place_order():
    """下单接口：创建订单，扣减库存，生成取餐码"""
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

    # 验证用户已绑定
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user or user['bind_status'] == 0:
        return jsonify({'success': False, 'message': ' 您尚未绑定，请发送：绑定 姓名 工号'})

    # 验证菜品存在且上架
    cursor.execute('SELECT * FROM dishes WHERE name = ? AND status = "上架"', (dish_name,))
    dish = cursor.fetchone()
    if not dish:
        return jsonify({'success': False, 'message': f'❌ "{dish_name}" 今日未供应或已下架'})

    # 验证下单截止时间
    cutoff_time = get_config('order_cutoff_time')
    current_time = datetime.now().strftime('%H:%M')
    if current_time > cutoff_time:
        return jsonify({'success': False, 'message': f'⏰ 下单已截止（每日{cutoff_time}），明日请早'})

    # 验证库存充足
    if dish['remaining'] < quantity:
        return jsonify({'success': False, 'message': f' "{dish_name}" 仅剩 {dish["remaining"]} 份，您要 {quantity} 份，请调整数量'})

    # 验证限购
    cursor.execute('''
        SELECT COALESCE(SUM(quantity), 0) as total
        FROM orders
        WHERE user_id = ? AND dish_name = ? AND status = 'pending' AND DATE(order_time) = DATE('now')
    ''', (user_id, dish_name))
    today_ordered = cursor.fetchone()['total']

    if today_ordered + quantity > dish['limit_per_person']:
        max_order = dish['limit_per_person'] - today_ordered
        return jsonify({'success': False,
                       'message': f' 每人限购 {dish["limit_per_person"]} 份，您已订 {today_ordered} 份，最多再订 {max_order} 份'})

    try:
        conn.execute('BEGIN')

        # 扣减库存
        cursor.execute('''
            UPDATE dishes SET remaining = remaining - ? WHERE name = ? AND remaining >= ?
        ''', (quantity, dish_name, quantity))

        if cursor.rowcount == 0:
            raise Exception('库存被抢光')

        # 生成订单号（同一批次下单共用一个订单号）
        cursor.execute('SELECT COUNT(DISTINCT order_no) as count FROM orders WHERE DATE(order_time) = DATE("now")')
        order_count = cursor.fetchone()['count']
        order_no = f"D{datetime.now().strftime('%Y%m%d')}{str(order_count + 1).zfill(4)}"

        # 设置取餐截止时间
        take_end = get_config('take_end')
        take_deadline = f"{datetime.now().strftime('%Y-%m-%d')} {take_end}"

        # 生成取餐码
        pickup_code = f"{user['employee_id'][-4:]}+{order_no[-3:]}"

        # 插入订单记录
        cursor.execute('''
            INSERT INTO orders (order_no, user_id, dish_name, quantity, order_time, take_deadline, status, pickup_code, unit_price, total_price)
            VALUES (?, ?, ?, ?, datetime('now'), ?, 'pending', ?, ?, ?)
        ''', (order_no, user_id, dish_name, quantity, take_deadline, pickup_code, dish['price'], dish['price'] * quantity))

        conn.commit()

        take_start = get_config('take_start')

        return jsonify({
            'success': True,
            'message': f'✅ 下单成功！\n您预订了：{dish_name} ×{quantity}\n取餐时间：今日 {take_start}-{take_end}\n取餐地点：食堂一楼大厅\n取餐凭证：{pickup_code}',
            'order_id': order_no,
            'order_no': order_no,
            'pickup_code': pickup_code,
            'take_time': f'{take_start}-{take_end}'
        })

    except Exception as e:
        conn.execute('ROLLBACK')
        return jsonify({'success': False, 'message': f' 库存刚刚被抢光，请重新下单'})


@app.route('/api/order_batch', methods=['POST'])
def order_batch():
    """批量下单（购物车）：一次提交多个菜品"""
    data = request.get_json()
    user_id = data.get('user_id')
    items = data.get('items', [])  # [{dish_name, quantity}, ...]
    remark = data.get('remark', '')

    if not user_id or not items:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证用户
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user or user['bind_status'] == 0:
        return jsonify({'success': False, 'message': '您尚未登录'})

    # 验证截止时间
    cutoff_time = get_config('order_cutoff_time')
    current_time = datetime.now().strftime('%H:%M')
    if current_time > cutoff_time:
        return jsonify({'success': False, 'message': f'下单已截止（每日{cutoff_time}）'})

    try:
        conn.execute('BEGIN')
        total_price = 0
        take_end = get_config('take_end')
        take_start = get_config('take_start')
        take_deadline = f"{datetime.now().strftime('%Y-%m-%d')} {take_end}"

        # 同一批次下单共用一个订单号
        cursor.execute('SELECT COUNT(DISTINCT order_no) as count FROM orders WHERE DATE(order_time) = DATE("now")')
        order_count = cursor.fetchone()['count']
        order_no = f"D{datetime.now().strftime('%Y%m%d')}{str(order_count + 1).zfill(4)}"
        pickup_code = f"{user['employee_id'][-4:]}+{order_no[-3:]}"

        for item in items:
            dish_name = item.get('dish_name')
            quantity = item.get('quantity', 1)
            if quantity <= 0:
                continue

            cursor.execute('SELECT * FROM dishes WHERE name = ? AND status = "上架"', (dish_name,))
            dish = cursor.fetchone()
            if not dish:
                raise Exception(f'"{dish_name}" 未供应')

            if dish['remaining'] < quantity:
                raise Exception(f'"{dish_name}" 仅剩 {dish["remaining"]} 份')

            # 限购检查
            cursor.execute('''
                SELECT COALESCE(SUM(quantity), 0) as total FROM orders
                WHERE user_id = ? AND dish_name = ? AND status = 'pending' AND DATE(order_time) = DATE('now')
            ''', (user_id, dish_name))
            today_ordered = cursor.fetchone()['total']
            if today_ordered + quantity > dish['limit_per_person']:
                raise Exception(f'"{dish_name}" 每人限购 {dish["limit_per_person"]} 份')

            # 扣库存
            cursor.execute('UPDATE dishes SET remaining = remaining - ? WHERE name = ? AND remaining >= ?',
                          (quantity, dish_name, quantity))
            if cursor.rowcount == 0:
                raise Exception(f'"{dish_name}" 库存被抢光')

            # 插入订单记录（共用同一个 order_no）
            cursor.execute('''
                INSERT INTO orders (order_no, user_id, dish_name, quantity, order_time, take_deadline, status, pickup_code, remark, unit_price, total_price)
                VALUES (?, ?, ?, ?, datetime('now'), ?, 'pending', ?, ?, ?, ?)
            ''', (order_no, user_id, dish_name, quantity, take_deadline, pickup_code, remark, dish['price'], dish['price'] * quantity))

            total_price += dish['price'] * quantity

        conn.commit()
        return jsonify({
            'success': True,
            'message': f'下单成功！订单号 {order_no}，合计 ¥{total_price:.2f}',
            'order_id': order_no,
            'order_no': order_no,
            'order_ids': [order_no],
            'total_price': total_price,
            'pickup_code': pickup_code,
            'take_time': f'{take_start}-{take_end}'
        })
    except Exception as e:
        conn.execute('ROLLBACK')
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/user_orders', methods=['GET'])
def get_user_orders():
    """查询用户今日订单（按 order_no 分组）"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT o.order_no, o.dish_name, o.quantity, o.order_time, o.take_deadline,
               o.status, o.pickup_code, o.total_price, o.remark, o.unit_price, u.name
        FROM orders o JOIN users u ON o.user_id = u.user_id
        WHERE o.user_id = ? AND DATE(o.order_time) = DATE('now')
        ORDER BY o.order_time DESC
    ''', (user_id,))

    # 按 order_no 分组
    grouped = {}
    for row in cursor.fetchall():
        no = row['order_no']
        if no not in grouped:
            grouped[no] = {
                'order_id': no,
                'order_no': no,
                'items': [],
                'order_time': row['order_time'],
                'take_deadline': row['take_deadline'],
                'status': row['status'],
                'pickup_code': row['pickup_code'],
                'remark': row['remark'],
                'total_price': 0,
                'user_name': row['name']
            }
        grouped[no]['items'].append({
            'dish_name': row['dish_name'],
            'quantity': row['quantity'],
            'unit_price': row['unit_price'],
            'subtotal': row['total_price']
        })
        grouped[no]['total_price'] += row['total_price']

    return jsonify({'success': True, 'data': list(grouped.values())})


@app.route('/api/user_orders/history', methods=['GET'])
def get_user_order_history():
    """查询用户历史订单（按 order_no 分组，支持日期范围筛选）"""
    user_id = request.args.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not user_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    query = '''
        SELECT o.order_no, o.dish_name, o.quantity, o.order_time, o.take_deadline,
               o.status, o.pickup_code, o.total_price, o.remark, o.unit_price
        FROM orders o
        WHERE o.user_id = ?
    '''
    params = [user_id]

    if start_date:
        query += ' AND DATE(o.order_time) >= ?'
        params.append(start_date)

    if end_date:
        query += ' AND DATE(o.order_time) <= ?'
        params.append(end_date)

    query += ' ORDER BY o.order_time DESC LIMIT 200'

    cursor.execute(query, params)

    # 按 order_no 分组
    grouped = {}
    order_seq = []
    for row in cursor.fetchall():
        no = row['order_no']
        if no not in grouped:
            grouped[no] = {
                'order_id': no,
                'order_no': no,
                'items': [],
                'order_time': row['order_time'],
                'take_deadline': row['take_deadline'],
                'status': row['status'],
                'pickup_code': row['pickup_code'],
                'remark': row['remark'],
                'total_price': 0
            }
            order_seq.append(no)
        grouped[no]['items'].append({
            'dish_name': row['dish_name'],
            'quantity': row['quantity'],
            'unit_price': row['unit_price'],
            'subtotal': row['total_price']
        })
        grouped[no]['total_price'] += row['total_price']

    return jsonify({'success': True, 'data': [grouped[no] for no in order_seq]})


@app.route('/api/dietary_suggestion', methods=['GET'])
def get_dietary_suggestion():
    """获取饮食建议：基于今日订单统计热量和糖分，给出健康建议"""
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT d.nutrition_info, d.allergy_tag, SUM(o.quantity) as total_qty
        FROM orders o JOIN dishes d ON o.dish_name = d.name
        WHERE o.user_id = ? AND DATE(o.order_time) = DATE('now')
        GROUP BY o.dish_name
    ''', (user_id,))

    today_orders = cursor.fetchall()

    suggestions = []
    total_cal = 0
    total_sugar = 0

    for row in today_orders:
        nutrition_info = row['nutrition_info']
        if nutrition_info:
            try:
                nutrition = json.loads(nutrition_info)
                total_cal += nutrition.get('cal', 0) * row['total_qty']
                total_sugar += nutrition.get('sugar', 0) * row['total_qty']
            except:
                pass

    # 生成饮食建议
    if total_cal > 2000:
        suggestions.append('今日热量摄入较高，建议选择清淡菜品')
    elif total_cal < 1000:
        suggestions.append('今日热量摄入偏低，建议适当增加主食')

    if total_sugar > 50:
        suggestions.append('糖分摄入偏高，注意饮食均衡')

    # 随机推荐3个菜品
    cursor.execute('SELECT name, nutrition_info, allergy_tag FROM dishes WHERE status = "上架" ORDER BY RANDOM() LIMIT 3')
    recommendations = []
    for row in cursor.fetchall():
        recommendations.append({
            'name': row['name'],
            'nutrition_info': row['nutrition_info'],
            'allergy_tag': row['allergy_tag']
        })

    return jsonify({
        'success': True,
        'data': {
            'today_calories': total_cal,
            'today_sugar': total_sugar,
            'suggestions': suggestions if suggestions else ['今日饮食搭配合理'],
            'recommendations': recommendations
        }
    })

# ============ 管理端 API ============

@app.route('/api/verify_order', methods=['POST'])
def verify_order():
    """订单核销：管理员验证用户订单，标记为已取餐"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    order_id = data.get('order_id')

    if not admin_id or not order_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    # 验证订单存在且待取餐（按 order_no 核销整个订单的所有菜品）
    cursor.execute('SELECT * FROM orders WHERE order_no = ? AND status = "pending"', (order_id,))
    orders = cursor.fetchall()
    if not orders:
        return jsonify({'success': False, 'message': '订单不存在或已核销'}), 404

    # 更新该订单号下所有菜品的状态
    cursor.execute('UPDATE orders SET status = "taken" WHERE order_no = ? AND status = "pending"', (order_id,))
    conn.commit()

    dish_summary = '、'.join([f'{o["dish_name"]}×{o["quantity"]}' for o in orders])
    log_admin_action(admin_id, '核销订单', f'订单号: {order_id}, 菜品: {dish_summary}')

    return jsonify({'success': True, 'message': f'✅ 核销成功！订单 {order_id} 已完成（共 {len(orders)} 个菜品）'})


@app.route('/api/admin/add_dish', methods=['POST'])
def add_dish():
    """上架新菜品"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    category = data.get('category', '热菜')
    price = data.get('price', 0)
    stock = data.get('stock', 0)
    limit_per_person = data.get('limit_per_person', 5)
    nutrition_info = data.get('nutrition_info')
    allergy_tag = data.get('allergy_tag')
    alias = data.get('alias')
    description = data.get('description', '')
    image_emoji = data.get('image_emoji', '🍽️')

    if not admin_id or not name:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    try:
        cursor.execute(
            'INSERT INTO dishes (name, category, price, remaining, limit_per_person, status, initial_stock, nutrition_info, allergy_tag, alias, description, image_emoji) VALUES (?, ?, ?, ?, ?, "上架", ?, ?, ?, ?, ?, ?)',
            (name, category, price, stock, limit_per_person, stock, nutrition_info, allergy_tag, alias, description, image_emoji)
        )
        conn.commit()

        log_admin_action(admin_id, '上架', f'菜品: {name}, 分类: {category}, 价格: ¥{price}, 库存: {stock}')

        return jsonify({'success': True, 'message': f'"{name}" 上架成功'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': f'"{name}" 已存在'}), 409


@app.route('/api/admin/remove_dish', methods=['POST'])
def remove_dish():
    """下架菜品"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')

    if not admin_id or not name:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
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
    """修改菜品库存"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    new_stock = data.get('new_stock')

    if not admin_id or not name or new_stock is None:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    # 验证菜品存在
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
    """菜品补货：在现有库存基础上增加数量"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    amount = data.get('amount')

    if not admin_id or not name or amount is None:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    # 验证菜品存在
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
    """修改菜品限购数量"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    name = data.get('name')
    new_limit = data.get('new_limit')

    if not admin_id or not name or new_limit is None:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    # 验证菜品存在
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
    """修改下单截止时间"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    cutoff_time = data.get('cutoff_time')

    if not admin_id or not cutoff_time:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    old_value = get_config('order_cutoff_time')
    cursor.execute(
        'UPDATE system_config SET value = ?, updated_at = datetime("now") WHERE config_key = "order_cutoff_time"',
        (cutoff_time,)
    )
    conn.commit()

    log_admin_action(admin_id, '改截止时间', f'原时间: {old_value}, 新时间: {cutoff_time}')

    return jsonify({'success': True, 'message': f'✅ 下单截止时间已更新为 {cutoff_time}'})


@app.route('/api/admin/update_take_time', methods=['POST'])
def update_take_time():
    """修改取餐时段"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    take_start = data.get('take_start')
    take_end = data.get('take_end')

    if not admin_id or not take_start or not take_end:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    old_start = get_config('take_start')
    old_end = get_config('take_end')

    cursor.execute(
        'UPDATE system_config SET value = ?, updated_at = datetime("now") WHERE config_key = "take_start"',
        (take_start,)
    )
    cursor.execute(
        'UPDATE system_config SET value = ?, updated_at = datetime("now") WHERE config_key = "take_end"',
        (take_end,)
    )
    conn.commit()

    log_admin_action(admin_id, '改取餐时段', f'原时段: {old_start}-{old_end}, 新时段: {take_start}-{take_end}')

    return jsonify({'success': True, 'message': f'✅ 取餐时段已更新为 {take_start}-{take_end}'})


@app.route('/api/admin/cancel_order', methods=['POST'])
def cancel_order():
    """取消订单：恢复库存（仅截止时间前可取消）"""
    data = request.get_json()
    admin_id = data.get('admin_id')
    order_id = data.get('order_id')

    if not admin_id or not order_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    # 验证订单存在且待处理（按 order_no 取消整个订单的所有菜品）
    cursor.execute('SELECT * FROM orders WHERE order_no = ? AND status = "pending"', (order_id,))
    orders = cursor.fetchall()
    if not orders:
        return jsonify({'success': False, 'message': '订单不存在或已处理'}), 404

    # 验证未过截止时间
    cutoff_time = get_config('order_cutoff_time')
    current_time = datetime.now().strftime('%H:%M')
    if current_time > cutoff_time:
        return jsonify({'success': False, 'message': '已过截止时间，无法取消'}), 400

    try:
        conn.execute('BEGIN')

        # 更新该订单号下所有菜品状态为已取消
        cursor.execute('UPDATE orders SET status = "cancelled" WHERE order_no = ? AND status = "pending"', (order_id,))

        # 恢复每个菜品的库存
        for order in orders:
            cursor.execute('UPDATE dishes SET remaining = remaining + ? WHERE name = ?',
                          (order['quantity'], order['dish_name']))

        conn.commit()

        dish_summary = '、'.join([f'{o["dish_name"]}×{o["quantity"]}' for o in orders])
        log_admin_action(admin_id, '取消订单', f'订单号: {order_id}, 菜品: {dish_summary}')

        return jsonify({'success': True, 'message': f'✅ 订单 {order_id} 已取消，库存已恢复（共 {len(orders)} 个菜品）'})
    except Exception as e:
        conn.execute('ROLLBACK')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/stats', methods=['GET'])
def get_stats():
    """今日数据统计：订单数、热销菜品、低库存预警"""
    admin_id = request.args.get('admin_id')

    if not admin_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    # 今日订单总数（按 order_no 去重统计）
    cursor.execute('SELECT COUNT(DISTINCT order_no) as total FROM orders WHERE DATE(order_time) = DATE("now")')
    total_orders = cursor.fetchone()['total']

    # 待取餐订单数（按 order_no 去重统计）
    cursor.execute('SELECT COUNT(DISTINCT order_no) as cnt FROM orders WHERE DATE(order_time) = DATE("now") AND status = "pending"')
    pending_orders = cursor.fetchone()['cnt']

    # 已取餐订单数（按 order_no 去重统计）
    cursor.execute('SELECT COUNT(DISTINCT order_no) as cnt FROM orders WHERE DATE(order_time) = DATE("now") AND status = "taken"')
    taken_orders = cursor.fetchone()['cnt']

    # 今日营业额（已取餐 + 待取餐，不含取消和超时）
    cursor.execute('SELECT COALESCE(SUM(total_price), 0) as revenue FROM orders WHERE DATE(order_time) = DATE("now") AND status IN ("pending", "taken")')
    today_revenue = cursor.fetchone()['revenue']

    # 热销菜品TOP5
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

    # 低库存预警（剩余最少的3个）
    cursor.execute('SELECT name, remaining FROM dishes WHERE status = "上架" ORDER BY remaining ASC LIMIT 3')
    low_stock = []
    for row in cursor.fetchall():
        low_stock.append({'name': row['name'], 'remaining': row['remaining']})

    stats = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'taken_orders': taken_orders,
        'today_revenue': round(today_revenue, 2),
        'top_dishes': top_dishes,
        'low_stock': low_stock
    }

    return jsonify({'success': True, 'data': stats})


@app.route('/api/admin/orders', methods=['GET'])
def get_all_orders():
    """获取今日所有订单（支持按状态筛选）"""
    admin_id = request.args.get('admin_id')
    status = request.args.get('status')

    if not admin_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin['role'] != 'admin':
        return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    query = '''
        SELECT o.order_no, o.user_id, o.dish_name, o.quantity, o.order_time, o.take_deadline,
               o.status, o.pickup_code, o.total_price, o.remark, o.unit_price,
               u.name as user_name, u.employee_id
        FROM orders o JOIN users u ON o.user_id = u.user_id
        WHERE DATE(o.order_time) = DATE('now')
    '''
    params = []

    if status:
        query += ' AND o.status = ?'
        params.append(status)

    query += ' ORDER BY o.order_time DESC'

    cursor.execute(query, params)

    # 按 order_no 分组
    grouped = {}
    order_seq = []
    for row in cursor.fetchall():
        no = row['order_no']
        if no not in grouped:
            grouped[no] = {
                'order_id': no,
                'order_no': no,
                'user_id': row['user_id'],
                'user_name': row['user_name'],
                'employee_id': row['employee_id'],
                'items': [],
                'order_time': row['order_time'],
                'take_deadline': row['take_deadline'],
                'status': row['status'],
                'pickup_code': row['pickup_code'],
                'remark': row['remark'],
                'total_price': 0
            }
            order_seq.append(no)
        grouped[no]['items'].append({
            'dish_name': row['dish_name'],
            'quantity': row['quantity'],
            'unit_price': row['unit_price'],
            'subtotal': row['total_price']
        })
        grouped[no]['total_price'] += row['total_price']

    return jsonify({'success': True, 'data': [grouped[no] for no in order_seq]})


@app.route('/api/admin/logs', methods=['GET'])
def get_admin_logs():
    """获取管理员操作日志（最近20条）"""
    admin_id = request.args.get('admin_id')

    if not admin_id:
        return jsonify({'success': False, 'message': '缺少参数'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 验证管理员权限
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


@app.route('/api/process_overtime', methods=['POST'])
def process_overtime_orders():
    """处理超时订单：标记超时，恢复库存"""
    data = request.get_json()
    admin_id = data.get('admin_id')

    if admin_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE user_id = ?', (admin_id,))
        admin = cursor.fetchone()
        if not admin or admin['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限执行此操作'}), 403

    conn = get_db()
    cursor = conn.cursor()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 查询超时订单
    cursor.execute('SELECT * FROM orders WHERE status = "pending" AND take_deadline < ?', (current_time,))
    overtime_orders = cursor.fetchall()

    if len(overtime_orders) == 0:
        return jsonify({'success': True, 'message': '暂无超时订单'})

    try:
        conn.execute('BEGIN')

        # 按 order_no 分组处理，统计订单数
        order_nos = set()
        for order in overtime_orders:
            # 标记为超时
            cursor.execute('UPDATE orders SET status = "overtime" WHERE id = ?', (order['id'],))
            # 恢复库存
            cursor.execute('UPDATE dishes SET remaining = remaining + ? WHERE name = ?',
                          (order['quantity'], order['dish_name']))
            order_nos.add(order['order_no'])

        conn.commit()

        return jsonify({'success': True, 'message': f'已处理 {len(order_nos)} 个超时订单（{len(overtime_orders)} 个菜品），库存已释放'})
    except Exception as e:
        conn.execute('ROLLBACK')
        return jsonify({'success': False, 'message': str(e)}), 500

# ============ 静态资源服务 ============


@app.route('/')
def index():
    """用户端首页"""
    return app.send_static_file('index.html')


@app.route('/admin')
def admin():
    """管理端首页"""
    return app.send_static_file('admin.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)