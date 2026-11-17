from settings import read_limit

class Relay:
    def __init__(self, transport, config):
        self.transport = transport
        self.limit = read_limit(config)
        self.latest = {}
        self.epoch = 0

    def accept(self, payload):
        device, sequence = payload['device'], int(payload['seq'])
        if not device or sequence < 0:
            raise ValueError('invalid event')
        if sequence <= self.latest.get(device, -1):
            return 'duplicate'
        if device not in self.latest and len(self.latest) >= self.limit:
            return 'capacity'
        self.latest[device] = sequence
        self.transport.publish('events', {'device': device, 'seq': sequence, 'epoch': self.epoch})
        return 'accepted'

    def configure(self, config):
        limit = read_limit(config)
        if limit < len(self.latest):
            return False
        self.limit = limit
        self.epoch += 1
        return True

    def disconnect(self, device):
        self.latest.pop(device, None)
