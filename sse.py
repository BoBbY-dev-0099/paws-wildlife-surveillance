import asyncio
import json
from typing import AsyncGenerator


class SSEManager:
    def __init__(self):
        self._queues: list[asyncio.Queue] = []
        self._loop = None

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._queues.append(q)
        # Capture the running event loop for thread-safe publishing
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._queues:
            self._queues.remove(q)

    def publish(self, data: dict):
        """Thread-safe publish — works from background threads AND the main asyncio thread."""
        message = json.dumps(data)
        print(f"[SSE] Publishing: {data.get('step', 'unknown')} - {data.get('message', '')[:50]}")
        print(f"[SSE] Active queues: {len(self._queues)}")
        dead = []
        for q in self._queues:
            try:
                # Check if we're in the same thread as the event loop
                try:
                    running_loop = asyncio.get_running_loop()
                except RuntimeError:
                    running_loop = None

                if running_loop is not None:
                    # We're inside the event loop thread — safe to call put_nowait
                    q.put_nowait(message)
                elif self._loop is not None and self._loop.is_running():
                    # We're in a background thread — use call_soon_threadsafe
                    self._loop.call_soon_threadsafe(q.put_nowait, message)
                else:
                    # No loop available yet, try put_nowait anyway
                    q.put_nowait(message)
            except Exception:
                dead.append(q)
        for q in dead:
            self._queues.remove(q)

    async def subscribe_generator(self) -> AsyncGenerator[str, None]:
        q = self.subscribe()
        try:
            while True:
                try:
                    message = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'step': 'heartbeat', 'message': 'keepalive'})}\n\n"
        finally:
            self.unsubscribe(q)


nova_sse = SSEManager()
