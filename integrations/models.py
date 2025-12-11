from django.db import models
import json

class SBO(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    begin_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    def to_dict(self):
        return {
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "begin_time": self.begin_time,
            "end_time": self.end_time
        }