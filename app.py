from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
import numpy as np
import io
import base64
import os
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

RECAPTCHA_SITE_KEY = "6LdyaBYsAAAAACyUnXmvWZuWD3o2U0vZ1P8_nBw7"
RECAPTCHA_SECRET_KEY = "6LdyaBYsAAAAADfC83TrEor1NW3hu78hKtTREi3x"


def verify_recaptcha(response_token):
    """Верификация Google reCAPTCHA"""
    data = {
        'secret': RECAPTCHA_SECRET_KEY,
        'response': response_token
    }

    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            timeout=5
        )
        result = response.json()
        return result.get('success', False)
    except requests.RequestException:
        return False


def resize_image_to_match(image1, image2):
    """Изменение размера второго изображения под первое"""
    width1, height1 = image1.size
    width2, height2 = image2.size

    # Если размеры совпадают, ничего не делаем
    if width1 == width2 and height1 == height2:
        return image2

    # Меняем размер второго изображения под первое
    return image2.resize((width1, height1), Image.Resampling.LANCZOS)


def blend_images(image1, image2, blend_level):
    """
    Смешивание двух изображений
    blend_level: от 0.0 до 1.0
    0.0 - полностью первое изображение
    1.0 - полностью второе изображение
    """
    # Конвертируем в RGB, если необходимо
    if image1.mode != 'RGB':
        image1 = image1.convert('RGB')
    if image2.mode != 'RGB':
        image2 = image2.convert('RGB')

    # Изменяем размер второго изображения под первое
    image2 = resize_image_to_match(image1, image2)

    # Преобразуем в numpy массивы
    img1_array = np.array(image1, dtype=np.float32)
    img2_array = np.array(image2, dtype=np.float32)

    # Нормализуем уровень смешивания
    alpha = float(blend_level)
    alpha = max(0.0, min(1.0, alpha))  # Ограничиваем от 0 до 1

    # Линейное смешивание
    blended_array = (1 - alpha) * img1_array + alpha * img2_array

    # Преобразуем обратно в Image
    blended_array = np.clip(blended_array, 0, 255).astype(np.uint8)
    blended_image = Image.fromarray(blended_array)

    return blended_image, image2  # Возвращаем и измененное второе изображение


def add_watermark(image, text="Вариант 4", opacity=0.5):
    """
    Добавление водяного знака на изображение
    Поворачивает текст на 90 градусов
    """
    # Создаем копию изображения
    watermarked = image.copy()

    # Создаем слой для водяного знака
    watermark = Image.new('RGBA', watermarked.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark)

    # Параметры текста
    try:
        # Пробуем использовать шрифт по умолчанию или загрузить стандартный
        font = ImageFont.truetype("arial.ttf", 100)
    except IOError:
        # Если шрифт не найден, используем стандартный
        font = ImageFont.load_default()

    # Определяем размер текста
    # Создаем временное изображение для определения размера
    temp_img = Image.new('RGBA', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Поворачиваем текст на 90 градусов
    # Создаем отдельное изображение для текста
    text_img = Image.new('RGBA', (text_width + 100, text_height + 100), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((50, 50), text, font=font, fill=(255, 255, 255, int(255 * opacity)))

    # Поворачиваем на 90 градусов
    rotated_text = text_img.rotate(90, expand=True)

    # Размещаем водяной знак в центре
    x = (watermarked.width - rotated_text.width) // 2
    y = (watermarked.height - rotated_text.height) // 2

    # Накладываем водяной знак
    watermark.paste(rotated_text, (x, y), rotated_text)

    # Объединяем с исходным изображением
    watermarked = Image.alpha_composite(
        watermarked.convert('RGBA'),
        watermark
    )

    return watermarked.convert('RGB')


def create_color_histogram(image, title):
    """Создание цветовой гистограммы изображения"""
    # Конвертируем в RGB, если необходимо
    if image.mode != 'RGB':
        image = image.convert('RGB')

    img_array = np.array(image)

    # Размеры гистограммы
    width, height = 600, 300
    hist_img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(hist_img)

    # Цветовые каналы
    colors = ['red', 'green', 'blue']
    channel_data = []

    # Строим гистограмму для каждого канала
    for i in range(3):
        channel = img_array[:, :, i].flatten()
        hist, bins = np.histogram(channel, bins=256, range=(0, 255))
        hist = hist / hist.max()  # Нормализуем
        channel_data.append(hist)

    # Рисуем оси
    draw.line([(50, 50), (50, height - 50)], fill='black', width=2)  # Y ось
    draw.line([(50, height - 50), (width - 50, height - 50)],
              fill='black', width=2)  # X ось

    # Подписи
    draw.text((30, 20), title[:30], fill='black', font_size=12)
    draw.text((width // 2, height - 30), 'Значение пикселя', fill='black')
    draw.text((10, height // 2), 'Частота', fill='black', angle=90)

    # Рисуем гистограммы для каждого канала
    for i, color in enumerate(colors):
        hist = channel_data[i]
        color_map = {'red': (255, 0, 0), 'green': (0, 255, 0), 'blue': (0, 0, 255)}

        # Рисуем линии гистограммы
        for j in range(255):
            x1 = 50 + j * (width - 100) // 256
            x2 = 50 + (j + 1) * (width - 100) // 256

            y1 = height - 50 - int(hist[j] * (height - 100))
            y2 = height - 50 - int(hist[j + 1] * (height - 100))

            # Полупрозрачная заливка под линией
            overlay = Image.new('RGBA', (x2 - x1, height - 50 - y1),
                                (*color_map[color], 50))
            hist_img.paste(overlay, (x1, y1), overlay)

            # Линия гистограммы
            draw.line([(x1, y1), (x2, y2)], fill=color_map[color], width=2)

    # Легенда
    legend_y = 70
    for i, color in enumerate(colors):
        color_map = {'red': (255, 0, 0), 'green': (0, 255, 0), 'blue': (0, 0, 255)}
        draw.rectangle([width - 120, legend_y + i * 20,
                        width - 100, legend_y + i * 20 + 10],
                       fill=color_map[color])
        draw.text((width - 95, legend_y + i * 20),
                  f'{color.upper()}', fill='black', font_size=10)

    # Сохраняем в буфер
    buf = io.BytesIO()
    hist_img.save(buf, format='PNG', quality=95)
    buf.seek(0)

    return buf


def convert_image_to_base64(image):
    """Конвертация изображения в base64"""
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


@app.route('/', methods=['GET', 'POST'])
def index():
    """Основной маршрут приложения"""
    image1_hist = None
    image2_hist = None
    blended_hist = None
    image1_data = None
    image2_data = None
    blended_data = None
    message = ""
    captcha_error = ""

    if request.method == 'POST':
        # Проверка reCAPTCHA
        recaptcha_response = request.form.get('g-recaptcha-response')
        if not recaptcha_response:
            captcha_error = "Пожалуйста, подтвердите, что вы не робот"
        elif not verify_recaptcha(recaptcha_response):
            captcha_error = "Ошибка проверки reCAPTCHA. Попробуйте еще раз."
        else:
            # Проверка загруженных файлов
            if 'image1' not in request.files or 'image2' not in request.files:
                message = "Пожалуйста, загрузите оба изображения"
            else:
                image1_file = request.files['image1']
                image2_file = request.files['image2']

                if image1_file.filename == '' or image2_file.filename == '':
                    message = "Пожалуйста, выберите оба изображения"
                else:
                    try:
                        # Получаем уровень смешивания
                        blend_level = float(request.form.get('blend_level', 0.5))

                        # Загружаем изображения
                        image1 = Image.open(image1_file.stream)
                        image2 = Image.open(image2_file.stream)

                        # Конвертируем в RGB, если необходимо
                        if image1.mode != 'RGB':
                            image1 = image1.convert('RGB')
                        if image2.mode != 'RGB':
                            image2 = image2.convert('RGB')

                        # Создаем гистограммы исходных изображений
                        image1_hist_buf = create_color_histogram(image1,
                                                                 "Первое изображение")
                        image1_hist = base64.b64encode(
                            image1_hist_buf.getvalue()).decode('utf-8')

                        image2_hist_buf = create_color_histogram(image2,
                                                                 "Второе изображение")
                        image2_hist = base64.b64encode(
                            image2_hist_buf.getvalue()).decode('utf-8')

                        # Смешиваем изображения
                        blended_image, resized_image2 = blend_images(image1, image2, blend_level)

                        # Добавляем водяной знак на результирующее изображение
                        blended_image = add_watermark(blended_image, "Вариант 4", opacity=0.4)

                        # Создаем гистограмму для смешанного изображения
                        blended_hist_buf = create_color_histogram(
                            blended_image,
                            f"Смешанное (уровень: {blend_level:.2f})"
                        )
                        blended_hist = base64.b64encode(
                            blended_hist_buf.getvalue()).decode('utf-8')

                        # Конвертируем изображения для отображения
                        image1_data = convert_image_to_base64(image1)
                        image2_data = convert_image_to_base64(resized_image2)
                        blended_data = convert_image_to_base64(blended_image)

                        message = (f"Обработка завершена успешно! "
                                   f"Уровень смешивания: {blend_level:.2f}")

                    except Exception as e:
                        message = f"Ошибка при обработке изображений: {str(e)}"
                        import traceback
                        print(traceback.format_exc())

    return render_template('index.html',
                           image1_hist=image1_hist,
                           image2_hist=image2_hist,
                           blended_hist=blended_hist,
                           image1_data=image1_data,
                           image2_data=image2_data,
                           blended_data=blended_data,
                           message=message,
                           captcha_error=captcha_error,
                           recaptcha_site_key=RECAPTCHA_SITE_KEY)


@app.route('/health')
def health():
    """Маршрут для проверки работоспособности приложения"""
    return {"status": "ok", "message": "Application is running"}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)