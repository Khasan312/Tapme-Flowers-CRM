# Размещение и восстановление

Серверная конфигурация подготовлена и проверена сборкой; внешний сервер пока
не развёрнут. Нужны Linux с Docker/Compose, домен с DNS на сервер и открытые
порты 80/443. Доступ к PostgreSQL и Redis наружу не публикуется.

## Первый запуск сервера

Создайте `.env.production` из `.env.production.example`, укажите настоящий
`PUBLIC_DOMAIN` и отдельные случайные пароли/секрет. Файл не помещайте в Git,
ограничьте права командой `chmod 600 .env.production`. Не переносите локальные
пароли в публичное окружение.

Все команды ниже выполняются из корня копии проекта на сервере:

```bash
docker compose --env-file .env.production -f compose.production.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml build
docker compose --env-file .env.production -f compose.production.yaml up -d --wait postgres redis
docker compose --env-file .env.production -f compose.production.yaml run --rm api python manage.py migrate
docker compose --env-file .env.production -f compose.production.yaml run --rm api python manage.py collectstatic --noinput
docker compose --env-file .env.production -f compose.production.yaml run --rm api python manage.py bootstrap_business --name 'Название магазина' --username owner
docker compose --env-file .env.production -f compose.production.yaml up -d --wait
```

Caddy получает сертификат для указанного домена, проксирует API, раздаёт SPA
и статику Django. Gunicorn запускается непривилегированным пользователем;
Django использует Secure/HttpOnly-сессию, CSRF и HTTPS redirect. Только Caddy
имеет опубликованные порты и передаёт доверенный заголовок схемы запроса.

Проверьте вход по HTTPS, создание заказа, загрузку и чтение фото, работу
флориста/курьера, страницу статуса и сохранность после пересоздания контейнеров.
В настройках заполните телефон, адрес, часовой пояс и окна магазина; добавьте
команду и импортируйте пробную часть базы с предпросмотром.

При обновлении сначала сделайте резервную копию, затем пересоберите образы,
примените миграции, соберите статику и повторите `up`. Не запускайте несколько
экземпляров beat: планировщик нужен один. Повтор генерации напоминаний безопасен.

## Фотографии

По умолчанию фото лежат в закрытом томе `photos`. Том не раздаётся веб-сервером.
Для S3-совместимого провайдера задайте переменные из `.env.production.example`,
закройте публичный доступ к bucket и выдайте учётной записи только нужный bucket.
Облачный адаптер предусмотрен, но с реальным провайдером ещё не проверялся.
Переход требует переноса фото с прежними ключами; переключение настройки само
по себе не копирует данные. Команды export/import ниже работают через Storage.

## Копирование и проверка восстановления

```bash
python3 scripts/backup.py --compose-file compose.production.yaml --env-file .env.production
python3 scripts/verify_backup.py backups/ИМЯ_КОПИИ --compose-file compose.production.yaml --env-file .env.production
```

Копия содержит `database.dump`, `photos.zip`, `manifest.json` с SHA-256.
Секреты окружения не копируются: храните их отдельно в защищённом месте.
Проверка создаёт временную БД со случайным именем, восстанавливает дамп,
проверяет схему/число записей, соответствие фото ключам, распаковывает фото
во временную директорию и удаляет только созданную тестовую БД.

Рабочая БД при проверке не изменяется. Для согласованного снимка при переносе
магазина остановите запись через API/worker на время копирования; обычный
`pg_dump` даёт согласованный снимок БД, но экспорт фото выполняется следующим шагом.
Скрипт не приостанавливает запись автоматически.

До пилота назначьте ежедневный запуск этих команд на сервере, срок хранения,
копирование за пределы сервера и уведомление о неуспехе. Сейчас системный таймер,
внешнее место копий и канал уведомлений не установлены. Одна копия на диске
этого компьютера не защищает от потери компьютера.

## Восстановление после сбоя

Сначала выполните `verify_backup.py`. Поднимите отдельное окружение восстановления
с пустыми томами; не восстанавливайте поверх действующего магазина.
Используйте сохранённые секреты и ту же версию кода, которая создала копию.
Остановите API/worker/beat этого окружения, запустите только PostgreSQL/Redis.

Для пустой БД выбранного окружения (пути замените на конкретную копию):

```bash
docker compose --env-file .env.production -f compose.production.yaml exec -T postgres sh -c 'pg_restore --exit-on-error --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/ИМЯ_КОПИИ/database.dump
docker compose --env-file .env.production -f compose.production.yaml run --rm -T api python manage.py import_photos < backups/ИМЯ_КОПИИ/photos.zip
docker compose --env-file .env.production -f compose.production.yaml run --rm -T api python manage.py import_photos --apply < backups/ИМЯ_КОПИИ/photos.zip
```

Первая команда фото только проверяет архив и показывает количество.
`--apply` восстанавливает отсутствующие файлы с исходными ключами, пропускает
совпадающие и отказывается перезаписывать другое содержимое. Затем примените
нужные миграции, `collectstatic`, запустите окружение и проверьте вход/заказы/фото.
Только после проверки переключайте домен на восстановленное окружение.

Сиротские фото после аварии: `manage.py cleanup_orphan_photos` показывает число
несвязанных файлов старше суток; удаление требует явного `--apply`.

## Доступ и наблюдение

Владелец меняет пароль через кнопку своего логина; сбрасывает пароль обычного
сотрудника в «Настройках». Восстановление забытого пароля владельца выполняется
через сервер с двойным скрытым вводом:

```bash
docker compose --env-file .env.production -f compose.production.yaml exec api python manage.py recover_owner --username owner
```

Сброс владельца не доступен менеджеру. Если пользователь принадлежит нескольким
бизнесам, его глобальный пароль также нельзя сбрасывать владельцу одного бизнеса.
Почтовое восстановление не настроено: провайдер почты пока не выбран.

`GET /health/` выполняет запрос к БД, отдаёт 200 или 503 без деталей ошибки.
Проверяйте HTTPS `/health/` внешним монитором; контейнеры имеют restart policy.
Отдельно наблюдайте место на диске, возраст последней проверенной копии и Celery:

```bash
docker compose --env-file .env.production -f compose.production.yaml ps
docker compose --env-file .env.production -f compose.production.yaml exec worker celery -A config.celery:app inspect ping --timeout 5
docker compose --env-file .env.production -f compose.production.yaml logs --tail=100 api worker beat
```

Access log API содержит IP, код ответа и длительность, не URL публичного токена.
Удалённый сбор ошибок и уведомления внешнего монитора подключаются после выбора
площадки. Проверка локальной сборки не заменяет испытание HTTPS/DNS, S3 и
восстановления на реальном сервере.

Для подготовленного сервера с GitHub Actions Runner используйте [CI/CD](CI_CD.md).
