import io
from PIL import Image


def test_generate_card_returns_png_bytes():
    from content_bot.services.image_card import generate_card
    result = generate_card("Как я автоматизировал 4 часа работы за 10 минут")
    assert isinstance(result, bytes)
    assert len(result) > 1000
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"
    assert img.size == (1080, 1080)


def test_generate_card_handles_long_text():
    from content_bot.services.image_card import generate_card
    long_text = "Очень длинный текст. " * 30
    result = generate_card(long_text)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (1080, 1080)


def test_generate_card_handles_empty_text():
    from content_bot.services.image_card import generate_card
    result = generate_card("")
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (1080, 1080)


def test_generate_card_handles_multiline_text():
    from content_bot.services.image_card import generate_card
    text = "Первая строка хука.\n\nВторой абзац который не должен попасть на карточку."
    result = generate_card(text)
    assert isinstance(result, bytes)
