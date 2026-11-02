from django.db import models
from django.db.models.functions import Now


class Humedad(models.Model):
    humedad = models.FloatField()
    timestamp = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = 'humedad'
        ordering = ['-timestamp']
        verbose_name_plural = 'humedad'

    def __str__(self):
        return f'{self.humedad} ({self.timestamp:%Y-%m-%d %H:%M:%S})'
