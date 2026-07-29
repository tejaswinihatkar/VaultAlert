"""
VaultAlert — AI Service (Gemini Integration)
Provides natural language incident summaries and anomaly threat scoring.
Falls back to rule-based summaries if GEMINI_API_KEY is not configured.
"""

import asyncio
from typing import Optional

from loguru import logger

from app.core.config import settings


# Severity-weighted threat scores for rule-based fallback
_EVENT_SCORES: dict[str, float] = {
    "DoorForced":         0.95,
    "Tampering":          0.90,
    "EmergencyLockdown":  0.85,
    "UnknownFace":        0.75,
    "FingerprintFailed":  0.60,
    "OTPFailed":          0.50,
    "MotionDetected":     0.30,
    "DoorLeftOpen":       0.25,
    "CameraOffline":      0.20,
    "BatteryLow":         0.15,
    "InternetOffline":    0.10,
    "PowerFailure":       0.40,
    "AccessGranted":      0.05,
    "AccessDenied":       0.45,
}

_FALLBACK_SUMMARIES: dict[str, str] = {
    "DoorForced":
        "A forced door entry was detected. The door was physically opened without authentication. "
        "Immediate inspection of the locker and surrounding area is strongly recommended.",
    "Tampering":
        "Physical tampering with the locker hardware was detected. This could indicate an "
        "attempted break-in or unauthorized modification of the device.",
    "EmergencyLockdown":
        "Emergency lockdown has been activated. All access to this locker has been suspended "
        "pending manual review by an authorized administrator.",
    "UnknownFace":
        "An unrecognized individual attempted to access this locker via facial recognition. "
        "The access attempt was denied. Review camera footage for identification.",
    "FingerprintFailed":
        "A fingerprint authentication failure was recorded. The presented fingerprint did not "
        "match any enrolled templates. Access was denied.",
    "OTPFailed":
        "An invalid or expired one-time password was entered. This may indicate a phishing "
        "attempt or unauthorized access attempt.",
    "MotionDetected":
        "Motion was detected near the locker. No authentication attempt was made. "
        "This could be routine activity or unauthorized presence.",
    "DoorLeftOpen":
        "The locker door has been left open beyond the configured auto-lock threshold. "
        "The system has attempted to re-engage the locking mechanism.",
    "CameraOffline":
        "The surveillance camera for this locker has gone offline. Surveillance coverage is "
        "currently unavailable. Check power and connectivity.",
    "BatteryLow":
        "The device battery level has dropped below the alert threshold. A recharge or battery "
        "replacement is required to ensure continuous operation.",
    "InternetOffline":
        "The locker device has lost internet connectivity. Remote monitoring and control are "
        "temporarily unavailable. The device may operate in offline mode.",
    "PowerFailure":
        "A power failure has been detected for this locker device. The backup battery (if installed) "
        "is now active. Restore power as soon as possible.",
    "AccessGranted":
        "Authorized access was successfully granted. All authentication factors were verified.",
    "AccessDenied":
        "An access attempt was denied due to failed authentication. The user did not meet the "
        "required security criteria for this locker.",
}


class AIService:
    """
    AI-powered incident analysis and threat scoring service.
    Uses Gemini Pro when API key is available; falls back to rule-based logic.
    """

    def __init__(self) -> None:
        self._enabled = bool(settings.GEMINI_API_KEY)
        if self._enabled:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model = genai.GenerativeModel("gemini-pro")
                logger.info("AI Service: Gemini Pro initialized.")
            except ImportError:
                logger.warning("AI Service: google-generativeai not installed. Using fallback.")
                self._enabled = False
        else:
            logger.info("AI Service: No GEMINI_API_KEY set — using rule-based fallback.")

    async def generate_incident_summary(
        self,
        event_type: str,
        locker_name: str,
        timestamp: str,
        details: Optional[dict] = None,
    ) -> str:
        """
        Generate a natural language summary of a security incident.
        Returns a Gemini-generated or rule-based summary string.
        """
        if self._enabled:
            try:
                return await self._gemini_summary(event_type, locker_name, timestamp, details or {})
            except Exception as e:
                logger.warning(f"AI Service: Gemini call failed ({e}). Using fallback.")

        return _FALLBACK_SUMMARIES.get(
            event_type,
            f"A security event of type '{event_type}' was recorded for locker '{locker_name}' "
            f"at {timestamp}. Please review the event details and take appropriate action.",
        )

    async def _gemini_summary(
        self,
        event_type: str,
        locker_name: str,
        timestamp: str,
        details: dict,
    ) -> str:
        """Call Gemini Pro to generate a professional incident summary."""
        import google.generativeai as genai

        prompt = (
            f"You are a security analyst for a smart locker system called VaultAlert. "
            f"Write a concise, professional 2-3 sentence incident summary for the following event:\n\n"
            f"- Event Type: {event_type}\n"
            f"- Locker: {locker_name}\n"
            f"- Timestamp: {timestamp}\n"
            f"- Additional Details: {details}\n\n"
            f"Be factual, clear, and recommend immediate action where appropriate. "
            f"Do not use markdown formatting."
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: self._model.generate_content(prompt)
        )
        return response.text.strip()

    async def score_threat(
        self,
        event_type: str,
        recent_event_count: int = 0,
    ) -> float:
        """
        Score threat level 0.0–1.0 based on event type and recent history.
        Escalates score if repeated events detected.
        """
        base_score = _EVENT_SCORES.get(event_type, 0.3)

        # Escalate if repeated events in short window
        if recent_event_count > 3:
            escalation = min(0.2 * (recent_event_count - 3), 0.3)
            base_score = min(base_score + escalation, 1.0)

        return round(base_score, 2)

    async def natural_language_search(self, query: str, events: list) -> list:
        """
        Filter events using natural language query.
        Falls back to keyword matching when Gemini unavailable.
        """
        if not self._enabled:
            # Simple keyword fallback
            query_lower = query.lower()
            return [
                e for e in events
                if query_lower in (e.get("description") or "").lower()
                or query_lower in (e.get("event_type") or "").lower()
            ]

        # With Gemini: could implement semantic search
        # For now, return all events with a warning
        logger.info("AI natural language search is a future enhancement.")
        return events


# Module-level singleton
ai_service = AIService()
