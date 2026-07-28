"""CPU-only inference for the supplied SimpleCNN state dictionary.

The course-provided model is a SimpleCNN state dictionary. The architecture
is reconstructed here so the model can be loaded safely with ``weights_only``
instead of unpickling the full-object ``model.pth`` artifact.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

MODEL_NAME = "simple-cnn-state-dict-v1"
IMAGE_SIZE = 128
MODEL_PATH = Path(__file__).resolve().parent / "models" / "model_state_dict.pth"
PNEUMONIA_CLASS_INDEX = 1


def _dependencies():
    try:
        import torch
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "AI inference dependencies are unavailable. Run `uv sync` first."
        ) from exc
    return torch, Image


def _build_model(torch):
    class SimpleCNN(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.conv = torch.nn.Sequential(
                torch.nn.Conv2d(1, 16, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.MaxPool2d(kernel_size=2, stride=2),
                torch.nn.Conv2d(16, 32, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.MaxPool2d(kernel_size=2, stride=2),
            )
            self.fc = torch.nn.Sequential(
                torch.nn.Flatten(),
                torch.nn.Linear(32 * 32 * 32, 2),
            )

        def forward(self, inputs):
            return self.fc(self.conv(inputs))

    return SimpleCNN()


@lru_cache(maxsize=1)
def load_model():
    """Load one CPU model instance and retain it in process memory."""
    torch, _ = _dependencies()
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"AI model file is missing: {MODEL_PATH}")

    model = _build_model(torch)
    try:
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict, strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("The SimpleCNN model could not be loaded.") from exc

    model.eval()
    return model


def _image_to_tensor(image_path: Path, torch, Image):
    try:
        with Image.open(image_path) as image:
            grayscale = image.convert("L").resize(
                (IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.LANCZOS
            )
            pixels = list(grayscale.get_flattened_data())
    except (OSError, ValueError) as exc:
        raise ValueError("The saved X-ray image cannot be decoded.") from exc

    return torch.tensor(pixels, dtype=torch.float32).reshape(
        1, 1, IMAGE_SIZE, IMAGE_SIZE
    ) / 255.0


def predict_xray(image_path: Path) -> tuple[bool, float]:
    """Return ``(is_pneumonia, confidence_percent)`` for one saved X-ray."""
    torch, Image = _dependencies()
    model = load_model()
    image_tensor = _image_to_tensor(image_path, torch, Image)

    with torch.inference_mode():
        probabilities = torch.softmax(model(image_tensor), dim=1)[0]
        class_index = int(torch.argmax(probabilities).item())
        confidence = round(float(probabilities[class_index].item()) * 100, 2)

    # The course sample uses a two-class output. Confirm this mapping with
    # the instructor/training code before presenting real clinical meaning.
    return class_index == PNEUMONIA_CLASS_INDEX, confidence
