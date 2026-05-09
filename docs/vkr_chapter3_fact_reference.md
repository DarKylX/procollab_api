# Фактологическая справка для главы 3 ВКР: PROCOLLAB

Дата подготовки: 06.05.2026.

Источник фактов: локальные репозитории `Z:\VKR\procollab_api` и `Z:\VKR\procollab_front`, локальная база `procollab_api\db.sqlite3`, результаты запусков команд в рабочей среде.

Назначение документа: техническая справка для написания разделов 3.1-3.3 ВКР по проекту "Веб-приложение для организации и проведения кейс-чемпионатов". Документ не является академическим текстом; это набор проверенных фактов, таблиц, статусов и ссылок на код.

## 1. Общая сводка готовности

Статусы используются в практическом смысле:

- `Реализовано` - есть модели/API/сервисы/компоненты, сценарий можно описывать как внедренный.
- `Частично реализовано` - основная логика есть, но есть ограничения, незавершенный UI, непримененная локальная миграция или тестовый дефект.
- `Заготовка/placeholder` - видимое место в интерфейсе или коде есть, но функция не завершена.
- `Не найдено в коде` - при обследовании backend/frontend подтверждения реализации не найдено.

| Функция | Статус | Подтверждение в коде | Ограничения / замечания |
|---|---|---|---|
| Создание кейс-чемпионата | Реализовано | Backend: `partner_programs.views.PartnerProgramList.post`, `partner_programs.models.PartnerProgram`; frontend: `office/program/new`, `WizardComponent`, `BasicInfoStepComponent`, `ProgramService.create` | Создание проходит через мастер и статусную модель программы |
| Сохранение черновика | Реализовано | `PartnerProgram.status`, legacy-поле `draft`; frontend: `WizardStateService`, `ProgramEditStateService`, `ProgramEditComponent.canDeactivate` | Поле `draft` сохранено как совместимость, основная логика завязана на статусы |
| Редактирование программы | Реализовано | `PartnerProgramDetail.patch`; frontend tabs `main`, `schedule`, `materials`, `registration`, `criteria`, `verification`, `certificate` | Вкладка `certificate` в frontend пока заглушка |
| Настройка формы регистрации | Реализовано | `PartnerProgramField`, `PartnerProgramFieldValue`, `PartnerProgramSchemaView`, `PartnerProgramRegisterView`; frontend `RegistrationStepComponent`, `ProgramEditRegistrationComponent` | Поддерживаются кастомные поля и значения заявок |
| Регистрация участника на программу | Реализовано | `PartnerProgramUserProfile`, `PartnerProgramRegisterView`, `RegisterToProgramNewView`; frontend `ProgramRegisterComponent` | Есть связь пользователь-программа и данные анкеты |
| Подача проекта на чемпионат | Реализовано | `PartnerProgramProject`, `PartnerProgramProjectSubmitView`, `applyProjectToProgram`, `submitCompettetiveProject` | Учитываются правила индивидуального/командного участия |
| Модерация программы | Реализовано | `moderation.services.submit_program_to_moderation`, `approve_program`, `reject_program`; frontend `AdminModeration*`, `moderationStaffGuard` | Старые тесты readiness ожидают прежний формат ошибок и сейчас падают |
| Проверка готовности программы | Реализовано | `partner_programs.services.get_program_readiness_payload`, `ReadinessWidgetComponent`, `ProgramService.getReadiness` | Readiness разделен на обязательную готовность к модерации и операционную готовность |
| Верификация компании | Частично реализовано | Backend: `PartnerProgramVerificationRequest`, `verification_services.py`, `moderation.views.*Verification*`; frontend `ProgramEditVerificationComponent`, admin routes verification | Локальная миграция `partner_programs.0022_verification_request_snapshot_fields` не применена; в локальной БД 0 заявок |
| Экспертная оценка проектов | Частично реализовано | `Criteria`, `ProjectScore`, `ProjectExpertAssignment`, `ProjectEvaluation`, `ProjectEvaluationScore`; frontend `ExpertEvaluationListComponent`, `ExpertEvaluationDetailComponent`, `ProjectRatingService` | Локальная миграция `project_rates.0005_projectevaluation_projectevaluationscore` не применена; legacy-оценки `ProjectScore` есть |
| Сертификаты | Частично реализовано | Backend: `certificates.models`, `certificates.services`, routes `/certificate-template/`, `/certificates/generate/`, public verify; frontend route `edit/certificate` | Backend готовит PDF и хранит сертификаты, но frontend-вкладка сертификатов - `ProgramEditPlaceholderComponent`; в локальной БД сертификатов 0 |
| Email-уведомления | Частично реализовано | `UserNotificationPreferences`, `moderation.services`, `verification_services.py`, `certificates.services`, `mailing.tasks` | Реализованы email-предпочтения и отправка; полноценный in-app центр уведомлений для этих сценариев не подтвержден |
| Закрытые чемпионаты и приглашения | Частично реализовано | `PartnerProgramInvite`, `invite_urls.py`, `services.create_program_invite`, `accept_program_invite`, `resend_program_invite` | Backend API реализован; отдельный полноценный UI управления приглашениями в найденных frontend-компонентах не подтвержден |
| Аналитика и выгрузки | Реализовано | `PartnerProgramAnalyticsView`, `PartnerProgramAnalyticsExportView`, `export_program_projects`, `export_program_rates`; frontend `ProgramAnalyticsComponent` | Выгрузка XLSX используется в `ProgramService.exportAnalytics` |
| API-документация Swagger/ReDoc | Реализовано | `procollab.urls`: `/swagger/`, `/redoc/`, `/swagger.json` | Доступ только staff/admin; при генерации схемы есть предупреждение по `ProjectListForRate` |

## 2. Backend: структура и технологии

### 2.1. Технологический стек

| Область | Факт |
|---|---|
| Язык | Python 3.11.15 при запуске через Poetry |
| Менеджер зависимостей | Poetry 2.3.4 |
| Web framework | Django 4.1.3 |
| API | Django REST Framework 3.14.0 |
| JWT | `djangorestframework-simplejwt` |
| API-документация | `drf-yasg`, маршруты `/swagger/`, `/redoc/`, `/swagger.json` |
| Async/WebSocket база | `channels`, `daphne`, `channels-redis` |
| Очереди и расписание | Celery 5.4.0, `django-celery-beat`, Redis broker |
| DB в DEBUG | SQLite `db.sqlite3` |
| DB вне DEBUG | PostgreSQL через переменные окружения |
| Кэш в DEBUG | `django.core.cache.backends.filebased.FileBasedCache` |
| Кэш вне DEBUG | Redis через `django_redis.cache.RedisCache` |
| Файлы в DEBUG | локальное хранилище через `LocalFileSystemStorage` |
| Файлы вне DEBUG | Selectel Swift storage |
| Email | Unisender Go через `anymail.backends.unisender_go.EmailBackend` |
| PDF | WeasyPrint |
| Табличные выгрузки | `tablib[xlsx]`, `pandas` |

Основной файл настроек: `procollab/settings.py`.

### 2.2. Backend-приложения

| Django app | Назначение | Ключевые файлы |
|---|---|---|
| `partner_programs` | Жизненный цикл кейс-чемпионата: создание, регистрация, проекты, заявки, приглашения, readiness | `models.py`, `views.py`, `serializers.py`, `services.py`, `verification_services.py`, `urls.py`, `invite_urls.py`, `tasks.py` |
| `moderation` | Административная модерация программ и заявок на верификацию | `views.py`, `serializers.py`, `services.py`, `urls.py`, `tasks.py` |
| `project_rates` | Критерии, экспертные назначения, оценки проектов | `models.py`, `views.py`, `serializers.py`, `services.py`, `validators.py`, `urls.py` |
| `certificates` | Шаблоны сертификатов, генерация PDF, выдача, публичная проверка | `models.py`, `views.py`, `serializers.py`, `services.py`, `tasks.py`, `urls.py` |
| `users` | Пользователи, роли, JWT-аутентификация, предпочтения уведомлений | `models.py`, `views.py`, `serializers.py`, `authentication.py`, `permissions.py`, `urls.py` |
| `projects` | Проекты участников и компании | `models.py`, `views.py`, `serializers.py`, `urls.py` |
| `files` | Загрузка, хранение и удаление файлов | `models.py`, `service.py`, `views.py`, `storage.py`, `urls.py` |
| `mailing` | Рассылки по программам | `tasks.py`, модели/сервисы рассылок |

### 2.3. Модели предметной области

| Модель | Файл | Основные поля и связи | Назначение |
|---|---|---|---|
| `PartnerProgram` | `partner_programs/models.py` | `name`, `tag`, `description`, `status`, `readiness`, `is_competitive`, `is_private`, `verification_status`, `participation_format`, `team_min_size`, `team_max_size`, даты старта/окончания/регистрации, `company -> Company`, M2M `users`, M2M `managers` | Центральная сущность кейс-чемпионата |
| `PartnerProgramUserProfile` | `partner_programs/models.py` | `user`, `partner_program`, `project`, `partner_program_data`, timestamps; unique `user + partner_program` | Регистрация пользователя на программу и хранение анкеты |
| `PartnerProgramProject` | `partner_programs/models.py` | `partner_program`, `project`, `submitted`, `datetime_submitted`; unique `partner_program + project` | Привязка проекта к чемпионату и статус подачи |
| `PartnerProgramField` | `partner_programs/models.py` | `partner_program`, `name`, `label`, `field_type`, `is_required`, `help_text`, `show_filter`, `options`; unique `partner_program + name` | Настраиваемые поля регистрации |
| `PartnerProgramFieldValue` | `partner_programs/models.py` | `program_project`, `field`, `value_text`; unique `program_project + field` | Значения дополнительных полей для проекта |
| `PartnerProgramMaterial` | `partner_programs/models.py` | `program`, `title`, `url`, `file -> UserFile`, timestamps | Материалы программы |
| `PartnerProgramInvite` | `partner_programs/models.py` | `program`, `email`, `token`, `status`, `accepted_at`, `expires_at`, `accepted_by`, `created_by` | Приглашения в закрытые программы |
| `PartnerProgramVerificationRequest` | `partner_programs/models.py` | `program`, `company`, `initiator`, `decided_by`, snapshot-поля компании, контакты, `status`, `documents` M2M `UserFile` | Заявка на верификацию компании |
| `ModerationLog` | `moderation/models.py` | `program`, `author`, `action`, `status_before`, `status_after`, `comment`, `rejection_reason`, `sections_to_fix` | История действий модерации |
| `Criteria` | `project_rates/models.py` | `partner_program`, `name`, `description`, `type`, `min_value`, `max_value`, `weight` | Критерии оценки |
| `ProjectScore` | `project_rates/models.py` | `criteria`, `user`, `project`, `value`; unique `criteria + user + project` | Legacy-оценка по критерию |
| `ProjectExpertAssignment` | `project_rates/models.py` | `partner_program`, `project`, `expert`; unique `partner_program + project + expert` | Назначение эксперта на проект |
| `ProjectEvaluation` | `project_rates/models.py` | `program_project`, `user`, `status`, `comment`, `total_score`, `submitted_at`; unique `program_project + user` | Новая сущность экспертной оценки заявки |
| `ProjectEvaluationScore` | `project_rates/models.py` | `evaluation`, `criterion`, `value`; unique `evaluation + criterion` | Баллы внутри новой экспертной оценки |
| `ProgramCertificateTemplate` | `certificates/models.py` | `program`, `background_image`, `font_family`, цвета, `fields_positioning`, условия выдачи | Настройка шаблона сертификата |
| `CertificateGenerationRun` | `certificates/models.py` | `program`, `status`, counters, `error_message`, timestamps | Запуск массовой генерации |
| `IssuedCertificate` | `certificates/models.py` | `program`, `user`, `pdf_file`, `team_name`, `final_score`, `rating_position`, `certificate_uuid`; unique `program + user` | Выданный сертификат |
| `UserNotificationPreferences` | `users/models.py` | one-to-one `user`, email-флаги, `inapp_notifications_enabled` | Настройки уведомлений пользователя |
| `CustomUser` | `users/models.py` | `email`, `user_type`, профильные поля, `last_activity` | Основная модель пользователя |
| `Expert` | `users/models.py` | one-to-one `user`, `preferred_industries`, `useful_to_project`, M2M `programs` | Профиль эксперта |
| `Company` | `projects/models.py` | `name`, `inn` | Компания |
| `Project` | `projects/models.py` | название/описание/отрасль/стадия, `leader`, M2M `subscribers`, M2M `companies` | Проект участника |
| `UserFile` | `files/models.py` | `link`, `user`, `name`, `extension`, `mime_type`, `size`, `datetime_uploaded` | Метаданные загруженных файлов |

### 2.4. Миграции и состояние локальной БД

Команда проверки миграций:

```powershell
$env:DEBUG='True'; poetry run python manage.py makemigrations --check --dry-run
```

Результат: `No changes detected`.

Команда проверки примененности миграций:

```powershell
$env:DEBUG='True'; poetry run python manage.py showmigrations partner_programs project_rates moderation certificates users projects files
```

Найденные непримененные миграции в локальной БД:

| App | Миграция | Влияние |
|---|---|---|
| `partner_programs` | `0022_verification_request_snapshot_fields` | В коде есть snapshot-поля заявки верификации, но локальная SQLite-БД еще не применяет эту миграцию |
| `project_rates` | `0005_projectevaluation_projectevaluationscore` | В коде есть новые модели `ProjectEvaluation` и `ProjectEvaluationScore`, но локальная SQLite-БД еще не содержит их таблицы |

Технический вывод: для демонстрации и тестовой эксплуатации нужно выполнить `python manage.py migrate` перед использованием верификации и новой модели экспертной оценки.

### 2.5. API-маршруты

Главный файл маршрутов: `procollab/urls.py`.

| Группа | Маршруты | Классы / функции | Назначение |
|---|---|---|---|
| API-документация | `/swagger/`, `/redoc/`, `/swagger.json`, `/swagger.yaml` | `drf_yasg.get_schema_view` | Документация API для staff/admin |
| Программы | `/programs/`, `/programs/<pk>/` | `PartnerProgramList`, `PartnerProgramDetail` | Список, создание, просмотр, редактирование |
| Readiness | `/programs/<pk>/readiness/` | `PartnerProgramReadinessView` | Проверка готовности программы |
| Аналитика | `/programs/<pk>/analytics/`, `/programs/<pk>/analytics/export/` | `PartnerProgramAnalyticsView`, `PartnerProgramAnalyticsExportView` | Метрики и XLSX-выгрузка |
| Критерии | `/programs/<pk>/criteria/`, `/programs/<pk>/criteria/<criterion_id>/` | `ProgramCriteriaListCreateView`, `ProgramCriteriaDetailView` | Управление критериями |
| Эксперты | `/programs/<pk>/experts/`, `/programs/<pk>/experts/search/`, `/programs/<pk>/experts/<user_id>/` | expert views в `partner_programs.views` | Назначение и поиск экспертов |
| Регистрация | `/programs/<pk>/schema/`, `/programs/<pk>/register/`, `/programs/<pk>/register_new/` | `PartnerProgramSchemaView`, `PartnerProgramRegisterView`, `RegisterToProgramNewView` | Получение формы и регистрация |
| Проекты программы | `/programs/<pk>/projects/`, `/programs/<pk>/projects/apply/`, `/programs/projects/filter/` | project views в `partner_programs.views` | Просмотр, фильтрация, подача проекта |
| Подача проекта | `/programs/partner-program-projects/<pk>/submit/` | `PartnerProgramProjectSubmitView` | Финальная подача проекта на оценку |
| Модерация программы | `/programs/<pk>/submit-to-moderation/`, `/withdraw-from-moderation/` | moderation submit/withdraw views | Отправка и отзыв из модерации |
| Верификация | `/programs/<pk>/verification/`, `/programs/<pk>/verification/submit/` | verification views в `partner_programs.views` | Заявка компании на верификацию |
| Приглашения | `/programs/<pk>/invites/`, `/programs/<pk>/invites/<invite_id>/revoke/`, `/resend/` | invite views | Управление приглашениями |
| Public invite | `/api/invites/<token>/`, `/api/invites/<token>/accept/`, `/invite/<token>/` | `PartnerProgramInviteDetailView`, `PartnerProgramInviteAcceptView` | Просмотр и принятие приглашения |
| Admin moderation | `/api/admin/moderation/programs/`, `/<id>/decision/`, `/freeze/`, `/restore/`, `/archive/` | `moderation.views` | Админская модерация программ |
| Admin verification | `/api/admin/moderation/verification/requests/`, `/<id>/decision/`, rejection reasons | `moderation.views.*Verification*` | Админская проверка компаний |
| Сертификаты | `/programs/<pk>/certificate-template/`, `/preview/`, `/stats/`, `/certificates/generate/`, `/my-certificate/` | `certificates.views` | Шаблон, предпросмотр, генерация, получение |
| Публичная проверка сертификата | `/api/public/certificates/verify/<uuid>/`, `/certificates/verify/<uuid>/` | certificate verification views | Проверка подлинности сертификата |
| Оценка проектов | `/rate-project/expert/evaluations/`, `/rate-project/<program_id>/submissions/`, `/draft/`, `/submit/`, `/rate/<project_id>` | `project_rates.views` | Экспертные списки, черновик и отправка оценки |
| Настройки уведомлений | `/auth/users/me/notification-preferences/` | `UserNotificationPreferencesView` | Настройки email/in-app уведомлений |

### 2.6. Сервисная логика

| Сервис / модуль | Ключевые функции | Реализованная логика |
|---|---|---|
| `partner_programs.services` | `get_program_readiness_payload`, `get_moderation_submission_errors` | Проверка обязательных секций: `basic_info`, `dates`, `registration`, `visual_assets`; расчет процента готовности; разделение на moderation readiness и operational readiness |
| `partner_programs.services` | `create_program_invite`, `send_program_invite`, `resolve_program_invite`, `accept_program_invite`, `revoke_program_invite`, `resend_program_invite` | Закрытые приглашения по email/token, принятие приглашения, повторная отправка |
| `partner_programs.services` | `validate_project_team_size_for_program` | Проверка формата участия и ограничений размера команды |
| `partner_programs.services` | `publish_finished_program_projects` | Автопубликация проектов после завершения программы при включенном флаге |
| `partner_programs.services` | `export_program_projects`, `export_program_rates` | Табличные выгрузки проектов и оценок |
| `partner_programs.verification_services` | `submit_verification_request`, `approve_verification_request`, `reject_verification_request`, `revoke_program_verification` | Верификация компании, логирование в `ModerationLog`, email-уведомления |
| `moderation.services` | `submit_program_to_moderation`, `approve_program`, `reject_program`, `withdraw_from_moderation` | Статусный процесс модерации программы |
| `moderation.services` | `freeze_stale_programs`, `freeze_program`, `restore_program`, `archive_program` | Автоматическая и ручная заморозка, восстановление и архивирование |
| `certificates.services` | `validate_background_file`, `upload_template_background`, `render_certificate_pdf`, `issue_certificate` | Валидация шаблона, генерация PDF, загрузка файла, создание сертификата |
| `certificates.services` | `generate_certificates_for_program`, `get_program_certificate_stats` | Массовая генерация и статистика сертификатов |
| `project_rates.validators` | `validate_score_value` | Проверка типа и диапазона оценки по критерию |
| `files.service` | `upload_file`, `delete_file`, storage classes | Локальное/Selectel-хранилище, обработка изображений, сохранение `UserFile` |

### 2.7. Celery-задачи

Файл расписания: `procollab/celery.py`.

| Задача | Расписание | Назначение |
|---|---|---|
| `vacancy.tasks.email_notificate_vacancy_outdated` | каждую минуту | Уведомления по устаревшим вакансиям |
| `mailing.tasks.run_program_mailings` | ежедневно 10:00 | Запуск программных рассылок |
| `partner_programs.tasks.publish_finished_program_projects_task` | ежедневно 06:00 | Публикация проектов завершенных программ |
| `moderation.tasks.freeze_stale_programs` | ежедневно 06:00 | Автозаморозка проблемных опубликованных программ |
| `partner_programs.tasks.send_readiness_reminders` | ежедневно 09:00 | Напоминания о готовности программы |
| `certificates.tasks.complete_finished_programs` | ежедневно 06:30 | Завершение программ и генерация сертификатов по условиям |
| `certificates.tasks.generate_certificates_for_program` | запуск из кода | Массовая генерация сертификатов |
| `certificates.tasks.generate_single_certificate` | запуск из кода | Генерация одного сертификата |

### 2.8. API-документация и доступ

Проверка через Django test client:

| URL | Анонимный доступ | Staff/admin доступ | Факт |
|---|---|---|---|
| `/swagger/` | 403 | 200 | HTML Swagger UI доступен только staff/admin |
| `/redoc/` | 403 | 200 | HTML ReDoc доступен только staff/admin |
| `/swagger.json` | 403 | 200 | JSON-схема доступна только staff/admin |

Замечание: при генерации схемы зафиксировано предупреждение по view `ProjectListForRate`: при `swagger_fake_view` не полностью обрабатывается отсутствие `program_id`. Сама схема при staff-доступе возвращается со статусом 200.

## 3. Frontend: структура и реализация Angular

### 3.1. Технологический стек

| Область | Факт |
|---|---|
| Framework | Angular 17 |
| UI | Angular Material/CDK, собственная библиотека `projects/ui` |
| Языки | TypeScript, HTML, SCSS |
| Приложение | `projects/social_platform` |
| Основной проект Angular | `social_platform` в `angular.json` |
| Команды | `npm run start:social`, `npm run build:social:dev`, `npm run test:ci` |
| Node в окружении проверки | bundled Node.js v24.14.0 |

Основной frontend-каталог сценариев программ: `procollab_front/projects/social_platform/src/app/office/program`.

### 3.2. Маршруты интерфейса

| Маршрут | Компоненты / модуль | Назначение |
|---|---|---|
| `/office/program` | `PROGRAM_ROUTES` | Корневой раздел программ |
| `/office/program/new` | `WizardComponent` | Мастер создания программы |
| `/office/program/new/basic-info` | `BasicInfoStepComponent` | Базовая информация |
| `/office/program/new/registration` | `RegistrationStepComponent` | Настройка регистрации |
| `/office/program/new/publish` | `PublishStepComponent` | Проверка и отправка |
| `/office/program/all` | `AllProgramsComponent` | Все доступные программы |
| `/office/program/my` | `MyProgramsComponent` | Программы пользователя |
| `/office/program/:programId` | `ProgramDetailMainComponent` with children | Страница программы |
| `/office/program/:programId/projects` | `ProgramListComponent`, `ProjectsFilterComponent` | Проекты программы |
| `/office/program/:programId/members` | members child route | Участники программы |
| `/office/program/:programId/register` | `ProgramRegisterComponent` | Регистрация на программу |
| `/office/program/:programId/edit` | `ProgramEditComponent` | Редактирование программы |
| `/office/program/:programId/edit/main` | `ProgramEditMainComponent` | Основные настройки |
| `/office/program/:programId/edit/schedule` | `ProgramEditScheduleComponent` | Расписание |
| `/office/program/:programId/edit/materials` | `ProgramEditMaterialsComponent` | Материалы |
| `/office/program/:programId/edit/registration` | `ProgramEditRegistrationComponent` | Поля регистрации |
| `/office/program/:programId/edit/criteria` | `ProgramEditCriteriaComponent` | Критерии и эксперты |
| `/office/program/:programId/edit/verification` | `ProgramEditVerificationComponent` | Верификация компании |
| `/office/program/:programId/edit/certificate` | `ProgramEditPlaceholderComponent` | Заглушка вкладки сертификата |
| `/office/program/:programId/analytics` | `ProgramAnalyticsComponent` | Аналитика |
| `/office/expert/evaluations` | expert evaluation routes/components | Кабинет эксперта |
| `/office/admin/moderation` | `MODERATION_ROUTES`, `moderationStaffGuard` | Админская модерация |

### 3.3. Компоненты раздела программ

| Компонент | Файл / группа | Назначение |
|---|---|---|
| `ProgramComponent` | `office/program/program.component.ts` | Layout раздела программ |
| `WizardComponent` | `office/program/pages/wizard` | Мастер создания |
| `WizardProgressComponent` | `office/program/components/wizard-progress` | Индикатор шагов |
| `BasicInfoStepComponent` | wizard step | Основная информация |
| `RegistrationStepComponent` | wizard step | Поля регистрации |
| `PublishStepComponent` | wizard step | Проверка готовности и публикация |
| `AllProgramsComponent` | pages/all-programs | Список всех программ |
| `MyProgramsComponent` | pages/my-programs | Программы пользователя |
| `ProgramCardComponent` | components/program-card | Карточка программы |
| `ProgramStatusBadgeComponent` | components/program-status-badge | Визуальный статус программы |
| `ReadinessWidgetComponent` | components/readiness-widget | Чеклист готовности |
| `VerificationBannerComponent` | components/verification-banner | Баннер верификации для менеджера |
| `ProgramDetailMainComponent` | pages/detail | Главная страница программы |
| `ProgramContextActionsComponent` | detail components | Контекстные действия менеджера/участника |
| `ProgramStatCardsComponent` | detail components | Статистические карточки |
| `ProgramListComponent` | projects list | Список проектов |
| `ProjectsFilterComponent` | projects filter | Фильтрация проектов |
| `ProgramRegisterComponent` | register page | Регистрация пользователя |
| `ProgramEditComponent` | edit shell | Оболочка редактирования и защита от потери изменений |
| `ProgramEditMainComponent` | edit/main | Основные поля |
| `ProgramEditScheduleComponent` | edit/schedule | Даты и расписание |
| `ProgramEditMaterialsComponent` | edit/materials | Материалы |
| `ProgramEditRegistrationComponent` | edit/registration | Анкета регистрации |
| `ProgramEditCriteriaComponent` | edit/criteria | Критерии и эксперты |
| `ProgramEditVerificationComponent` | edit/verification | Заявка на верификацию |
| `ProgramEditPlaceholderComponent` | edit/certificate | Placeholder для настройки сертификата |
| `ProgramAnalyticsComponent` | analytics | Аналитика и выгрузка |
| `ExpertEvaluationListComponent` | expert evaluations | Список назначенных оценок |
| `ExpertEvaluationDetailComponent` | expert evaluation detail | Оценка конкретной заявки |
| `RatingCardComponent` | rating UI | Карточка оценки |
| `ProgramNewsCardComponent` | news UI | Новости программы |

### 3.4. Frontend-сервисы

| Сервис | Ключевые методы | Назначение |
|---|---|---|
| `ProgramService` | `getAll`, `getActual`, `getOne`, `create`, `update`, `getReadiness`, `submitToModeration`, `getAnalytics`, `exportAnalytics` | Основной HTTP-сервис программ |
| `ProgramService` | `getCriteria`, `createCriterion`, `updateCriterion`, `deleteCriterion`, `getProgramExperts`, `searchExperts`, `addProgramExpert`, `deleteProgramExpert` | Критерии и эксперты |
| `ProgramService` | `getDataSchema`, `register`, `getAllProjects`, `applyProjectToProgram`, `submitCompettetiveProject` | Регистрация и проекты |
| `ProjectRatingService` | `getExpertEvaluationPrograms`, `getSubmissions`, `getSubmission`, `saveDraft`, `submitEvaluation`, `rate` | Экспертная оценка |
| `ProgramNewsService` | `fetchNews`, `readNews`, `toggleLike`, `addNews`, `editNews`, `deleteNews` | Новости программы |
| `ProgramEditStateService` | signals `savedProgram`, `currentProgram`, `dirtyTabs`, `canSave`, `saveCurrent`, `reset` | Состояние формы редактирования |
| `WizardStateService` | `setBasicInfo`, `setRegistration`, `setDraftId`, `setStepValidity`, `reset` | Состояние мастера создания |
| `ModerationService` | `getPrograms`, `getProgram`, `decide`, `getVerificationRequests`, `decideVerification` | Админская модерация |
| `RoleResolverService` | role resolution methods | Определение ролей пользователя в программе |

### 3.5. Верификация во frontend

Компонент `ProgramEditVerificationComponent` реализует не заглушку, а рабочую форму:

- ввод данных компании и контактов;
- проверка ИНН по шаблону 10 или 12 цифр;
- описание роли/оснований;
- подтверждающий checkbox;
- загрузка до 5 файлов через `FileService.uploadFile({ preserveOriginal: true })`;
- ограничение файла до 10 MB;
- разрешенные форматы PDF, PNG, JPG, JPEG;
- отображение статусов `pending`, `verified`, `rejected`, `revoked`;
- повторная отправка после отказа;
- отображение истории/комментариев.

Компонент `VerificationBannerComponent` показывает менеджеру баннер, если у программы нет подтвержденной верификации. Баннер ведет на `/office/program/:id/edit/verification` и скрывается на 7 дней через `localStorage`.

### 3.6. Заглушки во frontend

| Место | Статус | Факт |
|---|---|---|
| `/office/program/:programId/edit/certificate` | Заготовка/placeholder | Используется `ProgramEditPlaceholderComponent`; текст указывает, что настройка будет доступна позднее и не обязательна для создания/модерации |

Backend сертификатов при этом реализован: модели, API, генерация PDF и публичная проверка существуют.

## 4. Тестирование и качество

### 4.1. Backend-проверки окружения

Команда:

```powershell
$env:DEBUG='True'; poetry run python manage.py check
```

Результат:

- Django system check: `System check identified no issues (0 silenced)`.
- Предупреждение: `DateTimeField Vacancy.datetime_created received a naive datetime`, связано с тестовыми/локальными данными вакансий при включенном time zone support.

Команда:

```powershell
$env:DEBUG='True'; poetry run python manage.py makemigrations --check --dry-run
```

Результат:

- `No changes detected`.
- То же предупреждение по naive datetime.

### 4.2. Backend unit/integration tests

Запуск:

```powershell
$env:DEBUG='True'
poetry run python manage.py test partner_programs moderation certificates project_rates users.tests.UserTestCase users.tests_filters projects.tests_program_participation_rules files.tests --verbosity 1
```

Результат:

| Показатель | Значение |
|---|---|
| Найдено тестов | 196 |
| Время Django test runner | 125.759 s |
| Итог | FAILED |
| Успешно | 193 теста по разнице |
| Ошибки | 0 |
| Падения assertions | 3 |

Падающие тесты:

| Тест | Файл/класс | Причина |
|---|---|---|
| `test_submit_to_moderation_rejects_missing_required_fields` | `partner_programs.tests.PartnerProgramReadinessAndModerationTests` | Тест ожидает ошибку по полю `name`, актуальная реализация возвращает секционные ошибки `basic_info`, `registration`, `visual_assets` |
| `test_submit_to_moderation_updates_status` | `partner_programs.tests.PartnerProgramReadinessAndModerationTests` | Тест ожидает 200, актуальный endpoint возвращает 400 из-за расширенных требований готовности |
| `test_html_page_returns_valid_certificate_details` | `certificates.tests_verification.PublicCertificateVerificationTests` | Ожидалась дата `04.05.2026`, HTML возвращает `05.05.2026`; вероятная причина - локальная дата/timezone при отображении |

Вывод для ВКР: backend-тесты в большинстве проходят, но набор тестов требует актуализации под новую модель readiness и уточнения правила отображения даты сертификата.

### 4.3. Frontend tests

Проверочный запуск без системного `npm`, через найденный bundled Node.js:

```powershell
& 'C:\Users\evsee\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' '.\node_modules\@angular\cli\bin\ng.js' test social_platform --browsers=Headless --no-watch
```

Результат: Karma стартует, но тестовый bundle не собирается. Итоговая ошибка: `Error: Found 1 load error`.

Основные причины компиляционного сбоя:

| Файл / область | Проблема |
|---|---|
| `courses.component.spec.ts` | spec импортирует несуществующий `TrackCareerComponent`, фактический компонент - `CoursesComponent` |
| `course-detail.component.spec.ts` | импорт `./trajectory-detail.component` не найден |
| `info.component.spec.ts` | spec ожидает `InfoComponent`, фактические классы отличаются |
| `complete.component.spec.ts` | spec ожидает `CompleteComponent`, фактический класс - `TaskCompleteComponent` |
| `lesson.component.spec.ts` | импорт `./task.component` не найден |
| `courses/list/list.component.spec.ts` | импорт из `@office/program/detail/rate-projects/list/list.component` не найден |
| `list.resolver.spec.ts` | импорт `./records.resolver` не найден |
| `course-module-card.component.spec.ts` | spec ожидает `SkillCardComponent`, фактический класс - `CourseModuleCardComponent` |
| `office/mentors/mentors.component.ts` | не найден `MemberCardComponent` |
| `collaborator-card.component.spec.ts` | spec ожидает `InviteCardComponent`, фактический класс - `CollaboratorCardComponent` |
| `vacancies/list/list.component.spec.ts` | импорт `./VacanciesList.component` не найден |
| `bar-new/bar.component.spec.ts` | spec ожидает `BarComponent`, фактический класс - `BarNewComponent` |
| `office/shared/header/header.component.scss` | SCSS не может импортировать `src/styles/responsive` |

Вывод: frontend-тесты не доходят до выполнения из-за старых/сломанных spec/import в разных модулях, не только в разделе кейс-чемпионатов.

### 4.4. Frontend spec-файлы по разделу программ

В разделе программ найдены spec-файлы, покрывающие:

| Файл / класс | Что проверяется |
|---|---|
| `program-analytics.component.spec.ts` | загрузка аналитики, участники, empty states, сортировка, фильтры, forbidden state, ссылки на проекты |
| `my-programs.component.spec.ts` | разделение программ пользователя по секциям, empty state |
| `readiness-widget.component.spec.ts` | отображение readiness, checklist, completed icons, retry, refresh |
| `program.service.spec.ts` | readiness, analytics, export xlsx, patch draft, submit moderation, my programs, approve program |
| `project-rating.service.spec.ts` | списки оценок эксперта, заявки, detail, draft, final submit |
| `role-resolver.service.spec.ts` | роли пользователя, гостевой доступ |
| `program-status-badge.component.spec.ts` | отображение статусов и размеров badge |
| `wizard-progress.component.spec.ts` | активный шаг, клики по завершенным шагам |
| `wizard-state.service.spec.ts` | сохранение basic info, registration, reset |

### 4.5. Приемочные сценарии для ручной проверки

| Сценарий | Ожидаемый результат | Статус по коду |
|---|---|---|
| Создать программу через `/office/program/new/basic-info` | Создается `PartnerProgram`, появляется draft/status | Реализовано |
| Настроить поля регистрации | Создаются `PartnerProgramField`, схема доступна через `/schema/` | Реализовано |
| Зарегистрировать пользователя на программу | Создается `PartnerProgramUserProfile` | Реализовано |
| Подать проект на чемпионат | Создается/обновляется `PartnerProgramProject`, выставляется `submitted` | Реализовано |
| Посмотреть readiness | Возвращается checklist, процент, `can_submit` | Реализовано |
| Отправить программу на модерацию | При выполнении обязательных секций меняется статус | Реализовано, тесты нужно обновить |
| Одобрить/отклонить программу администратором | Создается `ModerationLog`, статус меняется | Реализовано |
| Подать заявку на верификацию компании | Создается `PartnerProgramVerificationRequest`, отправляются уведомления | Частично: нужна локальная миграция |
| Оценить проект экспертом | Сохраняется draft/final оценка | Частично: новая модель требует миграции |
| Сгенерировать сертификаты | Создается `CertificateGenerationRun` и `IssuedCertificate`, PDF сохраняется как файл | Backend реализован, frontend UI заглушка |
| Проверить сертификат по UUID | Public endpoint возвращает данные сертификата | Реализовано, есть тестовый дефект по дате |
| Экспортировать аналитику | Возвращается XLSX | Реализовано |

## 5. Метрики проекта и локальной БД

Метрика подсчитана приблизительно по файлам репозиториев `procollab_api` и `procollab_front`. Исключались `.git`, `node_modules`, `dist`, `.angular`, `.cache`, `media`, `log`, `migrations`. Комментарии и пустые строки не учитывались.

| Метрика | Значение |
|---|---:|
| Всего файлов в подсчете | 1215 |
| Непустых некомментарных строк | 110461 |
| Приблизительное число функций/классов/методов | 5419 |
| Python-файлов | 324 |
| Python LOC | 35194 |
| TypeScript-файлов | 523 |
| TypeScript LOC | 34541 |
| HTML-файлов | 186 |
| HTML LOC | 18928 |
| SCSS-файлов | 182 |
| SCSS LOC | 21798 |

Локальная SQLite-БД:

| Метрика | Значение |
|---|---:|
| Таблиц приложения без системных `sqlite_%` | 104 |
| Всего записей в этих таблицах | 11983 |
| `partner_programs_partnerprogram` | 34 |
| `partner_programs_partnerprogramuserprofile` | 616 |
| `partner_programs_partnerprogramproject` | 57 |
| `partner_programs_partnerprogramfield` | 60 |
| `partner_programs_partnerprogramfieldvalue` | 150 |
| `partner_programs_partnerprogrammaterial` | 38 |
| `partner_programs_partnerprograminvite` | 0 |
| `partner_programs_partnerprogramverificationrequest` | 0 |
| `moderation_moderationlog` | 15 |
| `project_rates_criteria` | 117 |
| `project_rates_projectexpertassignment` | 48 |
| `project_rates_projectscore` | 228 |
| `certificates_programcertificatetemplate` | 0 |
| `certificates_certificategenerationrun` | 0 |
| `certificates_issuedcertificate` | 0 |
| `users_customuser` | 108 |
| `users_expert` | 22 |
| `users_expert_programs` | 52 |
| `users_usernotificationpreferences` | 108 |
| `projects_company` | 100 |
| `projects_project` | 85 |
| `projects_projectcompany` | 70 |
| `files_userfile` | 13 |

Интерпретация: в локальной БД есть демонстрационные данные по программам, пользователям, проектам, критериям, экспертам и оценкам; данных по сертификатам и приглашениям пока нет.

## 6. Скриншоты и артефакты

Найденные готовые изображения для иллюстраций ВКР:

| Файл | Что показывает |
|---|---|
| `Z:\VKR\artifacts\vkr_screenshots\01_swagger_programs.png` | Swagger / API программ |
| `Z:\VKR\artifacts\vkr_screenshots\02_redoc_api.png` | ReDoc / документация API |
| `Z:\VKR\artifacts\vkr_screenshots\09_wizard_basic.png` | Базовый шаг мастера создания программы |
| `Z:\VKR\artifacts\vkr_screenshots\10_registration_edit.png` | Редактирование регистрации |
| `Z:\VKR\artifacts\vkr_screenshots\10_wizard_registration.png` | Шаг регистрации в мастере |
| `Z:\VKR\artifacts\vkr_screenshots\11_my_programs.png` | Мои программы |
| `Z:\VKR\artifacts\vkr_screenshots\11_program_showcase.png` | Витрина программы |
| `Z:\VKR\artifacts\vkr_screenshots\12_program_page.png` | Страница программы |
| `Z:\VKR\artifacts\vkr_screenshots\13_program_projects.png` | Проекты программы |

Также есть старый вывод тестов: `Z:\VKR\artifacts\test_outputs\backend_selected_tests.txt`.

## 7. Дефекты, риски и что честно указать в ВКР

| Риск / дефект | Уровень | Факт | Рекомендация |
|---|---|---|---|
| Две локальные миграции не применены | Средний | `partner_programs.0022`, `project_rates.0005` не отмечены как applied | Выполнить `python manage.py migrate` перед демонстрацией |
| 3 backend-теста падают | Средний | 196 tests, 3 assertion failures | Обновить тесты readiness и правило даты сертификата |
| Frontend unit tests не собираются | Высокий для CI | Karma падает на старых spec/import/SCSS ошибках | Починить устаревшие spec и alias/import `src/styles/responsive` |
| Certificate frontend UI - placeholder | Средний | Вкладка `edit/certificate` использует `ProgramEditPlaceholderComponent` | Описывать сертификаты как backend-готовые, UI - направление доработки |
| Swagger schema warning | Низкий | `/swagger.json` возвращает 200, но есть warning по `ProjectListForRate` | Добавить обработку `swagger_fake_view` |
| Данных по сертификатам/приглашениям нет в локальной БД | Низкий | соответствующие таблицы имеют 0 записей | Для демонстрации создать тестовые записи |

## 8. Что можно уверенно писать в главе 3

### 8.1. Полностью реализовано

- Backend-модель кейс-чемпионата и связанные сущности: программа, участники, проекты, кастомные поля регистрации, материалы.
- REST API для создания, редактирования, просмотра программ, регистрации, подачи проектов, аналитики и выгрузок.
- Мастер создания программы во frontend.
- Страница программы, список проектов, фильтры, карточки, личный список программ.
- Readiness checklist для проверки готовности программы.
- Модерация программ администратором, включая статусы, логи и причины отклонения.
- Экспорт аналитики/проектов/оценок.
- API-документация Swagger/ReDoc с ограничением доступа staff/admin.

### 8.2. Реализовано частично или с условиями

- Верификация компании: backend и frontend-форма реализованы, но локально нужна миграция `partner_programs.0022`.
- Экспертная оценка: legacy-оценки и frontend-сценарии есть, новая модель `ProjectEvaluation` требует миграции `project_rates.0005`.
- Сертификаты: backend, PDF, API и публичная проверка реализованы; frontend-настройка сертификатов пока placeholder.
- Уведомления: email-предпочтения и отправка уведомлений есть, полноценный in-app сценарий не подтвержден.
- Закрытые приглашения: backend API и сервисы есть, полноценный frontend-экран управления приглашениями не подтвержден.

### 8.3. Что лучше вынести в направления развития

- Завершить frontend-интерфейс настройки сертификатов.
- Применить миграции и создать демонстрационные данные по верификации, приглашениям и сертификатам.
- Актуализировать backend-тесты readiness и сертификатов.
- Починить frontend unit tests, устаревшие spec-файлы и SCSS import.
- Добавить end-to-end тесты основных сценариев: создание программы, регистрация, подача проекта, модерация, оценка, сертификат.
- Расширить интерфейс управления закрытыми приглашениями.

## 9. Минимальные практические характеристики для текста ВКР

| Характеристика | Значение |
|---|---|
| Тип системы | Web-приложение для организации и проведения кейс-чемпионатов |
| Архитектура | Django REST backend + Angular frontend |
| Основные роли | участник, менеджер/организатор, эксперт, администратор/модератор |
| Основные сущности | программа, пользователь, компания, проект, анкета регистрации, критерий, оценка, сертификат |
| Документация API | Swagger/ReDoc |
| Фоновые задачи | Celery + Redis |
| Файловое хранилище | Local storage в DEBUG, Selectel Swift вне DEBUG |
| Email | Unisender Go |
| Генерация PDF | WeasyPrint |
| Локальные данные | 34 программы, 108 пользователей, 85 проектов, 117 критериев, 228 оценок |
| Backend-проверка | `manage.py check` успешно |
| Backend-тесты | 196 tests, 193 pass, 3 fail |
| Frontend-тесты | Не собираются из-за устаревших spec/import |

## 10. Короткий итог для автора ВКР

Система PROCOLLAB имеет реализованное ядро для кейс-чемпионатов: создание и редактирование программ, регистрационные формы, участие пользователей, подача проектов, модерация, readiness checklist, экспертные критерии, аналитика и API-документация. Backend также содержит развитые подсистемы верификации и сертификатов, включая сервисы, модели, API, Celery-задачи и PDF-генерацию.

Главные оговорки для честного описания: локально не применены две новые миграции, frontend-вкладка сертификатов пока является placeholder, frontend unit tests не собираются из-за устаревших spec-файлов, а backend test suite требует обновления трех тестов под текущую бизнес-логику.
