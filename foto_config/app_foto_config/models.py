from django.db import models

# Create your models here.
# app_foto_config/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class OkrugTab(models.Model):
    """Таблица округов Москвы"""
    name_okrug = models.CharField('Название округа', max_length=100, unique=True)
    id_chat = models.CharField('ID чата', max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Округ'
        verbose_name_plural = 'Округа'
        db_table = 'okrug_tab'

    def __str__(self):
        return self.name_okrug


class ConfigTab(models.Model):
    """Основная таблица конфигурации фотоловушек"""
    STATUS_CHOICES = [
        ('on', 'Включено'),
        ('off', 'Выключено'),
    ]

    imei = models.CharField('IMEI', max_length=50, unique=True, db_index=True)
    addr_orientir = models.CharField('Адресный ориентир', max_length=500, blank=True, null=True)
    lat = models.CharField('Широта', max_length=50, blank=True, null=True)
    long = models.CharField('Долгота', max_length=50, blank=True, null=True)
    okrug = models.ForeignKey(OkrugTab, on_delete=models.SET_NULL, null=True,
                              verbose_name='Округ', related_name='configurations')
    autor = models.CharField('Автор', max_length=150, blank=True, null=True)
    date_records = models.DateTimeField('Дата записи', default=timezone.now)
    status = models.CharField('Статус', max_length=3, choices=STATUS_CHOICES, default='off')

    class Meta:
        verbose_name = 'Конфигурация фотоловушки'
        verbose_name_plural = 'Конфигурации фотоловушек'
        db_table = 'config_tab'
        ordering = ['-date_records']

    def __str__(self):
        return f"{self.imei} - {self.addr_orientir}"