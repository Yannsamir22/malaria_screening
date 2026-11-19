import io
import hashlib
from PIL import Image, UnidentifiedImageError

class ImageRejected(ValueError):
      pass

# Since pillow identifies formats with names like "PNG", "JPEG", "TIFF". But the api send "images/[png | jpeg | tiff]" we need a dictionary for translation
SUPPORTED_FORMATS = {
      "PNG": "image/png",
      "JPEG": "image/jpeg",
      "TIFF": "image/tiff"
}

def inspect_image(data: bytes, min_side: int) -> dict:
      # Step 1: verify integrity
      # Image.verify() checks that the file is not corrupt.
      # BUT it leaves the image object in an unusable state after calling it. So you open once just to verify, then throw that objectaway
      try:
            Image.open(io.BytesIO(data)).verify()
      except (
            UnidentifiedImageError,   # Pillow cannot recognise the format at all
            Image.DecompressionBombError,  # file is suspiciously large when decoded
            OSError,                  # truncated or corrupt file
            SyntaxError,              # malformed header
            ValueError,               # various internal Pillow errors            
      ):
            raise ImageRejected("The file is not a readable image")
      
      # Step 2: Open AGAIN to read the actual data
      try:
            img = Image.open(io.BytesIO(data))
            fmt = img.format
            width, height = img.size
      except Exception:
            raise ImageRejected("The file is not a readable image")
      
      # Step 3: Check the format is supported
      if fmt not in SUPPORTED_FORMATS:
            raise ImageRejected(
                  f"Unsupported image format {fmt}. Accepted: PNG, JPEG, TIFF"
            )
            
      # Step 4: check the dimensions
      if min(width, height) < min_side:
            raise ImageRejected(
                  f"Image too small: {width}x{height}."
                  f"Each side must be at least {min_side} px"
            )
            
      return {
            "content_type": SUPPORTED_FORMATS[fmt],
            "width": width,
            "height": height,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()
      }
      