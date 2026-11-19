from datetime import datetime, timezone
from typing import Protocol

def build_screening_created_event(screening: dict) -> dict:
      """
      Build the event payload for a new screening. 
      The screening argument is the raw record from the store.
      """
      return{
            "event": "screening.created",
            "screening_id": str(screening["id"]),
            "smear_type": screening["smear_type"],
            "region_code": screening["region_code"],
            "image_key": str(screening["id"]),
            "created": screening["created"].strftime("%Y-%m-%dTH:%M:%SZ")
      }
      
class JobPublisher(Protocol):
      def publish_screening_created(self, screening: dict) -> None:
            """Announce a new screening to the AI workers."""
            ...
            
class MemoryPublisher:
      def __init__(self):
            self.messages: list[dict] = []
            
      def publish_screening_created(self, screening: dict) -> None:
            event = build_screening_created_event(screening)
            self.messages.append(event)