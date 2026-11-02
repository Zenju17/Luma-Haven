"""Vercel's private queue subscriber, discovered from pyproject.toml."""
import os
from datetime import timedelta
from uuid import UUID
import django
from asgiref.sync import sync_to_async
from vercel.queue import Message, send, subscribe

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.payments.background import TOPIC, poll_once


@subscribe(topic=TOPIC, retry_after=60, max_concurrency=2, max_attempts=64)
async def poll_payment(message: Message[dict[str, object]]):
    attempt_id = str(UUID(str(message.payload['attempt_id'])))
    step = int(message.payload.get('step', 0))
    delay = await sync_to_async(poll_once)(attempt_id)
    if delay is not None:
        await send(TOPIC, {'attempt_id': attempt_id, 'step': step + 1}, delay=delay,
                   retention=timedelta(days=2), idempotency_key=f'payment:{attempt_id}:{step + 1}')
