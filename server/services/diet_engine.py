# -*- coding: utf-8 -*-
"""
医嘱规则引擎 (Diet Rule Engine)
核心：根据患者饮食类型(diet_type)，对菜单做刚性过滤 + 推荐标注。
数据来源：diet_rules 表（营养师/系统预设：allow/deny/recommend）。
参考成熟方案：好伙狮「医嘱联动」、hospitalmenu「按医嘱过滤菜单、糖尿病隐藏含糖菜」。
"""

import json


# 饮食类型中文名（用于前端展示与 HIS 映射）
DIET_TYPES = {
    'normal': '普食',
    'diabetic': '糖尿病饮食',
    'low_salt': '低盐低脂',
    'liquid': '流质饮食',
    'renal_low_protein': '肾病低蛋白',
    'low_purine': '低嘌呤',
}


def get_diet_label(diet_type):
    return DIET_TYPES.get(diet_type, diet_type)


def load_rules(conn, diet_type):
    """读取某饮食类型下的所有规则，返回 {allow:set, deny:set, recommend:set}"""
    cursor = conn.cursor()
    cursor.execute(
        'SELECT dish_name, action FROM diet_rules WHERE diet_type = ?', (diet_type,)
    )
    rules = {'allow': set(), 'deny': set(), 'recommend': set()}
    for row in cursor.fetchall():
        if row['action'] in rules:
            rules[row['action']].add(row['dish_name'])
    return rules


def apply_rules_to_menu(conn, diet_type, dishes):
    """
    对菜品列表施加饮食规则：
    - deny 集合：直接过滤掉（源头杜绝误点）
    - recommend 集合：标记 recommended=True（优先展示）
    - 其余：normal 可见但非推荐
    返回带 'recommended' 标记的新列表。
    """
    if not diet_type or diet_type == 'normal':
        for d in dishes:
            d['recommended'] = False
            d['diet_locked'] = False
        return dishes

    rules = load_rules(conn, diet_type)
    out = []
    for d in dishes:
        name = d['name']
        if name in rules['deny']:
            continue  # 刚性拦截：不进入可选菜单
        d['recommended'] = name in rules['recommend']
        d['diet_locked'] = False
        out.append(d)
    return out


def summarize_constraints(diet_type):
    """给前端/营养科一段人类可读的约束说明"""
    text = {
        'diabetic': '严格控制碳水与添加糖，优先低 GI、优质蛋白；含糖点心（红糖馒头/麻薯/双皮奶）不可选。',
        'low_salt': '每日食盐 < 5g，忌腌制、酱卤；多选蒸煮主食与清淡荤素。',
        'liquid': '仅可选流质/半流质（如双皮奶），固体餐食暂不可选，遵医嘱过渡。',
        'renal_low_protein': '限制蛋白质总量，优先优质低蛋白；卤味、皮爪等高蛋白荤菜不可选。',
        'low_purine': '低嘌呤，忌动物内脏、浓肉汤、部分海鲜；卤牛肉/鸡爪暂缓。',
        'normal': '无特殊限制，按需均衡选取。',
    }
    return text.get(diet_type, '')
