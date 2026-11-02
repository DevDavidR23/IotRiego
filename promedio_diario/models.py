from django.db import models


class PromedioDiario(models.Model):
    id = models.AutoField(primary_key=True)
    humedad_promedio = models.FloatField()
    fecha = models.DateField(unique=True, error_messages={
        'unique': 'Ya existe un registro para esta fecha.',
    })

    class Meta:
        db_table = 'promedio_diario'
        ordering = ['-fecha']
        verbose_name = 'promedio diario'
        verbose_name_plural = 'promedios diarios'

    def __str__(self):
        return f'{self.fecha}: {self.humedad_promedio}'
