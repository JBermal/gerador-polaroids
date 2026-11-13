"""
Motor de processamento de fotos com moldura configurável.
Dependências: apenas Pillow (stdlib para o resto).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

SHADOW_OFFSET_PX = 10
BORDER_WIDTH_PX = 3


@dataclass
class PhotoFrameConfig:
    frame_width_cm: float = 6.5
    frame_height_cm: float = 8.5
    photo_width_cm: float = 5.5
    photo_height_cm: float = 5.5
    margin_top_cm: float = 0.5
    margin_left_cm: float = 0.5
    margin_bottom_cm: float = 2.5
    margin_right_cm: float = 0.5
    dpi: int = 300
    use_filename_caption: bool = True
    custom_caption: str = ""
    caption_font_auto: bool = True
    caption_font_size: int = 50
    with_shadow: bool = False
    output_prefix: str = "polaroid_"
    jpeg_quality: int = 95

    def cm_to_pixels(self, cm: float) -> int:
        return int(cm * self.dpi / 2.54)

    def pixels_to_cm(self, pixels: int) -> float:
        return pixels * 2.54 / self.dpi

    def shadow_extra_cm(self) -> float:
        if not self.with_shadow:
            return 0.0
        return self.pixels_to_cm(SHADOW_OFFSET_PX * 2)

    def inner_frame_size_cm(self) -> tuple[float, float]:
        """Tamanho da moldura branca, descontando a área da sombra na saída final."""
        discount = self.shadow_extra_cm()
        return (
            max(0.1, self.frame_width_cm - discount),
            max(0.1, self.frame_height_cm - discount),
        )

    def photo_size_from_margins_cm(self) -> tuple[float, float]:
        """Calcula a área da foto descontando as margens da moldura interna."""
        inner_w, inner_h = self.inner_frame_size_cm()
        return (
            max(0.1, inner_w - self.margin_left_cm - self.margin_right_cm),
            max(0.1, inner_h - self.margin_top_cm - self.margin_bottom_cm),
        )

    def sync_photo_from_margins(self) -> None:
        self.photo_width_cm, self.photo_height_cm = self.photo_size_from_margins_cm()

    def resolve_caption(self, image_path: Path) -> str:
        if self.use_filename_caption:
            return image_path.stem
        return self.custom_caption.strip()

    def resolve_font_size_px(self, inner_width_cm: float) -> int:
        if self.caption_font_auto:
            return max(12, self.cm_to_pixels(inner_width_cm * 0.06))
        return max(8, self.caption_font_size)

    def validate(self) -> str | None:
        if self.frame_width_cm <= 0 or self.frame_height_cm <= 0:
            return "As dimensões de saída devem ser maiores que zero."
        if self.dpi < 72:
            return "O DPI deve ser no mínimo 72."

        inner_w, inner_h = self.inner_frame_size_cm()
        if inner_w <= 0 or inner_h <= 0:
            return "A sombra exige uma moldura maior. Aumente o tamanho de saída."

        photo_w, photo_h = self.photo_size_from_margins_cm()
        if photo_w <= 0 or photo_h <= 0:
            return "As margens excedem o tamanho disponível da moldura."

        used_width = self.margin_left_cm + photo_w + self.margin_right_cm
        used_height = self.margin_top_cm + photo_h + self.margin_bottom_cm
        if used_width > inner_w + 0.05:
            return "As margens laterais excedem a largura da moldura."
        if used_height > inner_h + 0.05:
            return "As margens verticais excedem a altura da moldura."
        if not self.caption_font_auto and self.caption_font_size < 8:
            return "O tamanho da fonte deve ser no mínimo 8 px."
        return None


PRESETS: dict[str, PhotoFrameConfig] = {
    "Polaroid (6,5 x 8,5 cm)": PhotoFrameConfig(
        frame_width_cm=6.5,
        frame_height_cm=8.5,
        photo_width_cm=5.5,
        photo_height_cm=5.5,
        margin_top_cm=0.5,
        margin_left_cm=0.5,
        margin_bottom_cm=2.5,
        margin_right_cm=0.5,
        use_filename_caption=True,
        output_prefix="polaroid_",
    ),
    "3x4 cm": PhotoFrameConfig(
        frame_width_cm=3.0,
        frame_height_cm=4.0,
        photo_width_cm=3.0,
        photo_height_cm=4.0,
        margin_top_cm=0.0,
        margin_left_cm=0.0,
        margin_bottom_cm=0.0,
        margin_right_cm=0.0,
        use_filename_caption=False,
        output_prefix="3x4_",
    ),
    "5x7 cm": PhotoFrameConfig(
        frame_width_cm=5.0,
        frame_height_cm=7.0,
        photo_width_cm=5.0,
        photo_height_cm=7.0,
        margin_top_cm=0.0,
        margin_left_cm=0.0,
        margin_bottom_cm=0.0,
        margin_right_cm=0.0,
        use_filename_caption=False,
        output_prefix="5x7_",
    ),
}


def default_output_folder() -> Path:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x27, None, 0, buf) == 0:
                path = Path(buf.value)
                if path.exists():
                    return path
        except Exception:
            pass

    for name in ("Imagens", "Pictures"):
        path = Path.home() / name
        if path.exists():
            return path
    return Path.home() / "Pictures"


def _load_caption_font(font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/gabriola.ttf",
        "C:/Windows/Fonts/segoepr.ttf",
        "C:/Windows/Fonts/ariali.ttf",
    ]
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def resize_and_crop(image: Image.Image, width_px: int, height_px: int) -> Image.Image:
    if image.mode != "RGB":
        image = image.convert("RGB")

    original_width, original_height = image.size
    scale_factor = max(width_px / original_width, height_px / original_height)
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    left = (new_width - width_px) // 2
    top = (new_height - height_px) // 2
    return image.crop((left, top, left + width_px, top + height_px))


def add_shadow(polaroid_image: Image.Image, frame_width: int, frame_height: int) -> Image.Image:
    canvas_width = frame_width + SHADOW_OFFSET_PX * 2
    canvas_height = frame_height + SHADOW_OFFSET_PX * 2

    canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
    shadow = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 50))
    canvas.paste(shadow, (SHADOW_OFFSET_PX, SHADOW_OFFSET_PX))
    canvas.paste(polaroid_image.convert("RGBA"), (0, 0))

    final_image = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
    final_image.paste(canvas, (0, 0), canvas)

    draw = ImageDraw.Draw(final_image)
    draw.rectangle(
        [
            BORDER_WIDTH_PX // 2,
            BORDER_WIDTH_PX // 2,
            canvas_width - BORDER_WIDTH_PX // 2,
            canvas_height - BORDER_WIDTH_PX // 2,
        ],
        outline=(0, 0, 0),
        width=BORDER_WIDTH_PX,
    )
    return final_image


def render_frame(
    photo: Image.Image,
    config: PhotoFrameConfig,
    caption: str = "",
) -> Image.Image:
    inner_w_cm, inner_h_cm = config.inner_frame_size_cm()
    frame_width = config.cm_to_pixels(inner_w_cm)
    frame_height = config.cm_to_pixels(inner_h_cm)
    margin_top = config.cm_to_pixels(config.margin_top_cm)
    margin_left = config.cm_to_pixels(config.margin_left_cm)
    margin_bottom = config.cm_to_pixels(config.margin_bottom_cm)

    frame = Image.new("RGB", (frame_width, frame_height), (255, 255, 255))
    frame.paste(photo, (margin_left, margin_top))

    if caption:
        draw = ImageDraw.Draw(frame)
        font_size = config.resolve_font_size_px(inner_w_cm)
        font = _load_caption_font(font_size)
        text_bbox = draw.textbbox((0, 0), caption, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = (frame_width - text_width) // 2
        text_y = frame_height - margin_bottom // 2 - text_height // 2
        draw.text((text_x, text_y), caption, fill=(100, 100, 100), font=font)

    if config.with_shadow:
        result = add_shadow(frame, frame_width, frame_height)
        target_width = config.cm_to_pixels(config.frame_width_cm)
        target_height = config.cm_to_pixels(config.frame_height_cm)
        if result.size != (target_width, target_height):
            result = result.resize((target_width, target_height), Image.Resampling.LANCZOS)
        return result

    return frame


def process_image_file(
    image_path: Path,
    output_folder: Path,
    config: PhotoFrameConfig,
) -> None:
    photo_w_cm, photo_h_cm = config.photo_size_from_margins_cm()
    photo_width = config.cm_to_pixels(photo_w_cm)
    photo_height = config.cm_to_pixels(photo_h_cm)

    with Image.open(image_path) as img:
        photo = resize_and_crop(img, photo_width, photo_height)
        caption = config.resolve_caption(image_path)
        result = render_frame(photo, config, caption=caption)

        output_folder.mkdir(parents=True, exist_ok=True)
        output_path = output_folder / f"{config.output_prefix}{image_path.name}"
        if output_path.suffix.lower() not in {".jpg", ".jpeg"}:
            output_path = output_path.with_suffix(".jpg")
        result.save(output_path, "JPEG", quality=config.jpeg_quality, dpi=(config.dpi, config.dpi))


def process_files(
    file_paths: list[Path],
    output_folder: Path,
    config: PhotoFrameConfig,
    progress_callback=None,
) -> tuple[int, int, list[str]]:
    errors: list[str] = []
    success = 0

    for index, file_path in enumerate(file_paths, start=1):
        try:
            process_image_file(file_path, output_folder, config)
            success += 1
        except Exception as exc:
            errors.append(f"{file_path.name}: {exc}")
        if progress_callback:
            progress_callback(index, len(file_paths), file_path.name)

    return success, len(file_paths), errors
