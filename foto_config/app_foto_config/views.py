# app_foto_config/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.utils import timezone  # ДОБАВИТЬ ЭТОТ ИМПОРТ
from .models import ConfigTab, OkrugTab
from .forms import ConfigFilterForm
from datetime import datetime


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАЗГРАНИЧЕНИЯ ДОСТУПА ==========

def get_user_okrugs(user):
    """
    Возвращает QuerySet округов, доступных пользователю.
    Суперпользователь видит все округа.
    Обычный пользователь видит только округа, связанные с его группами.
    """
    if user.is_superuser:
        return OkrugTab.objects.all()
    user_group_ids = user.groups.values_list('id', flat=True)
    return OkrugTab.objects.filter(group_id__in=user_group_ids)


def check_okrug_access(user, okrug_id):
    """Проверяет, имеет ли пользователь доступ к указанному округу."""
    if user.is_superuser:
        return True
    return get_user_okrugs(user).filter(id=okrug_id).exists()


# ========== ОСНОВНЫЕ VIEW-ФУНКЦИИ ==========

@login_required
def main_config(request):
    """Главная страница с таблицей конфигураций и фильтрацией"""
    user_okrugs = get_user_okrugs(request.user)

    configurations = ConfigTab.objects.select_related('okrug').filter(
        okrug__in=user_okrugs
    )

    filter_form = ConfigFilterForm(request.GET or None)
    filter_form.fields['okrug'].queryset = user_okrugs

    if filter_form.is_valid():
        imei = filter_form.cleaned_data.get('imei')
        okrug = filter_form.cleaned_data.get('okrug')

        if imei:
            configurations = configurations.filter(imei__icontains=imei)
        if okrug:
            configurations = configurations.filter(okrug=okrug)

    context = {
        'configurations': configurations,
        'filter_form': filter_form,
    }
    return render(request, 'main_config.html', context)


@login_required
def add_config(request):
    """Страница добавления новой конфигурации"""
    user_okrugs = get_user_okrugs(request.user)

    if not user_okrugs.exists() and not request.user.is_superuser:
        messages.error(request, 'У вас нет прав на добавление конфигураций')
        return redirect('main_config')

    if request.method == 'POST':
        imei = request.POST.get('imei', '').strip()
        addr_orientir = request.POST.get('addr_orientir', '').strip()
        lat = request.POST.get('lat', '').strip()
        long = request.POST.get('long', '').strip()
        okrug_id = request.POST.get('okrug')
        status = request.POST.get('status', 'off')

        errors = []
        if not imei:
            errors.append('Поле IMEI обязательно для заполнения')
        if ConfigTab.objects.filter(imei=imei).exists():
            errors.append(f'Фотоловушка с IMEI {imei} уже существует')

        if okrug_id and not check_okrug_access(request.user, okrug_id):
            errors.append('У вас нет доступа к выбранному округу')

        if errors:
            context = {
                'errors': errors,
                'okrugs': user_okrugs,
                'form_data': request.POST,
            }
            return render(request, 'input_config.html', context)

        # ИЗМЕНЕНИЕ: При создании записи autor_update не заполняем (будет null)
        config = ConfigTab(
            imei=imei,
            addr_orientir=addr_orientir,
            lat=lat,
            long=long,
            status=status,
            autor=request.user.username,
            # date_update заполнится автоматически (auto_now=True)
            # autor_update оставляем пустым при создании
        )

        if okrug_id:
            try:
                config.okrug = OkrugTab.objects.get(id=okrug_id)
            except OkrugTab.DoesNotExist:
                pass

        config.save()
        messages.success(request, f'Конфигурация для фотоловушки {imei} успешно создана')
        return redirect('main_config')

    else:
        context = {
            'okrugs': user_okrugs,
            'status_choices': ConfigTab.STATUS_CHOICES,
        }
        return render(request, 'input_config.html', context)


@login_required
def edit_config(request, pk):
    """Редактирование существующей конфигурации"""
    config = get_object_or_404(ConfigTab, pk=pk)

    if not check_okrug_access(request.user, config.okrug.id) and not request.user.is_superuser:
        raise PermissionDenied("У вас нет прав на редактирование этой конфигурации")

    user_okrugs = get_user_okrugs(request.user)

    if request.method == 'POST':
        new_imei = request.POST.get('imei', '').strip()
        old_imei = config.imei

        errors = []
        if not new_imei:
            errors.append('Поле IMEI обязательно для заполнения')
        if new_imei and new_imei != old_imei:
            if ConfigTab.objects.filter(imei=new_imei).exists():
                errors.append(f'Фотоловушка с IMEI {new_imei} уже существует')

        new_okrug_id = request.POST.get('okrug')
        if new_okrug_id and not check_okrug_access(request.user, new_okrug_id):
            errors.append('У вас нет доступа к выбранному округу')

        if errors:
            context = {
                'config': config,
                'okrugs': user_okrugs,
                'status_choices': ConfigTab.STATUS_CHOICES,
                'is_edit': True,
                'errors': errors,
            }
            return render(request, 'input_config.html', context)

        # Обновляем данные
        config.imei = new_imei
        config.addr_orientir = request.POST.get('addr_orientir', config.addr_orientir).strip()
        config.lat = request.POST.get('lat', config.lat).strip()
        config.long = request.POST.get('long', config.long).strip()
        config.status = request.POST.get('status', config.status)

        # ИЗМЕНЕНИЕ: Записываем автора изменения
        config.autor_update = request.user.username
        # date_update обновится автоматически (auto_now=True)

        okrug_id = request.POST.get('okrug')
        if okrug_id:
            try:
                config.okrug = OkrugTab.objects.get(id=okrug_id)
            except OkrugTab.DoesNotExist:
                pass
        else:
            config.okrug = None

        config.save()
        messages.success(request, f'Конфигурация для фотоловушки {config.imei} успешно обновлена')
        return redirect('main_config')

    else:
        context = {
            'config': config,
            'okrugs': user_okrugs,
            'status_choices': ConfigTab.STATUS_CHOICES,
            'is_edit': True,
        }
        return render(request, 'input_config.html', context)


@login_required
def delete_config(request, pk):
    """Удаление конфигурации"""
    config = get_object_or_404(ConfigTab, pk=pk)

    if not check_okrug_access(request.user, config.okrug.id) and not request.user.is_superuser:
        raise PermissionDenied("У вас нет прав на удаление этой конфигурации")

    if request.method == 'POST':
        imei = config.imei
        config.delete()
        messages.success(request, f'Конфигурация для фотоловушки {imei} успешно удалена')
        return redirect('main_config')

    return render(request, 'confirm_delete.html', {'config': config})