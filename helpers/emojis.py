import random
EMOJI_LIST = [
    ':horse:',
    ':dog:',
    ':monkey:',
    ':deer:',
    ':cat:',
    ':rooster:',
    ':eagle:',
    ':lemon:',
    ':ramen:',
    ':cake:',
]

"""
get random emoji from the EMOJI_LIST
"""
def get_random_emoji():
    return random.choice(EMOJI_LIST)
