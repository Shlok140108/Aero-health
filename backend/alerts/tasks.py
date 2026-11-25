from celery import shared_task
from .runner import evaluate_profiles

@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def evaluate_alerts_task(self):
    try:
        return evaluate_profiles()
    except Exception as exc:
        raise self.retry(exc=exc)
