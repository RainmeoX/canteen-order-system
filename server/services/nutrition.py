# -*- coding: utf-8 -*-
"""
营养评估服务 (Nutrition Service)
提供：NRS-2002 简化评分、Harris-Benedict 能量需求、蛋白目标计算。
参考：临床营养管理系统（NRS-2002/MUST）、Harris-Benedict/WHO 公式。
说明：本模块为「本地可跑」的简化实现，正式临床使用须由营养师复核。
"""

import math


def harris_benedict(sex, weight_kg, height_cm, age):
    """基础能量消耗 BEE（kcal/d）。公式取自 Harris-Benedict 修订版。"""
    if not (sex and weight_kg and height_cm and age):
        return None
    if sex == '男':
        bee = 88.362 + 13.397 * weight_kg + 4.799 * height_cm - 5.677 * age
    else:
        bee = 447.593 + 9.247 * weight_kg + 3.098 * height_cm - 4.330 * age
    return round(bee, 0)


def energy_target(sex, weight_kg, height_cm, age, stress=1.2):
    """每日能量需求 = BEE × 应激/活动系数。
    stress: 卧床 1.2 / 轻活动 1.375 / 术后 1.2-1.5 / 重症感染 1.5-2.0"""
    bee = harris_benedict(sex, weight_kg, height_cm, age)
    if bee is None:
        return None
    return round(bee * stress, 0)


def protein_target(weight_kg, case='normal'):
    """每日蛋白目标(g)。常规 0.8-1.0；术后 1.2-1.5；重症 1.5-2.0（kg/d）"""
    factor = {
        'normal': 1.0,
        'post_op': 1.3,
        'severe': 1.8,
    }.get(case, 1.0)
    if not weight_kg:
        return None
    return round(weight_kg * factor, 1)


def nrs2002_screen(weight_loss_pct=None, bmi=None, intake_days=None,
                    severity='mild', age=None):
    """
    NRS-2002 简化筛查（总分 = 营养状态 + 疾病严重度 + 年龄）。
    返回 (score, risk_level)。仅作演示，完整量表须营养师执行。
    """
    # 营养状态评分（取最大信号）
    nut = 0
    if weight_loss_pct is not None:
        nut = 1 if weight_loss_pct < 5 else (2 if weight_loss_pct < 10 else 3)
    elif bmi is not None:
        nut = 1 if bmi < 20.5 else 0
    elif intake_days is not None:
        nut = 1 if intake_days < 3 else (2 if intake_days < 1 else 0)

    # 疾病严重度
    sev = {'mild': 1, 'moderate': 2, 'severe': 3}.get(severity, 1)

    age_score = 1 if (age and age >= 70) else 0
    score = nut + sev + age_score
    risk = '高营养风险' if score >= 3 else ('中等风险' if score >= 1 else '低风险')
    return score, risk
