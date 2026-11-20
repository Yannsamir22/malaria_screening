from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
      jwt_secret: str
      max_image_bytes: int = 20 * 1024 * 1024 # 20_971_520
      min_image_side: int = 512
      
      def __post_init__(self) -> None:
            if len(self.jwt_secret) < 32:
                  raise RuntimeError("JWT_SECRET must be at least 32 characters")
            
      @classmethod
      def from_env(cls) -> Settings:
            jwt_secret = os.environ.get("JWT_SECRET")
            if not jwt_secret:
                  raise RuntimeError("JWT_SECRET must be at least 32 characters")
            
            kwargs: dict[str, str | int] = {"jwt_secret": jwt_secret}
            
            if(max_bytes := os.environ.get("MAX_IMAGE_BYTES")) is not None:
                  kwargs["max_image_bytes"] = int(max_bytes)
                  
            if(min_side := os.environ.get("MAX_IMAGE_SIDE")) is not None:
                  kwargs["min_image_side"] = int(min_side)
                  
                  
            return cls(**kwargs) # type: ignore[arg-type]
      