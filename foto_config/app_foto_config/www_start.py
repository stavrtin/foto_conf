# Команды для добавления округов с id_chat в Python shell
from .models import OkrugTab

# Подготовьте данные заранее в этом словаре
okrugs_data = {
    'ЦАО': '3087080103075694',
    'САО': '3073454609239370',
    'СВАО': '3087080844328117',
    'ВАО': '3077925348164238',
    'ЮВАО': '3087080274938312',
    'ЮАО': '3110311359589630',
    'ЮЗАО': '3113075510245014',
    'ЗАО': '3087080735630580',
    'СЗАО': '3087080447412686',
    'Зеленоград': '3073454243690670',
    'ТинАО': '3073455033858234',
    'Тестовый': '3075654772794088'
}

for name, chat_id in okrugs_data.items():
    obj, created = OkrugTab.objects.update_or_create(
        name_okrug=name,
        defaults={'id_chat': chat_id}
    )
    print(f'{"➕ Создан" if created else "🔄 Обновлен"}: {name} - {chat_id}')

print(f'\n✅ Итог: {OkrugTab.objects.count()} округов в БД')


