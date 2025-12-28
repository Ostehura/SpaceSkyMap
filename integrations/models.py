from django.db import models
import json

class SBO(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField()
    azimuth = models.FloatField()
    begin_time = models.DateTimeField()
    end_time = models.DateTimeField()
    points12 = models.JSONField(null=True, blank=True)
    
    def to_dict(self):
        return {
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "azimuth": self.azimuth,
            "begin_time": self.begin_time,
            "end_time": self.end_time,
            "points12": self.points12
        }
    
    def __str__(self):
        return (
            f"SBO(name={self.name}, "
            f"ra={self.latitude:.4f}°, "
            f"dec={self.longitude:.4f}°, "
            f"alt={self.altitude:.4f}°, "
            f"az={self.azimuth:.4f}°, "
            f"begin={self.begin_time}, "
            f"end={self.end_time})"
        )