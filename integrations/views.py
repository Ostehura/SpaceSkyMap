from django.shortcuts import render
import datetime
from typing import Optional

def get_query_sbo(
    latitude: float,
    longitude: float,
    data_czas: datetime.datetime,
    promien_szukania: Optional[float] = 10.0,
    jasnosc_max: Optional[float] = 18.0
) -> str:
    """
    Generuje URL zapytania do API JPL Horizons/Small-Body Observability.

    Argumenty:
        latitude (float): Szerokość geograficzna obserwatora (w stopniach, -90 do 90).
        longitude (float): Długość geograficzna obserwatora (w stopniach, -180 do 180).
        data_czas (datetime.datetime): Czas obserwacji.
        promien_szukania (float, opcjonalnie): Promień szukania w stopniach kwadratowych wokół zenitu. Domyślnie 10.0.
        jasnosc_max (float, opcjonalnie): Maksymalna wielkość gwiazdowa (jasność) do filtrowania. Domyślnie 18.0.

    Zwraca:
        str: Gotowy URL zapytania do SBO API.
    """
    # 1. Formatowanie daty/czasu do formatu akceptowanego przez API (np. '2025-Nov-25 18:00')
    time_str = data_czas.strftime("%Y-%b-%d %H:%M")
    data_czas_stop = data_czas + datetime.timedelta(days=1)
    time_str_stop = data_czas_stop.strftime("%Y-%b-%d %H:%M")

    # 2. Formatowanie lokalizacji obserwatora: 'geoc=szerokość,długość'
    # API Horizons często wymaga formatu Długość, Szerokość (np. 'lon,lat')
    geoc_str = f"'{longitude},{latitude},0'" # Dodano wysokość 0 km n.p.m.

    # 3. Definicja stałego URL bazowego
    # Chociaż SBO jest częścią Horizons, często zapytania są kierowane do ogólnego API JPL
    BASE_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

    # 4. Konstrukcja parametrów zapytania
    params = {
        # Ustawienia podstawowe
        "format": "text",               # Format odpowiedzi (tekstowy)
        "COMMAND": "'MB'",               # 'MB' oznacza Listę Małych Ciał (Minor Bodies)
        "CENTER": geoc_str,              # Lokalizacja obserwatora (lon, lat, elev)
        "START_TIME": f"'{time_str}'",   # Czas rozpoczęcia obserwacji
        "STOP_TIME": f"'{time_str_stop}'",    # Czas zakończenia obserwacji
        "STEP_SIZE": "'1d'",             # Rozmiar kroku (minimalny 1 dzień, ale API użyje START_TIME/STOP_TIME jako punktu)
        
        # Formatowanie wyjścia
        "CSV_FORMAT": "YES",            # Zwraca dane w formacie CSV
        "OBJ_DATA": "NO",                # Nie zwraca szczegółowych danych obiektu
        "QUANTITIES": "'1,3,9,19,20'",   # Określenie, jakie efemerydy chcemy (np. RA/Dec, Alt/Az, Jasność)
    }

    # 5. Łączenie parametrów w URL
    query_parts = []
    for key, value in params.items():
        # Używamy formatu 'key=value'
        query_parts.append(f"{key}={value}")

    # Finalny URL
    full_url = f"{BASE_URL}?" + "&".join(query_parts)
    return full_url
