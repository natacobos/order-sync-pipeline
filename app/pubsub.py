"""A local stand-in for a Pub/Sub subscription. It behaves like the real one in the ways that matter here:

- At-least-once delivery: a message that is not acknowledged (ack) is delivered again later. Calling nack()
  asks for it to be delivered again. Even an acknowledged message is occasionally delivered a second time.
- No ordering: messages can arrive in a different order from the one they were published in.
- Several instances: deliveries are spread across the service's instances, so a message delivered again
  usually goes to a different instance.

The behavior is fixed by a seed, so every run delivers the same messages in the same order.
"""
import json
import random


class Message:
    def __init__(self, message_id, data, delivery_attempt, on_settle):
        self.message_id = message_id
        self.data = data
        self.delivery_attempt = delivery_attempt
        self._on_settle = on_settle
        self._settled = False

    def ack(self):
        """Tell Pub/Sub the message was processed: it is not delivered again (except the occasional repeat)."""
        self._settle("ack")

    def nack(self):
        """Tell Pub/Sub the message was not processed: it is delivered again later."""
        self._settle("nack")

    def _settle(self, outcome):
        if not self._settled:
            self._settled = True
            self._on_settle(self, outcome)


class LocalSubscription:
    def __init__(self, path, seed=13, swap_rate=0.08, repeat_rate=0.06, max_attempts=10):
        with open(path, encoding="utf-8") as f:
            bodies = [line.strip().encode() for line in f if line.strip()]
        self._rng = random.Random(seed)
        self._repeat_rate = repeat_rate
        self._max_attempts = max_attempts
        self._queue = [(f"m-{i:04d}", body, 1) for i, body in enumerate(bodies)]
        for i in range(len(self._queue) - 1):  # some neighbors arrive swapped
            if self._rng.random() < swap_rate:
                self._queue[i], self._queue[i + 1] = self._queue[i + 1], self._queue[i]
        self.stats = {"delivered": 0, "acked": 0, "nacked": 0, "not_settled": 0, "repeated": 0}

    def deliveries(self):
        """Yield messages one by one, the way a push subscription calls the service."""
        while self._queue:
            message_id, body, attempt = self._queue.pop(0)
            message = Message(message_id, body, attempt, self._settled)
            self.stats["delivered"] += 1
            yield message
            if not message._settled:  # the ack deadline passed: delivered again
                self.stats["not_settled"] += 1
                self._again(message)

    def _settled(self, message, outcome):
        if outcome == "ack":
            self.stats["acked"] += 1
            if self._rng.random() < self._repeat_rate:  # Pub/Sub may deliver an acknowledged message again
                self.stats["repeated"] += 1
                self._queue.insert(min(len(self._queue), self._rng.randint(1, 4)),
                                   (message.message_id, message.data, message.delivery_attempt + 1))
        else:
            self.stats["nacked"] += 1
            self._again(message)

    def _again(self, message):
        if message.delivery_attempt < self._max_attempts:
            self._queue.insert(min(len(self._queue), self._rng.randint(3, 8)),
                               (message.message_id, message.data, message.delivery_attempt + 1))


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
