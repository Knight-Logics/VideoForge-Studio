from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path


class BillingStore:
    def __init__(self, storage_file: Path, audit_file: Path | None = None):
        self.storage_file = storage_file
        self.audit_file = audit_file or (self.storage_file.parent / "billing_audit.jsonl")
        self._lock = threading.Lock()
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_file.exists():
            self._write({"tokens": {}, "processed_purchase_ids": [], "free_trial_claims": {}})

    def _read(self) -> dict:
        try:
            payload = json.loads(self.storage_file.read_text(encoding="utf-8"))
            if "tokens" not in payload:
                payload["tokens"] = {}
            if "processed_purchase_ids" not in payload:
                payload["processed_purchase_ids"] = []
            if "free_trial_claims" not in payload:
                payload["free_trial_claims"] = {}
            if "emails" not in payload:
                payload["emails"] = {}
            if "recovery_log" not in payload:
                payload["recovery_log"] = {}
            return payload
        except (json.JSONDecodeError, OSError):
            return {"tokens": {}, "processed_purchase_ids": [], "free_trial_claims": {}, "emails": {}, "recovery_log": {}}

    def _write(self, payload: dict) -> None:
        self.storage_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _utc_now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _get_token_record(self, payload: dict, token: str) -> dict:
        tokens = payload.setdefault("tokens", {})
        record = tokens.get(token)

        # Backward-compatible migration path from int credits to record object.
        if isinstance(record, int):
            record = {
                "credits": int(record),
                "paid_credits": int(record),
                "free_trial_total": 0,
                "free_trial_remaining": 0,
                "created_at": self._utc_now(),
                "last_updated_at": self._utc_now(),
            }
            tokens[token] = record
        elif not isinstance(record, dict):
            record = {
                "credits": 0,
                "paid_credits": 0,
                "free_trial_total": 0,
                "free_trial_remaining": 0,
                "created_at": self._utc_now(),
                "last_updated_at": self._utc_now(),
            }
            tokens[token] = record

        if "paid_credits" not in record:
            record["paid_credits"] = int(record.get("credits", 0))
        if "free_trial_total" not in record:
            record["free_trial_total"] = 0
        if "free_trial_remaining" not in record:
            record["free_trial_remaining"] = 0

        self._sync_record_totals(record)

        return record

    def _sync_record_totals(self, record: dict) -> None:
        paid_credits = max(0, int(record.get("paid_credits", 0)))
        free_trial_remaining = max(0, int(record.get("free_trial_remaining", 0)))
        free_trial_total = max(0, int(record.get("free_trial_total", 0)))

        if free_trial_remaining > free_trial_total:
            free_trial_remaining = free_trial_total

        record["paid_credits"] = paid_credits
        record["free_trial_total"] = free_trial_total
        record["free_trial_remaining"] = free_trial_remaining
        record["credits"] = paid_credits + free_trial_remaining

    def _audit(self, event_type: str, details: dict) -> None:
        entry = {
            "timestamp": self._utc_now(),
            "event": event_type,
            **details,
        }
        with self.audit_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def get_credits(self, token: str) -> int:
        with self._lock:
            payload = self._read()
            record = self._get_token_record(payload, token)
            self._write(payload)
            return int(record.get("credits", 0))

    def get_status(self, token: str) -> dict:
        with self._lock:
            payload = self._read()
            record = self._get_token_record(payload, token)
            self._write(payload)
            return {
                "credits": int(record.get("credits", 0)),
                "paid_credits": int(record.get("paid_credits", 0)),
                "free_trial_total": int(record.get("free_trial_total", 0)),
                "free_trial_remaining": int(record.get("free_trial_remaining", 0)),
                "email_linked": bool(record.get("email")),
                "linked_email": str(record.get("email") or ""),
            }

    def get_free_trial_claim(self, claim_key: str) -> dict | None:
        with self._lock:
            payload = self._read()
            claim = payload.setdefault("free_trial_claims", {}).get(claim_key)
            if not isinstance(claim, dict):
                return None
            return claim.copy()

    def add_credits(self, token: str, credits: int, source: str = "manual") -> int:
        if credits <= 0:
            raise ValueError("credits must be > 0")

        with self._lock:
            payload = self._read()
            record = self._get_token_record(payload, token)
            current_paid = int(record.get("paid_credits", 0))
            record["paid_credits"] = current_paid + credits
            if not record.get("created_at"):
                record["created_at"] = self._utc_now()
            record["last_updated_at"] = self._utc_now()
            self._sync_record_totals(record)
            updated = int(record.get("credits", 0))
            self._write(payload)
            self._audit(
                "credits_added",
                {
                    "token": token,
                    "source": source,
                    "delta": credits,
                    "balance": updated,
                },
            )
            return updated

    def consume_credits(self, token: str, cost: int = 1, source: str = "render") -> tuple[bool, int]:
        if cost <= 0:
            raise ValueError("cost must be > 0")

        with self._lock:
            payload = self._read()
            record = self._get_token_record(payload, token)
            current_paid = int(record.get("paid_credits", 0))
            if current_paid < cost:
                return False, current_paid

            record["paid_credits"] = current_paid - cost
            record["last_updated_at"] = self._utc_now()
            self._sync_record_totals(record)
            updated = int(record.get("paid_credits", 0))
            self._write(payload)
            self._audit(
                "credits_consumed",
                {
                    "token": token,
                    "source": source,
                    "delta": -cost,
                    "balance": int(record.get("credits", 0)),
                    "paid_balance": updated,
                },
            )
            return True, updated

    def consume_free_trial_use(self, token: str, count: int = 1, source: str = "free_trial_render") -> tuple[bool, int]:
        if count <= 0:
            raise ValueError("count must be > 0")

        with self._lock:
            payload = self._read()
            record = self._get_token_record(payload, token)
            current_remaining = int(record.get("free_trial_remaining", 0))
            if current_remaining < count:
                return False, current_remaining

            record["free_trial_remaining"] = current_remaining - count
            record["last_updated_at"] = self._utc_now()
            self._sync_record_totals(record)
            updated_remaining = int(record.get("free_trial_remaining", 0))
            self._write(payload)
            self._audit(
                "free_trial_consumed",
                {
                    "token": token,
                    "source": source,
                    "delta": -count,
                    "free_trial_remaining": updated_remaining,
                    "balance": int(record.get("credits", 0)),
                },
            )
            return True, updated_remaining

    def restore_free_trial_use(self, token: str, count: int = 1, source: str = "free_trial_restore") -> int:
        if count <= 0:
            raise ValueError("count must be > 0")

        with self._lock:
            payload = self._read()
            record = self._get_token_record(payload, token)
            current_remaining = int(record.get("free_trial_remaining", 0))
            max_total = int(record.get("free_trial_total", 0))
            record["free_trial_remaining"] = min(max_total, current_remaining + count)
            record["last_updated_at"] = self._utc_now()
            self._sync_record_totals(record)
            updated_remaining = int(record.get("free_trial_remaining", 0))
            self._write(payload)
            self._audit(
                "free_trial_restored",
                {
                    "token": token,
                    "source": source,
                    "delta": count,
                    "free_trial_remaining": updated_remaining,
                    "balance": int(record.get("credits", 0)),
                },
            )
            return updated_remaining

    def claim_free_trial(self, token: str, claim_key: str, credits: int, source: str = "free_trial") -> tuple[bool, int]:
        if credits <= 0:
            raise ValueError("credits must be > 0")
        if not claim_key:
            raise ValueError("claim_key is required")

        with self._lock:
            payload = self._read()
            claims = payload.setdefault("free_trial_claims", {})

            record = self._get_token_record(payload, token)
            if claim_key in claims:
                self._write(payload)
                return False, int(record.get("free_trial_remaining", 0))

            record["free_trial_total"] = int(record.get("free_trial_total", 0)) + credits
            record["free_trial_remaining"] = int(record.get("free_trial_remaining", 0)) + credits
            if not record.get("created_at"):
                record["created_at"] = self._utc_now()
            record["last_updated_at"] = self._utc_now()
            self._sync_record_totals(record)

            claims[claim_key] = {
                "token": token,
                "claimed_at": self._utc_now(),
                "credits": credits,
                "source": source,
            }

            self._write(payload)
            self._audit(
                "free_trial_claimed",
                {
                    "token": token,
                    "claim_key": claim_key,
                    "delta": credits,
                    "balance": int(record.get("credits", 0)),
                    "free_trial_remaining": int(record.get("free_trial_remaining", 0)),
                    "source": source,
                },
            )
            return True, int(record.get("free_trial_remaining", 0))

    def is_purchase_processed(self, purchase_id: str) -> bool:
        with self._lock:
            payload = self._read()
            processed = payload.get("processed_purchase_ids", [])
            return purchase_id in processed

    def mark_purchase_processed(self, purchase_id: str) -> None:
        with self._lock:
            payload = self._read()
            processed = payload.setdefault("processed_purchase_ids", [])
            if purchase_id not in processed:
                processed.append(purchase_id)
                self._write(payload)
                self._audit(
                    "purchase_marked_processed",
                    {
                        "purchase_id": purchase_id,
                    },
                )

    def apply_purchase_once(self, purchase_id: str, token: str, credits: int, source: str = "stripe_checkout") -> tuple[bool, int]:
        """Atomically apply credits for a purchase exactly once.

        Returns (already_processed, current_balance).
        """
        if not purchase_id:
            raise ValueError("purchase_id is required")
        if not token:
            raise ValueError("token is required")
        if credits <= 0:
            raise ValueError("credits must be > 0")

        with self._lock:
            payload = self._read()
            processed = payload.setdefault("processed_purchase_ids", [])
            record = self._get_token_record(payload, token)

            if purchase_id in processed:
                self._write(payload)
                return True, int(record.get("credits", 0))

            current_paid = int(record.get("paid_credits", 0))
            record["paid_credits"] = current_paid + credits
            if not record.get("created_at"):
                record["created_at"] = self._utc_now()
            record["last_updated_at"] = self._utc_now()
            self._sync_record_totals(record)

            processed.append(purchase_id)
            updated = int(record.get("credits", 0))
            self._write(payload)

            self._audit(
                "credits_added",
                {
                    "token": token,
                    "source": source,
                    "delta": credits,
                    "balance": updated,
                },
            )
            self._audit(
                "purchase_marked_processed",
                {
                    "purchase_id": purchase_id,
                },
            )
            return False, updated

    def link_email(self, token: str, email: str) -> tuple[bool, str]:
        with self._lock:
            payload = self._read()
            emails = payload.setdefault("emails", {})

            existing_token = emails.get(email)
            if existing_token and existing_token != token:
                return False, "That email is already linked to a different access code."

            emails[email] = token
            record = self._get_token_record(payload, token)
            record["email"] = email
            record["last_updated_at"] = self._utc_now()
            self._write(payload)
            self._audit("email_linked", {"token": token, "email": email})
            return True, "ok"

    def get_token_by_email(self, email: str) -> str | None:
        with self._lock:
            payload = self._read()
            return payload.get("emails", {}).get(email)

    def get_email_for_token(self, token: str) -> str | None:
        with self._lock:
            payload = self._read()
            record = payload.get("tokens", {}).get(token)
            if isinstance(record, dict):
                return record.get("email")
            return None

    def get_last_recovery_sent(self, email: str) -> str | None:
        with self._lock:
            payload = self._read()
            return payload.get("recovery_log", {}).get(email)

    def record_recovery_sent(self, email: str) -> None:
        with self._lock:
            payload = self._read()
            payload.setdefault("recovery_log", {})[email] = self._utc_now()
            self._write(payload)
