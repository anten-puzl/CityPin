import os
from pathlib import Path
import pandas as pd
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import requests
import time
from urllib.parse import quote

# Глобальный словарь для кеширования результатов запросов по координатам
location_cache = {}

# Функция для преобразования GPS координат из формата EXIF в десятичные градусы
def convert_to_degrees(value):
    """Преобразует GPS координаты из формата EXIF в десятичные градусы"""
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

# Функция для получения GPS координат из EXIF данных
def get_gps_info(exif_data):
    """Извлекает GPS информацию из EXIF данных"""
    if not exif_data:
        return None
    
    gps_info = {}
    
    # Ищем GPS данные в EXIF
    for key, value in exif_data.items():
        tag_name = TAGS.get(key, key)
        if tag_name == 'GPSInfo':
            # Обрабатываем GPS данные
            for gps_key in value:
                sub_tag_name = GPSTAGS.get(gps_key, gps_key)
                gps_info[sub_tag_name] = value[gps_key]
    
    # Проверяем наличие необходимых GPS данных
    if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
        lat = convert_to_degrees(gps_info['GPSLatitude'])
        # Учитываем направление (N/S)
        if gps_info.get('GPSLatitudeRef', 'N') == 'S':
            lat = -lat
            
        lon = convert_to_degrees(gps_info['GPSLongitude'])
        # Учитываем направление (E/W)
        if gps_info.get('GPSLongitudeRef', 'E') == 'W':
            lon = -lon
            
        return {'latitude': lat, 'longitude': lon}
    
    return None

# Функция для определения города по GPS координатам
def get_location_info(latitude, longitude):
    """Получает информацию о местоположении по GPS координатам используя Nominatim API с кешированием"""
    if latitude is None or longitude is None:
        return None
    
    # Округляем координаты до 6 знаков после запятой для кеширования
    # (это примерно 10 см точности, что более чем достаточно для определения города)
    lat_rounded = round(latitude, 6)
    lon_rounded = round(longitude, 6)
    
    # Создаем ключ для кеша
    cache_key = f"{lat_rounded},{lon_rounded}"
    
    # Проверяем, есть ли результат в кеше
    if cache_key in location_cache:
        print(f"Используем кешированные данные для координат: {cache_key}")
        return location_cache[cache_key]
    
    # Формируем URL для запроса к Nominatim API
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=10&addressdetails=1"
    
    # Добавляем User-Agent в заголовки (требование Nominatim API)
    headers = {
        'User-Agent': 'CityPin/1.0 (https://github.com/yourusername/citypin)'
    }
    
    try:
        # Отправляем запрос
        response = requests.get(url, headers=headers)
        
        # Проверяем успешность запроса
        if response.status_code == 200:
            data = response.json()
            
            # Извлекаем информацию о местоположении
            location_info = {
                'city': None,
                'state': None,
                'country': None,
                'display_name': data.get('display_name')
            }
            
            # Получаем детальную информацию об адресе
            address = data.get('address', {})
            
            # Пытаемся получить город (может быть в разных полях)
            location_info['city'] = address.get('city') or address.get('town') or \
                                   address.get('village') or address.get('hamlet') or \
                                   address.get('municipality')
            
            # Получаем регион/штат
            location_info['state'] = address.get('state') or address.get('region') or \
                                    address.get('province') or address.get('county')
            
            # Получаем страну
            location_info['country'] = address.get('country')
            
            # Сохраняем результат в кеш
            location_cache[cache_key] = location_info
            
            return location_info
        else:
            print(f"Ошибка при запросе к Nominatim API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при определении местоположения: {e}")
        return None

# Функция для сканирования каталога с фотографиями
def scan_photos_directory(directory):
    """Сканирует указанный каталог и извлекает GPS координаты из фотографий"""
    # Поддерживаемые форматы изображений
    supported_formats = ('.jpg', '.jpeg', '.tiff', '.png')
    
    # Создаем список для хранения данных
    photo_data = []
    
    # Рекурсивно обходим все файлы в указанном каталоге
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(supported_formats):
                file_path = os.path.join(root, file)
                try:
                    # Открываем изображение
                    with Image.open(file_path) as img:
                        # Получаем EXIF данные
                        exif_data = img._getexif()
                        
                        # Извлекаем GPS информацию
                        gps_info = get_gps_info(exif_data)
                        
                        # Если GPS информация найдена, добавляем в список
                        if gps_info:
                            photo_data.append({
                                'file_path': file_path,
                                'latitude': gps_info['latitude'],
                                'longitude': gps_info['longitude']
                            })
                        else:
                            # Если GPS информация не найдена, добавляем запись без координат
                            photo_data.append({
                                'file_path': file_path,
                                'latitude': None,
                                'longitude': None
                            })
                except Exception as e:
                    print(f"Ошибка при обработке файла {file_path}: {e}")
    
    # Создаем DataFrame из собранных данных
    df = pd.DataFrame(photo_data)
    return df

# Функция для добавления информации о местоположении к данным фотографий
def add_location_info(photos_df):
    """Добавляет информацию о местоположении к DataFrame с данными фотографий"""
    # Добавляем новые столбцы для информации о местоположении
    photos_df['city'] = None
    photos_df['state'] = None
    photos_df['country'] = None
    photos_df['display_name'] = None
    
    # Счетчик обработанных фотографий с координатами
    processed_count = 0
    total_with_coords = photos_df['latitude'].notna().sum()
    
    # Обрабатываем каждую строку с координатами
    for index, row in photos_df[photos_df['latitude'].notna()].iterrows():
        processed_count += 1
        print(f"Определение местоположения для фото {processed_count}/{total_with_coords}: {row['file_path']}")
        
        # Получаем информацию о местоположении
        location_info = get_location_info(row['latitude'], row['longitude'])
        
        # Если информация получена, добавляем ее в DataFrame
        if location_info:
            photos_df.at[index, 'city'] = location_info['city']
            photos_df.at[index, 'state'] = location_info['state']
            photos_df.at[index, 'country'] = location_info['country']
            photos_df.at[index, 'display_name'] = location_info['display_name']
        
        # Делаем паузу между запросами, чтобы не превышать лимит Nominatim API
        # Если данные были получены из кеша, пауза не нужна
        cache_key = f"{round(row['latitude'], 6)},{round(row['longitude'], 6)}"
        if cache_key not in location_cache or len(location_cache) <= 1:
            time.sleep(1)
    
    return photos_df

# Функция для создания списка уникальных городов
def create_unique_locations_list(photos_df):
    """Создает список уникальных местоположений без дублей"""
    # Создаем DataFrame только с информацией о местоположении (без путей к файлам и координат)
    locations_df = photos_df[['city', 'state', 'country']].copy()
    
    # Удаляем строки, где город не определен
    locations_df = locations_df.dropna(subset=['city'])
    
    # Удаляем дубликаты
    unique_locations_df = locations_df.drop_duplicates()
    
    # Сортируем по стране и городу
    unique_locations_df = unique_locations_df.sort_values(by=['country', 'state', 'city'])
    
    return unique_locations_df

# Основная функция программы
def main():
    # Путь к каталогу с фотографиями (можно изменить на нужный)
    photos_directory = "c:/temp/"
    
    # Проверяем существование каталога
    if not os.path.exists(photos_directory):
        print(f"Каталог {photos_directory} не существует!")
        return
    
    print(f"Сканирование каталога {photos_directory}...")
    
    # Сканируем каталог и получаем данные
    photos_df = scan_photos_directory(photos_directory)
    
    # Выводим результаты сканирования
    print(f"Найдено {len(photos_df)} фотографий.")
    print(f"Из них {photos_df['latitude'].notna().sum()} с GPS координатами.")
    
    # Если есть фотографии с координатами, определяем местоположение
    if photos_df['latitude'].notna().sum() > 0:
        print("\nОпределение местоположения по GPS координатам...")
        photos_df = add_location_info(photos_df)
        
        # Выводим статистику по городам
        cities = photos_df['city'].dropna().value_counts()
        print("\nНайденные города:")
        for city, count in cities.items():
            print(f"{city}: {count} фото")
        
        # Создаем список уникальных местоположений
        unique_locations = create_unique_locations_list(photos_df)
        
        # Сохраняем список уникальных местоположений в CSV файл
        unique_locations_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unique_locations.csv')
        unique_locations.to_csv(unique_locations_file, index=False, encoding='utf-8')
        print(f"\nСписок уникальных местоположений сохранен в файл: {unique_locations_file}")
        
        # Выводим список уникальных местоположений
        print("\nСписок уникальных местоположений:")
        for _, row in unique_locations.iterrows():
            location_str = f"{row['city']}"
            if row['state']:
                location_str += f", {row['state']}"
            if row['country']:
                location_str += f", {row['country']}"
            print(location_str)
        
        # Выводим статистику по кешу
        print(f"\nСтатистика кеширования:")
        print(f"Всего уникальных координат в кеше: {len(location_cache)}")
    
    # Сохраняем результаты в CSV файл
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'photos_gps_data.csv')
    photos_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\nДанные сохранены в файл: {output_file}")
    
    # Выводим первые несколько строк таблицы
    print("\nПример данных:")
    print(photos_df.head())

if __name__ == "__main__":
    main()