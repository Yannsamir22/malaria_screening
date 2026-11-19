from  typing import Protocol

class ImageStorage(Protocol):
      def put(self, key: str, data: bytes, content_type: str) -> None:
            """Store image bytes under key."""
            ...
      
      def get(self, key: str) -> bytes:
            """Retrieve image bytes by key."""
            
      def delete(self, key: str) -> None:
            """Delete image bytes by key. Harmless if key does not exist."""
            
class MemoryImageStorage:
      def __init__(self):
            self._store: dict[str, bytes] = {}
            
      def put(self, key: str, data: bytes, content_type: str) -> None:
            # content_type is accepted but not needed in memory
            # (MinIO will need it to serve the file with the right header)
            self._store[key] = data
            
      def get(self, key: str) -> bytes:
            return self._store[key]
      
      def delete(self, key: str) -> None:
            # pop with a default of None means: remove if exists, do nothing if not
            self._store.pop(key, None)