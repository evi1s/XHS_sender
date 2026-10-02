"""零宽字符防检测模块

小红书等平台会对重复/相似营销文案做内容指纹检测与关键词风控。
在文案每个字符后随机插入零宽字符（\u200b 零宽空格、\u200c 零宽非连接符、\u200d 零宽连接符），
视觉上完全不可见、不影响卡片渲染与用户阅读，但字节序列不同，
可绕过重复内容检测与关键词匹配，降低限流/封禁风险。

策略：
- 文本已含零宽字符（模板自带或上次保存）→ 原样保留，不做二次插入
- 文本为纯文本（用户编辑过，零宽字符被覆盖）→ 每字符后随机插入 1-3 个零宽字符
"""
import random

ZW_CHARS = '\u200b\u200c\u200d'


def has_zero_width(text):
    """判断文本是否已含零宽字符。"""
    return bool(text) and any(c in text for c in ZW_CHARS)


def ensure_zero_width(text, rng=None):
    """保留已有零宽字符；纯文本则每字符后随机插入 1-3 个零宽字符。"""
    if not text or has_zero_width(text):
        return text
    rng = rng or random
    return ''.join(
        ch + ''.join(rng.choice(ZW_CHARS) for _ in range(rng.randint(1, 3)))
        for ch in text
    )
