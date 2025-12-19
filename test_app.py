import unittest
from app import app
import pytest


class FlaskAppTests(unittest.TestCase):
    """Тесты для Flask приложения"""

    def setUp(self):
        """Настройка тестового клиента"""
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        """Тест главной страницы"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

        html_content = response.data.decode('utf-8')
        self.assertIn('Смешивание двух изображений', html_content)
        self.assertIn('Вариант 4', html_content)

    def test_health_endpoint(self):
        """Тест эндпоинта проверки здоровья"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)

        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'ok')
        self.assertEqual(json_data['message'], 'Application is running')

    def test_page_contains_form_elements(self):
        """Тест наличия элементов формы"""
        response = self.app.get('/')
        html_content = response.data.decode('utf-8')

        self.assertIn('name="image1"', html_content)
        self.assertIn('name="image2"', html_content)
        self.assertIn('name="blend_level"', html_content)


# Дополнительные тесты с pytest
@pytest.mark.smoke
def test_app_import():
    """Тест импорта приложения"""
    from app import app
    assert app is not None
    assert app.config['MAX_CONTENT_LENGTH'] == 16 * 1024 * 1024


@pytest.mark.integration
def test_blend_function():
    """Тест функции смешивания"""
    from PIL import Image
    import numpy as np
    from app import blend_images

    # Создаем тестовые изображения
    img1 = Image.new('RGB', (100, 100), color='red')
    img2 = Image.new('RGB', (100, 100), color='blue')

    # Тестируем смешивание
    blended, resized = blend_images(img1, img2, 0.5)

    assert blended.size == (100, 100)
    assert resized.size == (100, 100)

    # Проверяем, что смешивание произошло
    pixel = np.array(blended)[50, 50]
    # Красный (255,0,0) + Синий (0,0,255) → Фиолетовый (~128,0,128)
    assert 100 < pixel[0] < 150  # R
    assert pixel[1] < 50  # G
    assert 100 < pixel[2] < 150  # B


if __name__ == '__main__':
    unittest.main()