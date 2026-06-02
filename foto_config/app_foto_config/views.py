from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import ConfigTab, OkrugTab
from .forms import ConfigFilterForm
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger  #
import re


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ВАЛИДАЦИИ ==========

def validate_imei(imei):
    """
    Проверяет корректность IMEI:
    - 15 цифр
    - нет пробелов и других символов
    """
    # Удаляем пробелы
    imei = imei.strip()

    # Проверяем, что состоит только из цифр
    if not imei.isdigit():
        return False, "IMEI должен содержать только цифры"

    # Проверяем длину
    if len(imei) != 15:
        return False, f"IMEI должен содержать ровно 15 цифр (сейчас {len(imei)})"

    return True, imei


def validate_coordinate(value, field_name):
    """
    Проверяет корректность координат:
    - формат чч.чччччч (до 6 знаков после точки)
    - обрезает лишние знаки после точки
    """
    if not value:
        return True, value

    # Удаляем пробелы
    value = value.strip().replace(' ', '')

    # Проверяем формат (число с точкой)
    pattern = r'^-?\d+\.?\d*$'
    if not re.match(pattern, value):
        return False, f"{field_name} должен быть в формате число.число (например: 55.751244)"

    # Разделяем на целую и дробную части
    if '.' in value:
        parts = value.split('.')
        integer_part = parts[0]
        fractional_part = parts[1][:6]  # Обрезаем до 6 знаков
        normalized_value = f"{integer_part}.{fractional_part}"
    else:
        normalized_value = value

    return True, normalized_value


def check_imei_exists(imei, exclude_id=None):
    """
    Проверяет существование IMEI в БД (независимо от округа)
    """
    query = ConfigTab.objects.filter(imei=imei)
    if exclude_id:
        query = query.exclude(id=exclude_id)
    return query.exists()


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

    # ========== ПАГИНАЦИЯ С ВЫБОРОМ КОЛИЧЕСТВА ==========
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(configurations, per_page)
    page = request.GET.get('page', 1)

    try:
        configurations_page = paginator.page(page)
    except PageNotAnInteger:
        configurations_page = paginator.page(1)
    except EmptyPage:
        configurations_page = paginator.page(paginator.num_pages)

    context = {
        'configurations': configurations_page,
        'filter_form': filter_form,
        'paginator': paginator,
        'page_obj': configurations_page,
        'per_page': per_page,
    }
    return render(request, 'main_config.html', context)

@login_required
def add_config(request):
    """Страница добавления новой конфигурации (без использования форм)"""
    user_okrugs = get_user_okrugs(request.user)

    if not user_okrugs.exists() and not request.user.is_superuser:
        messages.error(request, 'У вас нет прав на добавление конфигураций')
        return redirect('main_config')

    if request.method == 'POST':
        # Получаем данные из POST запроса
        imei_raw = request.POST.get('imei', '').strip()
        addr_orientir = request.POST.get('addr_orientir', '').strip()
        lat_raw = request.POST.get('lat', '').strip()
        long_raw = request.POST.get('long', '').strip()
        okrug_id = request.POST.get('okrug')
        status = request.POST.get('status', 'off')

        errors = []

        # 1. Валидация IMEI
        imei_valid, imei_result = validate_imei(imei_raw)
        if not imei_valid:
            errors.append(imei_result)
        else:
            imei = imei_result
            # Проверка на дубликат IMEI (независимо от округа)
            if check_imei_exists(imei):
                errors.append(f'Фотоловушка с IMEI {imei} уже существует в базе данных')

        # 2. Валидация координат
        lat_valid, lat = validate_coordinate(lat_raw, 'Широта')
        if not lat_valid:
            errors.append(lat_valid)

        long_valid, long = validate_coordinate(long_raw, 'Долгота')
        if not long_valid:
            errors.append(long_valid)

        # 3. Проверка обязательных полей
        if not imei_raw:
            errors.append('Поле IMEI обязательно для заполнения')

        # 4. Проверка доступа к округу
        if okrug_id and not check_okrug_access(request.user, okrug_id):
            errors.append('У вас нет доступа к выбранному округу')

        if errors:
            context = {
                'errors': errors,
                'okrugs': user_okrugs,
                'form_data': request.POST,
            }
            return render(request, 'input_config.html', context)

        # Создаем новую запись
        config = ConfigTab(
            imei=imei,
            addr_orientir=addr_orientir,
            lat=lat if lat else None,
            long=long if long else None,
            status=status,
            autor=request.user.username,
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
        # GET запрос - показываем форму
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
        # Получаем данные
        new_imei_raw = request.POST.get('imei', '').strip()
        old_imei = config.imei

        errors = []

        # 1. Валидация IMEI
        imei_valid, imei_result = validate_imei(new_imei_raw)
        if not imei_valid:
            errors.append(imei_result)
        else:
            new_imei = imei_result
            # Проверка на дубликат (исключая текущую запись)
            if new_imei != old_imei and check_imei_exists(new_imei, exclude_id=config.id):
                errors.append(f'Фотоловушка с IMEI {new_imei} уже существует в базе данных')

        # 2. Валидация координат
        lat_valid, lat = validate_coordinate(request.POST.get('lat', '').strip(), 'Широта')
        if not lat_valid:
            errors.append(lat_valid)

        long_valid, long = validate_coordinate(request.POST.get('long', '').strip(), 'Долгота')
        if not long_valid:
            errors.append(long_valid)

        # 3. Проверка обязательных полей
        if not new_imei_raw:
            errors.append('Поле IMEI обязательно для заполнения')

        # 4. Проверка доступа к новому округу
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
        config.lat = lat if lat else None
        config.long = long if long else None
        config.status = request.POST.get('status', config.status)

        # Записываем автора изменения
        config.autor_update = request.user.username

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