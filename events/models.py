from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class EventSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_subscriptions")
    event_id = models.CharField(max_length=255)
    event_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "event_id")

    def __str__(self):
        return f"{self.user} -> {self.event_id} @ {self.event_time}"
