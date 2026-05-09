# Фактическая справка по реализации модуля автономных кейс-чемпионатов

## 1. Backend: модели, приложения, API и инфраструктура

### 1.1. Django-приложения, где расположен функционал

| Приложение | Назначение в модуле |
|---|---|
| `partner_programs` | Основная логика кейс-чемпионатов: создание, редактирование, публикация, регистрация, проекты чемпионата, приглашения, верификация компании, готовность чемпионата. |
| `moderation` | Административная модерация чемпионатов: одобрение, отклонение, заморозка, восстановление, архивация, журнал решений, модерация заявок на верификацию. |
| `certificates` | Шаблон сертификата, генерация сертификатов, выдача участникам, публичная проверка сертификата. |
| `project_rates` | Критерии оценки, экспертные оценки проектов, распределение проектов между экспертами. |
| `users` | Пользователи, эксперты, роли, настройки уведомлений, отслеживание активности. |
| `projects` | Проекты участников, команды, компании, партнерские ресурсы. |
| `files` | Загрузка файлов и интеграция с файловым хранилищем Selectel. |
| `mailing` | Сценарии email-рассылок по программам и дедлайнам. |
| `procollab` | Общие настройки Django, маршрутизация, Celery, Redis, PostgreSQL, Unisender Go, Selectel. |

### 1.2. Новые и измененные Django-модели

| Модель | Приложение | Статус | Назначение |
|---|---|---|---|
| `PartnerProgram` | `partner_programs` | изменена | Центральная сущность кейс-чемпионата. Добавлены/используются статус жизненного цикла, закрытость, компания-организатор, статус верификации, чек-лист готовности, журнал напоминаний. |
| `PartnerProgramVerificationRequest` | `partner_programs` | новая | Заявка на верификацию компании-организатора: компания, контактное лицо, документы, статус, решение администратора. |
| `PartnerProgramInvite` | `partner_programs` | новая | Приглашение в закрытый чемпионат: email, токен, статус, срок действия, автор и принявший пользователь. |
| `PartnerProgramUserProfile` | `partner_programs` | существующая/используется | Регистрация пользователя в чемпионате и хранение дополнительных регистрационных данных. |
| `PartnerProgramProject` | `partner_programs` | существующая/изменена | Связь чемпионата и проекта, признак сдачи проекта, дата сдачи, ограничение редактирования после сдачи. |
| `PartnerProgramField` | `partner_programs` | существующая/используется | Динамическое поле регистрационной формы чемпионата. |
| `PartnerProgramFieldValue` | `partner_programs` | существующая/используется | Значение динамического поля для проекта в чемпионате. |
| `PartnerProgramMaterial` | `partner_programs` | существующая/используется | Материалы чемпионата: ссылка или файл. |
| `ModerationLog` | `moderation` | новая | Журнал модерации: действие, статус до и после, комментарий, причина отклонения, автор решения. |
| `ProgramCertificateTemplate` | `certificates` | новая | Шаблон сертификата: фон, шрифт, цвета, расположение полей, условия выдачи. |
| `CertificateGenerationRun` | `certificates` | новая | Запуск массовой генерации сертификатов: статус, ожидаемое/выданное количество, ошибка. |
| `IssuedCertificate` | `certificates` | новая | Выданный сертификат: чемпионат, пользователь, итоговые данные, UUID, PDF-файл. |
| `Criteria` | `project_rates` | существующая/используется | Критерий оценки проекта в рамках чемпионата. |
| `ProjectScore` | `project_rates` | существующая/используется | Оценка проекта по критерию от эксперта. |
| `ProjectExpertAssignment` | `project_rates` | новая/расширенная | Назначение проекта конкретному эксперту в рамках чемпионата. |
| `UserNotificationPreferences` | `users` | новая | Настройки email- и внутренних уведомлений пользователя. |
| `Company` | `projects` | изменена | Компания-организатор или партнер; используется в верификации и связи с чемпионатом. |

### 1.3. Основные API-методы и view-классы

#### Кейс-чемпионаты (`partner_programs`)

| API | View | Назначение |
|---|---|---|
| `GET/POST /programs/` | `PartnerProgramList` | Список чемпионатов и создание нового чемпионата/черновика. |
| `GET/PATCH /programs/<id>/` | `PartnerProgramDetail` | Получение и редактирование чемпионата. |
| `GET /programs/<id>/readiness/` | `PartnerProgramReadinessView` | Получение чек-листа готовности. |
| `POST /programs/<id>/submit-to-moderation/` | `PartnerProgramSubmitToModerationView` | Отправка чемпионата на модерацию. |
| `POST /programs/<id>/withdraw-from-moderation/` | `PartnerProgramWithdrawFromModerationView` | Отзыв с модерации. |
| `GET /programs/<id>/verification/` | `PartnerProgramVerificationStatusView` | Просмотр статуса верификации компании. |
| `POST /programs/<id>/verification/submit/` | `PartnerProgramVerificationSubmitView` | Отправка заявки на верификацию. |
| `GET/POST /programs/<id>/invites/` | `PartnerProgramInviteListCreateView` | Список и создание приглашений в закрытый чемпионат. |
| `POST /programs/<id>/invites/<invite_id>/revoke/` | `PartnerProgramInviteRevokeView` | Отзыв приглашения. |
| `POST /programs/<id>/invites/<invite_id>/resend/` | `PartnerProgramInviteResendView` | Повторная отправка приглашения. |
| `DELETE /programs/<id>/invites/<invite_id>/` | `PartnerProgramInviteDeleteView` | Удаление приглашения. |
| `GET /api/invites/<token>/` | `PublicPartnerProgramInviteView` | Публичная информация по приглашению. |
| `POST /api/invites/<token>/accept/` | `PublicPartnerProgramInviteAcceptView` | Принятие приглашения. |
| `GET /invite/<token>/` | `PublicPartnerProgramInvitePageView` | HTML-страница приглашения. |
| `GET /programs/<id>/schema/` | `PartnerProgramDataSchema` | Схема регистрационных полей. |
| `POST /programs/<id>/register/` | `PartnerProgramRegister` | Регистрация текущего пользователя. |
| `POST /programs/<id>/register_new/` | `PartnerProgramCreateUserAndRegister` | Создание пользователя и регистрация в чемпионате. |
| `GET/POST /programs/<id>/projects/apply/` | `PartnerProgramProjectApplyView` | Получение дополнительных полей и подача проекта. |
| `POST /programs/partner-program-projects/<id>/submit/` | `PartnerProgramProjectSubmitView` | Сдача конкурсного проекта. |
| `GET /programs/<id>/projects/` | `PartnerProgramProjectsAPIView` | Список проектов чемпионата. |
| `POST /programs/<id>/projects/filter/` | `ProgramProjectFilterAPIView` | Фильтрация проектов по динамическим полям. |
| `GET /programs/<id>/filters/` | `ProgramFiltersAPIView` | Данные для фильтров проектов. |
| `GET /programs/<id>/export-projects/` | `PartnerProgramExportProjectsAPIView` | Экспорт проектов. |
| `GET /programs/<id>/export-rates/` | `PartnerProgramExportRatesAPIView` | Экспорт оценок. |
| `GET /api/companies/search/` | `CompanySearchView` | Поиск компании по названию или ИНН. |

#### Модерация (`moderation`)

| API | View | Назначение |
|---|---|---|
| `GET /api/admin/moderation/programs/` | `ModerationProgramListView` | Список чемпионатов для модерации. |
| `GET /api/admin/moderation/programs/<id>/` | `ModerationProgramDetailView` | Детальная карточка чемпионата для администратора. |
| `POST /api/admin/moderation/programs/<id>/decision/` | `ModerationDecisionView` | Одобрение или отклонение чемпионата. |
| `POST /api/admin/moderation/programs/<id>/freeze/` | `ModerationProgramFreezeView` | Заморозка чемпионата. |
| `POST /api/admin/moderation/programs/<id>/restore/` | `ModerationProgramRestoreView` | Восстановление чемпионата. |
| `POST /api/admin/moderation/programs/<id>/archive/` | `ModerationProgramArchiveView` | Архивация чемпионата. |
| `GET /api/admin/moderation/logs/` | `ModerationLogListView` | Журнал модерации. |
| `GET /api/admin/moderation/rejection-reasons/` | `RejectionReasonListView` | Справочник причин отклонения. |
| `GET /api/admin/moderation/verification-requests/` | `ModerationVerificationRequestListView` | Список заявок на верификацию. |
| `GET /api/admin/moderation/verification-requests/<id>/` | `ModerationVerificationRequestDetailView` | Детали заявки на верификацию. |
| `POST /api/admin/moderation/verification-requests/<id>/decision/` | `ModerationVerificationDecisionView` | Решение по заявке на верификацию. |
| `POST /api/admin/moderation/programs/<id>/verification/revoke/` | `ModerationVerificationRevokeView` | Отзыв верификации. |

#### Сертификаты (`certificates`)

| API | View | Назначение |
|---|---|---|
| `GET/PUT/DELETE /programs/<id>/certificate-template/` | `ProgramCertificateTemplateView` | Получение, сохранение и удаление шаблона сертификата. |
| `POST /programs/<id>/certificate-template/preview/` | `ProgramCertificateTemplatePreviewView` | Предпросмотр сертификата. |
| `GET /programs/<id>/certificate-template/stats/` | `ProgramCertificateGenerationStatsView` | Статистика генерации. |
| `POST /programs/<id>/certificates/generate/` | `ProgramCertificateGenerationStartView` | Запуск генерации сертификатов. |
| `GET /programs/<id>/my-certificate/` | `MyProgramCertificateView` | Получение сертификата текущего пользователя. |
| `DELETE /api/admin/certificates/<id>/` | `IssuedCertificateDeleteView` | Административное удаление сертификата. |
| `GET /api/public/certificates/verify/<uuid>/` | `PublicCertificateVerificationAPIView` | Публичная проверка сертификата по UUID. |
| `GET /certificates/verify/<uuid>/` | `PublicCertificateVerificationPageView` | Публичная HTML-страница проверки. |
| `GET /api/certificates/fonts/` | `CertificateFontListView` | Список доступных шрифтов. |

#### Экспертная оценка (`project_rates`)

| API | View | Назначение |
|---|---|---|
| `GET/POST /rate-project/<program_id>` | `ProjectListForRate` | Список проектов для оценки и фильтрация. |
| `POST /rate-project/rate/<project_id>` | `RateProject` | Отправка оценок проекта. |

#### Пользовательские настройки (`users`)

| API | View | Назначение |
|---|---|---|
| `GET/PATCH /auth/users/me/notification-preferences/` | `UserNotificationPreferencesView` | Получение и изменение настроек уведомлений. |

### 1.4. Фоновые задачи Celery

| Задача | Файл | Назначение | Расписание |
|---|---|---|---|
| `certificates.tasks.complete_finished_programs` | `certificates/tasks.py` | Перевод завершенных чемпионатов в статус завершения и запуск связанных процессов. | каждый день в 06:30 |
| `certificates.tasks.generate_certificates_for_program` | `certificates/tasks.py` | Массовая генерация сертификатов для чемпионата. | запускается из API/сервисов |
| `certificates.tasks.generate_single_certificate` | `certificates/tasks.py` | Генерация одного сертификата участника. | запускается из массовой генерации |
| `moderation.tasks.freeze_stale_programs` | `moderation/tasks.py` | Автоматическая заморозка чемпионатов, требующих реакции организатора. | каждый день в 06:00 |
| `partner_programs.tasks.publish_finished_program_projects_task` | `partner_programs/tasks.py` | Публикация проектов после завершения программы, если включена настройка. | каждый день в 06:00 |
| `partner_programs.tasks.send_readiness_reminders` | `partner_programs/tasks.py` | Напоминания организаторам о незаполненных шагах подготовки чемпионата. | каждый день в 09:00 |
| `mailing.tasks.run_program_mailings` | `mailing/tasks.py` | Сценарные рассылки по программам и дедлайнам. | каждый день в 10:00 |
| `vacancy.tasks.email_notificate_vacancy_outdated` | `vacancy/tasks.py` | Уведомления о просроченных вакансиях. | каждую минуту в текущей конфигурации |
| `users.tasks.send_mail_cv` | `users/tasks.py` | Отправка CV пользователя по email. | по запросу |

### 1.5. Внешние сервисы и инфраструктура

| Сервис | Где используется | Назначение |
|---|---|---|
| PostgreSQL | `settings.py`, `docker-compose.local.yml` | Основная производственная БД. В DEBUG используется SQLite. |
| Redis | `settings.py`, `docker-compose*.yml` | Celery broker/result backend, кэш, channel layer для WebSocket. |
| Selectel Object Storage / Swift API | `files/service.py`, `settings.py` | Хранение загружаемых файлов, изображений и документов. |
| Unisender Go через `django-anymail` | `settings.py`, `mailing`, email-сервисы | Транзакционные email-уведомления и рассылки. |
| Telegram Bot API | `events/helpers.py`, `settings.py` | Автопостинг/обновление сообщений о событиях в Telegram-канале. |
| Django Channels / Daphne | `asgi.py`, `settings.py`, `chats` | WebSocket-коммуникации, прежде всего чаты. |
| Celery + django-celery-beat | `procollab/celery.py`, `settings.py` | Фоновые и периодические задачи. |
| drf-yasg | `procollab/urls.py` | Swagger и ReDoc документация API. |
| Sentry | `.env.example` | Переменная `SENTRY_DSN` предусмотрена, но явной инициализации `sentry_sdk` в `settings.py` не обнаружено. |

### 1.6. Миграции, полезные для ER-диаграммы

| Приложение | Миграции |
|---|---|
| `partner_programs` | `0017_partnerprogram_company_partnerprogram_frozen_at_and_more.py`, `0018_data_migration_draft_to_status.py`, `0019_partnerprogramverificationrequest.py`, `0020_partnerprograminvite.py` |
| `moderation` | `0001_initial.py`, `0002_alter_moderationlog_action.py`, `0003_alter_moderationlog_action.py` |
| `certificates` | `0001_initial.py`, `0002_certificategenerationrun_issuedcertificate_and_more.py` |
| `users` | `0061_alter_customuser_about_me.py`, `0062_usernotificationpreferences.py`, `0063_create_existing_notification_preferences.py` |
| `projects` | `0033_alter_company_inn.py` |
| `project_rates` | `0003_projectexpertassignment.py` |

## 2. Frontend: раздел 3.2 «Разработка клиентского приложения»

### 2.1. Реализованные Angular-страницы

| Страница / маршрут | Файлы | Назначение |
|---|---|---|
| `/program/new/basic-info` | `program/wizard/steps/basic-info-step` | Первый шаг мастера создания чемпионата: базовая информация. |
| `/program/new/registration` | `program/wizard/steps/registration-step` | Настройка регистрации: внутренняя форма или внешняя ссылка. |
| `/program/new/publish` | `program/wizard/steps/publish-step` | Финальный шаг мастера, проверка готовности и создание/отправка. |
| `/program/all` | `program/main`, `main/sections/all-programs` | Витрина всех доступных чемпионатов. |
| `/program/my` | `program/main`, `main/sections/my-programs` | Список чемпионатов пользователя/организатора. |
| `/program/:programId` | `program/detail/main` | Детальная страница чемпионата. |
| `/program/:programId/projects` | `program/detail/list` | Список проектов чемпионата. |
| `/program/:programId/members` | `program/detail/list` | Список участников чемпионата. |
| `/program/:programId/projects-rating` | `program/detail/list`, `features/project-rating` | Экспертная оценка проектов. |
| `/program/:programId/register` | `program/detail/register` | Регистрация участника в чемпионате. |
| `/program/:programId/edit/main` | `program/edit/tabs/main` | Редактирование основных данных чемпионата. |
| `/program/:programId/edit/schedule` | `program/edit/tabs/schedule` | Редактирование сроков чемпионата. |
| `/program/:programId/edit/materials` | `program/edit/tabs/materials` | Управление материалами. |
| `/program/:programId/edit/registration` | `program/edit/tabs/registration` | Редактирование регистрационной формы. |
| `/program/:programId/edit/criteria` | `program/edit/tabs/criteria` | Критерии оценки и эксперты. |
| `/program/:programId/edit/verification` | `program/edit/tabs/placeholder` | Раздел верификации, пока подключен как placeholder. |
| `/program/:programId/edit/certificate` | `program/edit/tabs/placeholder` | Раздел сертификата, пока подключен как placeholder. |

### 2.2. Основные Angular-компоненты

| Компонент | Назначение |
|---|---|
| `WizardComponent` | Контейнер мастера создания чемпионата. |
| `WizardProgressComponent` | Индикатор прогресса мастера. |
| `BasicInfoStepComponent` | Форма базовой информации. |
| `RegistrationStepComponent` | Форма настройки регистрации. |
| `PublishStepComponent` | Финальная проверка и публикация/создание. |
| `ProgramMainComponent` | Общая страница списков чемпионатов. |
| `AllProgramsComponent` | Витрина всех чемпионатов. |
| `MyProgramsComponent` | Список чемпионатов пользователя. |
| `VerificationBannerComponent` | Баннер статуса верификации. |
| `ProgramCardComponent` | Карточка чемпионата. |
| `ProgramStatusBadgeComponent` | Визуальный статус чемпионата. |
| `ReadinessWidgetComponent` | Виджет готовности чемпионата. |
| `ProgramDetailMainComponent` | Основная вкладка детальной страницы чемпионата. |
| `ProgramContextActionsComponent` | Контекстные действия по чемпионату. |
| `ProgramMetaInfoComponent` | Метаданные чемпионата. |
| `ProgramStatCardsComponent` | Статистические карточки. |
| `ProgramListComponent` | Универсальный список проектов/участников/оценки. |
| `ProjectsFilterComponent` | Фильтры проектов чемпионата. |
| `ProgramRegisterComponent` | Регистрация пользователя в чемпионате. |
| `ProgramEditComponent` | Контейнер редактирования чемпионата. |
| `ProgramEditMainComponent` | Вкладка основных данных. |
| `ProgramEditScheduleComponent` | Вкладка сроков. |
| `ProgramEditMaterialsComponent` | Вкладка материалов. |
| `ProgramEditRegistrationComponent` | Вкладка регистрационной формы. |
| `ProgramEditCriteriaComponent` | Вкладка критериев и экспертов. |
| `ProgramEditPlaceholderComponent` | Заглушка для будущих вкладок верификации и сертификатов. |
| `RatingCardComponent` | Карточка экспертной оценки. |
| `ProjectRatingComponent` | UI оценки проекта. |
| `BooleanCriterionComponent`, `RangeCriterionInputComponent` | Поля критериев оценки. |

### 2.3. Как frontend ходит в API

Frontend использует Angular-сервисы, которые обращаются к backend через общий `ApiService` из `projects/core`. В сервисах формируются URL, query-параметры и DTO, а компоненты работают уже с Observable.

| Сервис | Основные методы | Backend API |
|---|---|---|
| `ProgramService` | `getAll`, `getMyPrograms`, `getOne`, `create`, `update`, `getReadiness`, `submitToModeration`, `withdrawFromModeration`, `register`, `applyProjectToProgram`, `submitCompettetiveProject` | `/programs/`, `/programs/<id>/`, `/programs/<id>/readiness/`, `/programs/<id>/submit-to-moderation/`, `/programs/<id>/register/`, `/programs/<id>/projects/apply/` |
| `ProjectRatingService` | `getAll`, `postFilters`, `rate`, `formValuesToDTO` | `/rate-project/<program_id>`, `/rate-project/rate/<project_id>` |
| `ProgramNewsService` | CRUD/лайки/просмотры новостей программы | `/programs/<id>/news/` |
| `ProgramEditStateService` | Хранение состояния формы, признаков изменений и валидности | Локальное состояние редактирования, используется вместе с `ProgramService.update`. |
| `WizardStateService` | Хранение данных мастера, проверка шагов, `canSubmitToModeration()` | Локальное состояние мастера, итоговая отправка через `ProgramService.create`. |
| Resolvers (`ProgramMainResolver`, `ProgramDetailResolver`, `ProgramRegisterResolver`, `ProgramProjectsResolver`, `ProgramMembersResolver`) | Предзагрузка данных перед открытием маршрутов | Списки, детали, схема регистрации, проекты, участники. |

Обработка ошибок реализуется на уровне компонентов и сервисов через Observable-потоки: backend возвращает HTTP-статусы и сообщения валидации, frontend блокирует сохранение невалидных форм, показывает статусы загрузки/сохранения и защищает маршруты от потери несохраненных изменений через `CanDeactivate`.

## 3. Фактические тестовые сценарии

### 3.1. Автоматизированные backend-тесты

| Блок | Что проверяется | Примеры тестов |
|---|---|---|
| Создание и настройка чемпионата | Валидация динамических полей, расчет готовности, отправка на модерацию, дедлайны подачи проекта. | `test_readiness_returns_payload_for_manager`, `test_submit_to_moderation_updates_status`, `test_submit_blocked_after_deadline`, `test_submit_allowed_before_deadline`. |
| Регистрация и приглашения | Создание одиночных и массовых приглашений, запрет для открытых программ, доступ по токену, принятие, повторное принятие, отзыв, удаление, приватность. | `test_manager_can_create_single_invite`, `test_authenticated_user_can_accept_invite`, `test_repeated_accept_returns_410`, `test_private_program_is_hidden_from_public_list`. |
| Модерация | Доступ администратора, запрет неадминистраторам, одобрение, отклонение с комментарием, отзыв с модерации, заморозка, восстановление, архивация. | `test_admin_can_approve_program_and_log`, `test_admin_can_reject_program_with_comment`, `test_non_admin_gets_403_on_admin_endpoint`, `test_admin_can_archive_frozen_program`. |
| Автоматическая заморозка и напоминания | Заморозка устаревших чемпионатов, исключение чемпионатов с будущими сроками, учет пользовательских настроек уведомлений. | `test_task_auto_freezes_stale_published_program`, `test_task_does_not_freeze_program_with_future_deadline`, `test_send_readiness_reminders_marks_sent`. |
| Верификация компании | Отправка заявки, обязательные поля, ИНН, количество и размер документов, повторная отправка, решение администратора, отзыв верификации, поиск компании. | `test_manager_can_submit_verification_request`, `test_submit_with_invalid_inn_returns_400`, `test_admin_can_approve_verification_request`, `test_admin_can_revoke_verified_program`, `test_company_search_matches_name_and_inn`. |
| Сертификаты | Создание шаблона, фон, формат/размер изображения, предпросмотр, удаление шаблона, генерация по условиям, выдача, публичная проверка. | `test_manager_can_create_template_with_payload`, `test_preview_returns_html_with_test_data`, `test_single_certificate_generation_creates_file`, `test_api_returns_certificate_verification_payload`. |
| Экспертная оценка | Распределенное оценивание, назначение экспертов, ограничения по проекту и программе, запрет удаления назначения после оценки. | `test_list_projects_with_distribution`, `test_rate_project_with_distribution_allows_assigned_expert`, `test_assignment_respects_max_project_rates`, `test_assignment_cannot_be_deleted_after_scores`. |
| Настройки уведомлений | Автосоздание настроек, получение текущих настроек, PATCH. | `test_user_creation_creates_notification_preferences`, `test_current_user_notification_preferences_get_patch`. |

### 3.2. Автоматизированные frontend-тесты

| Блок | Что проверяется |
|---|---|
| `ProgramService` | Формирование запросов к API, параметры списков, создание/редактирование, readiness, отправка на модерацию. |
| `ProjectRatingService` | Получение проектов для оценки, отправка оценок, преобразование значений формы в DTO. |
| `RoleResolverService` | Определение роли пользователя относительно чемпионата. |
| `ReadinessWidgetComponent` | Отображение процента готовности и отдельных пунктов чек-листа. |
| `ProgramStatusBadgeComponent` | Отображение статуса чемпионата. |
| `ProgramCardComponent`, `RatingCardComponent`, `ProgramMainComponent`, `ProgramRegisterComponent` | Базовое создание компонентов и отображение данных. |
| `WizardStateService`, `WizardProgressComponent` | Состояние мастера и прогресс шагов. |

Запуск frontend-тестов предусмотрен командами `npm test` и `npm run test:ci`.

### 3.3. Приемочные сценарии для описания в ВКР

| Сценарий | Что ожидалось | Результат |
|---|---|---|
| Создание черновика чемпионата через мастер | После заполнения базовых данных создается `PartnerProgram` со статусом `draft`. | Пройдено, используется `ProgramService.create`. |
| Настройка регистрационной формы | Поля сохраняются, схема доступна через `/programs/<id>/schema/`, регистрация валидирует обязательные поля и типы. | Пройдено, покрыто тестами динамических полей. |
| Проверка готовности чемпионата | `/programs/<id>/readiness/` возвращает список выполненных и невыполненных условий. | Пройдено, покрыто backend-тестами readiness и frontend-виджетом. |
| Отправка на модерацию | При достаточной готовности статус меняется на `pending_moderation`, создается запись `ModerationLog`. | Пройдено, покрыто тестами отправки на модерацию. |
| Отклонение модератором без комментария | Backend должен вернуть ошибку, так как причина/комментарий обязательны. | Пройдено, покрыто тестом `test_admin_cannot_reject_without_comment`. |
| Публикация чемпионата администратором | Статус меняется на `published`, действие фиксируется в журнале. | Пройдено, покрыто тестом одобрения. |
| Заморозка просроченного чемпионата | По расписанию Celery чемпионат переводится в `frozen`, если организатор не завершил обязательные действия. | Пройдено, покрыто тестами `freeze_stale_programs`. |
| Создание закрытого чемпионата и приглашений | Закрытый чемпионат скрыт из публичного списка, доступ открывается по приглашению. | Пройдено, покрыто тестами приватности и invite-flow. |
| Принятие приглашения | Пользователь регистрируется в чемпионате, приглашение получает статус used; повторное принятие возвращает ошибку. | Пройдено, покрыто тестами invite-flow. |
| Отправка заявки на верификацию компании | Создается `PartnerProgramVerificationRequest`, документы прикрепляются, статус становится pending. | Пройдено, покрыто тестами верификации. |
| Одобрение/отклонение верификации | Администратор меняет статус заявки и статус верификации чемпионата, решение логируется. | Пройдено, покрыто тестами верификации. |
| Назначение эксперта на проект | Назначение создается только если эксперт относится к программе, проект привязан к программе и не превышен лимит оценок. | Пройдено, покрыто тестами `ProjectExpertAssignment`. |
| Оценка проекта экспертом | Назначенный эксперт отправляет оценки по критериям, значения валидируются по типу и диапазону. | Пройдено, покрыто тестами `project_rates`. |
| Создание шаблона сертификата | Менеджер чемпионата сохраняет шаблон, фон и параметры оформления; посторонний пользователь получает отказ. | Пройдено, покрыто тестами сертификатов. |
| Генерация сертификатов | Для подходящих участников создаются `IssuedCertificate` и PDF-файлы; повторная генерация не создает дубликаты. | Пройдено, покрыто тестами генерации. |
| Публичная проверка сертификата | По UUID возвращаются публичные данные сертификата без раскрытия лишних персональных данных. | Пройдено, покрыто тестами публичной проверки. |
| Настройки уведомлений | Пользователь может отключить отдельные типы email-уведомлений; фоновые задачи учитывают эти настройки. | Пройдено, покрыто тестами пользователей, модерации и сертификатов. |

### 3.4. Найденные и исправленные ошибки, которые можно описать

| Ошибка | Исправление / контроль |
|---|---|
| Чемпионат мог быть отправлен на модерацию без достаточной готовности. | Добавлен readiness-чек и проверка перед отправкой. |
| Отклонение модератором могло быть недостаточно информативным. | Для отклонения требуется комментарий/причина, запись сохраняется в `ModerationLog`. |
| Закрытые чемпионаты могли быть видны пользователям без приглашения. | Добавлена проверка приватности в списке и деталях программы. |
| Повторное использование приглашения могло привести к некорректной регистрации. | Добавлены статусы приглашений и проверка repeated accept. |
| Верификация могла приниматься с некорректными документами. | Добавлены проверки обязательных полей, ИНН, количества и размера документов. |
| Назначение эксперта могло не учитывать принадлежность к программе или лимит оценок. | Добавлена валидация в `ProjectExpertAssignment`. |
| Сертификаты могли генерироваться повторно для одного пользователя. | Добавлено уникальное ограничение `program + user` и тест идемпотентности. |
| Email-уведомления могли отправляться пользователям, которые их отключили. | Добавлена модель `UserNotificationPreferences` и проверки в сервисах/задачах. |

### 3.5. Адаптивность

В кодовой базе есть компонентная структура Angular и responsive-верстка на уровне SCSS-компонентов, однако автоматизированных e2e-тестов адаптивности в найденных файлах нет. Для ВКР корректно указать, что адаптивность проверялась функционально вручную на типовых ширинах:

| Ширина | Что проверять |
|---|---|
| 360 px | Мастер создания, карточки чемпионатов, формы регистрации, отсутствие горизонтального скролла. |
| 768 px | Планшетная компоновка списков, вкладки редактирования, виджет готовности. |
| Desktop | Полные таблицы проектов/участников, экспертная оценка, модерационные действия, карточки статистики. |

## 4. Минимальная структура файлов для передачи в описание

### Backend

```text
procollab_api/
  partner_programs/
    models.py
    serializers/
    views.py
    services.py
    tasks.py
    urls.py
    invite_urls.py
    verification_services.py
    migrations/
    tests.py
    tests_invites.py
    tests_verification.py
  moderation/
    models.py
    serializers.py
    views.py
    permissions.py
    services.py
    tasks.py
    urls.py
    migrations/
    tests.py
  certificates/
    models.py
    serializers.py
    views.py
    services.py
    tasks.py
    urls.py
    migrations/
    tests.py
    tests_generation.py
    tests_verification.py
  project_rates/
    models.py
    serializers.py
    views.py
    urls.py
    tests.py
  users/
    models.py
    serializers.py
    views.py
    urls.py
    tasks.py
    migrations/
    tests.py
```

### Frontend

```text
procollab_front/projects/social_platform/src/app/office/program/
  program.routes.ts
  main/
    sections/all-programs/
    sections/my-programs/
    components/verification-banner/
  wizard/
    wizard.routes.ts
    wizard.component.ts
    components/wizard-progress/
    steps/basic-info-step/
    steps/registration-step/
    steps/publish-step/
    services/wizard-state.service.ts
  detail/
    detail.routes.ts
    main/
    list/
    register/
  edit/
    edit.routes.ts
    edit.component.ts
    services/program-edit-state.service.ts
    tabs/main/
    tabs/schedule/
    tabs/materials/
    tabs/registration/
    tabs/criteria/
  readiness-widget/
  shared/program-card/
  shared/program-status-badge/
  shared/rating-card/
  services/program.service.ts
  services/project-rating.service.ts
  services/program-news.service.ts
```
