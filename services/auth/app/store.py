from copy import deepcopy
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID, uuid4

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)

class UserStore:

    def __init__(
        self,
        new_id: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = utc_now,
    ):
        self._users: dict[str, dict] = {}
        self._email_index: dict[str, str] = {}

        self._new_id = new_id
        self._clock = clock

    def add(self, record: dict) -> dict:
        user_id = str(self._new_id())

        if record["email"] in self._email_index:
            raise ValueError("Email already exists.")

        stored_record = deepcopy(record)
        stored_record["id"] = user_id
        stored_record["status"] = stored_record.get("status", "active")
        stored_record["created"] = self._clock().isoformat()

        self._users[user_id] = stored_record
        self._email_index[stored_record["email"]] = user_id

        return deepcopy(stored_record)

    def get(self, user_id: str) -> dict | None:
        record = self._users.get(user_id)

        if record is None:
            return None

        return deepcopy(record)

    def get_by_email(self, email: str) -> dict | None:
        user_id = self._email_index.get(email)

        if user_id is None:
            return None

        return self.get(user_id)

    def list(
        self,
        role: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:

        records = list(self._users.values())

        if role is not None:
            records = [r for r in records if r.get("role") == role]

        if status is not None:
            records = [r for r in records if r.get("status") == status]

        return deepcopy(records[offset:offset + limit])

    def update(self, user_id: str, changes: dict) -> dict | None:
        record = self._users.get(user_id)

        if record is None:
            return None

        if "email" in changes:
            new_email = changes["email"]

            existing_id = self._email_index.get(new_email)

            if existing_id is not None and existing_id != user_id:
                raise ValueError("Email already exists.")

            old_email = record["email"]
            self._email_index.pop(old_email, None)
            self._email_index[new_email] = user_id

        record.update(deepcopy(changes))

        return deepcopy(record)

    def set_status(self, user_id: str, status: str) -> dict | None:
        record = self._users.get(user_id)

        if record is None:
            return None

        record["status"] = status

        return deepcopy(record)