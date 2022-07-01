# Социальная сеть YaTube.
![Django](https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

Социальная сеть с возможностью создания, просмотра, редактирования и удаления (CRUD) записей. Реализован механизм подписки на понравившихся авторов и отслеживание их записей. Покрытие тестами. Возможность добавления изображений.

* Инструментарий:
  * Django 2.2
  * Python 3.8
  * Django Unittest
  * Django debug toolbar
  * PostgreSQL
  * Django ORM

* Запуск:
  * Установка зависимостей:
    * `pip install -r requirements.txt`
  * Применение миграций:
    * `python manage.py makemigrations`
    * `python manage.py migrate`
  * Создание администратора:
    * `python manage.py createsuperuser`
  * Запуск приложения:
    * `python manage.py runserver`
