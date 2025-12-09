from datetime import timedelta
from django.utils import timezone

from .models import EventSubscription
from emailer.service import sendEmail

def send_notification(user, event):
   
    name = user.first_name or ""
    surname = user.last_name or ""
    event_name = event.event_id
    begin_time = event.event_time
    
    title = f"Reminder: {event_name}"

    message = (
        f"Dear {name} {surname}, we would like to remind you that {event_name} "
        f"will be at {begin_time} and will be visible at your location. "
        f"You received this mail because you have subscribed to this event. "
        f"Best regards, The SkyMap team."
    )

    sendEmail(user.email, title, message)
    
    
    
    
    
def notify():
    """
    Szuka subskrypcji na wydarzenia, które odbędą się
    w ciągu następnych 1–25 godzin i wysyła powiadomienia (print na konsolę).
    """
    now = timezone.now()
    window_start = now + timedelta(hours=1)
    window_end = now + timedelta(hours=25)

    subs = EventSubscription.objects.filter(
        event_time__gte=window_start,
        event_time__lte=window_end,
    )

    for sub in subs:
        send_notification(sub.user, sub)
        
        