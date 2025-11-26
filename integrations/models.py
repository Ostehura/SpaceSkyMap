from django.db import models

class SBO(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    data_czas = models.DateTimeField()
    promien_szukania = models.FloatField(default=10.0)
    jasnosc_max = models.FloatField(default=18.0)

    def __str__(self):
        return f"SBO at ({self.latitude}, {self.longitude}) on {self.data_czas}"    promien_szukania: Optional[float] = 10.0,
     jasnosc_max: Optional[float] = 18.0
 ) -> str:
     """
     Generuje URL zapytania do API JPL Horizons/Small-Body Observability.
