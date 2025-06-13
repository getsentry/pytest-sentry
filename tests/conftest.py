import pytest_sentry
from sentry_sdk.transport import Transport


class MyTransport(Transport):
    def __init__(self):
        self.events = []
        self.transactions = []
        super().__init__()

    def capture_event(self, event):
        self.events.append(event)
        return event

    def capture_envelope(self, envelope):
        if envelope.get_event() is not None:
            self.events.append(envelope.get_event())

        if envelope.get_transaction_event() is not None:
            self.transactions.append(envelope.get_transaction_event())

        return envelope

    def flush(self, timeout, callback=None):
        pass

    def kill(self):
        pass


# Global test variables
GLOBAL_TRANSPORT = MyTransport()
GLOBAL_CLIENT = pytest_sentry.Client(transport=GLOBAL_TRANSPORT)
