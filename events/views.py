from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from integrations.views import get_query_sbo # moduł integracji z NASA


@api_view(['POST'])
@permission_classes([IsAuthenticated])  
def events_view(request):
    
    data = request.query_params or request.data

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    begin_time = data.get('begin_time')
    end_time = data.get('end_time')

    
    missing = []
    if latitude is None:
        missing.append('latitude')
    if longitude is None:
        missing.append('longitude')
    if begin_time is None:
        missing.append('begin_time')
    if end_time is None:
        missing.append('end_time')

    if missing:
        return Response(
            {"detail": f"Brak wymaganych parametrów: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    
    try:
        lat = float(latitude)
        lon = float(longitude)
    except ValueError:
        return Response(
            {"detail": "Parametry 'latitude' i 'longitude' muszą być liczbami (float)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    
    def parse_iso(dt_str: str):
        
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    start_dt = parse_iso(begin_time)
    end_dt = parse_iso(end_time)

    if start_dt is None or end_dt is None:
        return Response(
            {"detail": "Parametry 'begin_time' i 'end_time' muszą być w formacie ISO 8601."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if start_dt >= end_dt:
        return Response(
            {"detail": "'begin_time' musi być wcześniejszy niż 'end_time'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        events = get_query_sbo(
            latitude=lat,
            longitude=lon,
            begin_time=start_dt,
            end_time=end_dt,
        )
    except Exception as e:
        print(e)
        return Response(
            {"detail": "Błąd podczas pobierania danych z modułu NASA."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not isinstance(events, list):
        return Response(
            {"detail": "Nieprawidłowy format danych zwróconych przez moduł NASA."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(events, status=status.HTTP_200_OK)
