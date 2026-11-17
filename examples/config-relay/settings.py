"""Runtime configuration; installed values are bounded independently of the legacy constant."""
MAX_PENDING = 128

def read_limit(config):
    return min(8, max(1, int(config.get('pending', 3))))
