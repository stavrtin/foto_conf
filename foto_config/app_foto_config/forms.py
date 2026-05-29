# app_foto_config/forms.py

from django import forms
from .models import ConfigTab, OkrugTab

class ConfigFilterForm(forms.Form):
    """Форма для фильтрации"""
    imei = forms.CharField(max_length=50, required=False,
                          label='IMEI',
                          widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по IMEI'}))
    okrug = forms.ModelChoiceField(queryset=OkrugTab.objects.all(),
                                   required=False,
                                   label='Округ',
                                   widget=forms.Select(attrs={'class': 'form-control'}))