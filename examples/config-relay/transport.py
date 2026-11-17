class Transport:
    def __init__(self):
        self.online = True
        self.sent = []

    def publish(self, topic, payload):
        if not self.online:
            return False
        self.sent.append((topic, dict(payload)))
        return True
