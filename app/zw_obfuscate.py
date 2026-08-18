
import random


ZW_CHARS = '\u200b\u200c\u200d'


def has_zero_width(text):
    
    return bool(text) and any(c in text for c in ZW_CHARS)


def ensure_zero_width(text, rng=None):
    
    if not text or has_zero_width(text):
        return text
    rng = rng or random
    return ''.join(
        ch + ''.join(rng.choice(ZW_CHARS) for _ in range(rng.randint(1, 3)))
        for ch in text
    )
