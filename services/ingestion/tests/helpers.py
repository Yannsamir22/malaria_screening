import uuid
from datetime import datetime, timedelta, timezone

from tests.tokens import make_token

def make_id_factory():
      counter = {"n": 0}
      
      def new_id():
            counter["n"] += 1
            return uuid.UUID(int=counter["n"])
      
      return new_id

def make_ticking_clock():
      state = {"t": datetime(2026, 1, 1, tzinfo=timezone.utc)}
      
      def clock():
            state["t"] += timedelta(seconds=1)
            return state["t"]
      return clock

def auth(role, sub=None) -> dict:
      return {"Authorization": f"Bearer {make_token(role, user_id=sub)}"}