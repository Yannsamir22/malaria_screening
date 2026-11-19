import io
import pytest
from PIL import Image
from app.imaging import inspect_image, ImageRejected

def make_image_bytes(format="PNG", size=(600, 600)):
      """Helper: create a real in-memory image and return its bytes."""
      buf = io.BytesIO()
      Image.new("RGB", size, color=(255, 0, 0)).save(buf, format=format)
      return buf.getvalue()

# Test 1: a valid 600x600 PNG returns the right keys
def test_valid_png_returns_facts():
      data = make_image_bytes("PNG", (600, 600))
      result = inspect_image(data, min_side=512)
      assert result["content_type"] == "image/png"
      assert result["width"] == 600
      assert result["height"] == 600
      assert len(result["sha256"]) == 64
 
 
#  Test 3: a GIF raises ImageRejected  (unsupported format)
def test_gif_is_rejected():
      data = make_image_bytes("GIF", (600, 600))
      with pytest.raises(ImageRejected, match="GIF"): 
            inspect_image(data, min_side=512)
            
# Test 4: a 400x400 image raises ImageRejected (too small)
def test_too_small_raises():
      data = make_image_bytes("PNG", (400, 400))
      with pytest.raises(ImageRejected, match="400x400"):
            inspect_image(data, min_side=512)
            
            
# Test 5: JPEG and TIFF are accepted
def test_jpeg_and_tiff_accepted():
      for fmt, mime in [("JPEG", "image/jpeg"), ("TIFF", "image/tiff")]:
            data = make_image_bytes(fmt, (600, 600))
            result = inspect_image(data, min_side=512)
            assert result["content_type"] == mime
                  