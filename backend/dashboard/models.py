from django.db import models


class DatabaseCacheEntry(models.Model):
    """Schema for Django's shared database cache backend."""

    cache_key = models.CharField(max_length=255, primary_key=True)
    value = models.TextField()
    expires = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "django_cache"