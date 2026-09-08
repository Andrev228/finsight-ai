"""Privacy-safe local AI telemetry."""

import hashlib
import hmac

from app.core.config import settings
from app.db.models import AiRun
from app.db.session import async_session


class AiRunRecorder:
    def __init__(self) -> None:
        self._pepper = settings.app_encryption_key.get_secret_value().encode()

    async def record(
        self,
        *,
        user_id: str,
        question: str,
        latency_ms: int,
        success: bool,
        unsupported: bool = False,
        model: str | None = None,
        tools_used: list[str] | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error_code: str | None = None,
    ) -> None:
        if not self._pepper:
            return
        question_hash = self._fingerprint(question)
        user_fingerprint = self._fingerprint(user_id)
        async with async_session() as session:
            session.add(
                AiRun(
                    user_fingerprint=user_fingerprint,
                    question_hash=question_hash,
                    model=model,
                    tools_used=tools_used or [],
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    success=success,
                    unsupported=unsupported,
                    error_code=error_code,
                ),
            )
            await session.commit()

    def _fingerprint(self, value: str) -> str:
        return hmac.new(
            self._pepper,
            value.encode(),
            hashlib.sha256,
        ).hexdigest()
