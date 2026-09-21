import random

_PROXIES = [
    # "http://user:pass@ip:port",
]

def get_random_proxy(gate=None, fallback_to_all=True):
    if not _PROXIES:
        return None
    return {"http": random.choice(_PROXIES), "https": random.choice(_PROXIES)}
