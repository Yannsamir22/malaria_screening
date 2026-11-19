import copy
import uuid
from datetime import datetime, timezone

def utc_now():
      return datetime.now(timezone.utc).replace(microsecond=0)

class ScreeningStore:
      def __init__(self, new_id = uuid.uuid4, clock = utc_now):
            self.new_id = new_id
            self.clock = clock
            self._records = {}
            
      def add(self, details: dict) -> dict:
            screening_id = self.new_id()
            now = self.clock()
            
            record = {
                  **details,
                  "id": screening_id,
                  "created": now,
                  "updated": now,
                  "status": "pending"
            }
            self._records[screening_id] = record
            
            return copy.deepcopy(record)
      
      def get(self, screening_id):
            record = self._records.get(screening_id)
            if record is None:
                  return None
            return copy.deepcopy(record)
      
      def list(self, status=None, smear_type=None, region_code=None, submitted_by=None, limit=10, offset=0) -> list[dict]:
            # 1. Filter records based on provided arguments
            results = [
                  record
                  for record in self._records.values()
                  if(status is None or record.get("status") == status)
                  and (smear_type is None or record.get("smear_type") == smear_type)
                  and (region_code is None or record.get("region_code") == region_code)
                  and (submitted_by is None or record.get("submitted_by") == submitted_by)
            ]
            results.reverse()
            
            # 2. Sort newest first
            results.sort(key=lambda r: r["created"], reverse=True)
            
            # 3. Slice using offset and limit
            end = None if limit is None else offset + limit
            sliced = results[offset:end]
            
            # 4. Return deep copies 
            return [copy.deepcopy(record) for record in sliced]
      
      def set_status(self, screening_id, status, failure_reason=None):
            record = self._records.get(screening_id)
            
            if record is None:
                  return None
            record["status"] = status
            record["updated"] = self._clock()
            
            if failure_reason is not None:
                  record["failure_reason"] = failure_reason
            
            return copy.deepcopy(record)
      
      def remove(self,  screening_id):
            self._records.pop(screening_id, None)
            
            