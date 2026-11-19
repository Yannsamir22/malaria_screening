import pytest
from app.config import Settings

def test_settings_defaults_and_valid_secret() -> None:
      s = Settings(jwt_secret="a" * 32)
      assert s.jwt_secret == "a" * 32
      assert s.max_image_bytes == 20_971_520
      assert s.min_image_side == 512
      
      
def test_settings_short_secret_raises() -> None:
      with pytest.raises(RuntimeError, match="JWT_SECRET must be at least 32 characters"):
            Settings(jwt_secret="tooshort")
def test_settings_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
      monkeypatch.setenv("JWT_SECRET", "x" * 32)
      monkeypatch.delenv("MAX_IMAGE_BYTES", raising=False)
      monkeypatch.delenv("MIN_IMAGE_SIDE", raising=False)
      
      s = Settings.from_env()
      assert s.max_image_bytes == 20_971_520
      assert s.min_image_side == 512
      
# def test_settings_from_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
#     monkeypatch.setenv("JWT_SECRET", "x" * 40)
#     monkeypatch.setenv("MAX_IMAGE_BYTES", "1048576")
#     monkeypatch.setenv("MIN_IMAGE_SIDE", "256")

#     s = Settings.from_env()
#     assert s.max_image_bytes == 1_048_576
#     assert s.min_image_side == 256