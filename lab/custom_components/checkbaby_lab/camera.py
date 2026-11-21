"""A camera that shows a drawn cot instead of a child."""

from __future__ import annotations

import io

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from PIL import Image, ImageDraw

from .entity import LabEntity


def _cot_picture() -> bytes:
    """A drawing, so that no footage of a real child is ever needed."""
    image = Image.new("RGB", (640, 360), (40, 44, 52))
    draw = ImageDraw.Draw(image)
    draw.rectangle((140, 60, 500, 300), outline=(200, 200, 200), width=6)
    draw.ellipse((270, 100, 370, 180), fill=(230, 200, 180))
    draw.rounded_rectangle((250, 180, 390, 280), radius=30, fill=(120, 170, 220))
    draw.text((150, 310), "CheckBaby Lab: drawing, not a camera", fill=(200, 200, 200))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the camera."""
    picture = await hass.async_add_executor_job(_cot_picture)
    async_add_entities([LabCamera(hass, picture)])


class LabCamera(LabEntity, Camera):
    """Serves the same drawing every time."""

    def __init__(self, hass: HomeAssistant, picture: bytes) -> None:
        """Keep the picture."""
        LabEntity.__init__(self, hass, "nursery", "Nursery")
        Camera.__init__(self)
        self._picture = picture

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes:
        """Return the drawing."""
        return self._picture
