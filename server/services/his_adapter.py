# -*- coding: utf-8 -*-
"""
HIS / EMR 适配层 (Stub)
生产环境应经 HTTP API 对接医院 HIS，实时同步患者主索引与饮食医嘱。
本模块为「本地可跑」的桩实现：用床头码 token 返回模拟患者档案与医嘱，
接口形状与真实对接保持一致，便于后续替换为真实 HTTP 调用。
参考：好伙狮「HIS 深度集成」、戈子科技「医嘱数据无缝对接」。
"""

# 模拟 HIS 患者主索引（真实环境由 HIS 返回）
_HIS_PATIENTS = {
    'QR-END01': {  # 内分泌科 8F 床1
        'patient_id': 'P001', 'name': '张明', 'dept': '内分泌科',
        'diseases': ['2型糖尿病', '高血压'], 'allergies': ['海鲜'],
        'diet_type': 'diabetic', 'height_cm': 170, 'weight_kg': 78,
        'age': 56, 'sex': '男',
    },
    'QR-CAR03': {  # 心内科 9F 床3
        'patient_id': 'P002', 'name': '李秀', 'dept': '心内科',
        'diseases': ['冠心病', '高血压'], 'allergies': [],
        'diet_type': 'low_salt', 'height_cm': 158, 'weight_kg': 64,
        'age': 63, 'sex': '女',
    },
    'QR-SUR02': {  # 普外 7F 床2
        'patient_id': 'P003', 'name': '王强', 'dept': '普外科',
        'diseases': ['阑尾术后'], 'allergies': [],
        'diet_type': 'liquid', 'height_cm': 175, 'weight_kg': 70,
        'age': 41, 'sex': '男',
    },
    'QR-REN05': {  # 肾内科 10F 床5
        'patient_id': 'P004', 'name': '赵丽', 'dept': '肾内科',
        'diseases': ['慢性肾病'], 'allergies': ['青霉素'],
        'diet_type': 'renal_low_protein', 'height_cm': 162, 'weight_kg': 58,
        'age': 49, 'sex': '女',
    },
}


def fetch_patient_by_bed_token(bed_qr_token):
    """
    按床头码 token 获取患者档案 + 饮食医嘱。
    返回 dict 或 None（token 无效）。
    """
    return _HIS_PATIENTS.get(bed_qr_token)


def fetch_patient_by_id(patient_id):
    for p in _HIS_PATIENTS.values():
        if p['patient_id'] == patient_id:
            return p
    return None
