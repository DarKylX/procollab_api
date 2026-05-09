# MVP уведомлений PROCOLLAB

## Аудит найденной инфраструктуры

- Моделей `Notification` / `NotificationDelivery` до MVP не было.
- В `users.models.UserNotificationPreferences` уже есть настройки:
  `inapp_notifications_enabled`, `email_moderation_results`,
  `email_verification_results`, `email_reminders_enabled`.
- Email уже настроен через Anymail Unisender Go:
  `anymail.backends.unisender_go.EmailBackend`, `UNISENDER_GO_API_KEY`,
  `EMAIL_USER`, `DEFAULT_FROM_EMAIL`.
- Celery уже подключен через `procollab/celery.py`; в проекте есть email-задачи
  в `mailing.tasks`, `vacancy.tasks`, `users.tasks`.
- Общие email-шаблоны были, но шаблонов для MVP-уведомлений не было.
- Angular-колокольчик существовал, но работал без backend API уведомлений и
  в основном показывал инвайты.

## Backend

Добавлен app `notifications`:

- `Notification` - in-app уведомление пользователя:
  `recipient`, `type`, `title`, `message`, `object_type`, `object_id`, `url`,
  `is_read`, `created_at`, `dedupe_key`.
- `NotificationDelivery` - доставка по каналам `in_app` и `email`:
  `status`, `sent_at`, `error`.
- `NotificationDelivery(channel="in_app")` создается сразу со статусом `sent`.
- Email delivery создается как `pending`, а Celery task ставится только через
  `transaction.on_commit`.

API:

- `GET /notifications/`
- `GET /notifications/unread-count/`
- `POST /notifications/{id}/read/`
- `POST /notifications/mark-all-read/`

Все API endpoints фильтруют данные строго по `recipient=request.user`; staff не
видит чужие уведомления через этот API.

## Service layer

Единая точка входа: `notifications.services`.

Сервис отвечает за:

- выбор получателей;
- проверку пользовательских предпочтений;
- dedupe;
- создание in-app уведомления;
- создание delivery-записей;
- постановку email task через `transaction.on_commit`;
- построение абсолютного email CTA URL через `FRONTEND_URL` / `SITE_URL`.

Если `UserNotificationPreferences` отсутствуют, используются дефолты:
in-app включены, email включен для moderation / verification / expert assignment.

## События

Реализованы типы:

- `program_submitted_to_moderation`
- `program_moderation_approved`
- `program_moderation_rejected`
- `company_verification_submitted`
- `company_verification_approved`
- `company_verification_rejected`
- `expert_projects_assigned`

Точки интеграции:

- `moderation.services.submit_program_to_moderation`
- `moderation.services.approve_program`
- `moderation.services.reject_program`
- `partner_programs.verification_services.submit_verification_request`
- `partner_programs.verification_services.approve_verification_request`
- `partner_programs.verification_services.reject_verification_request`
- `project_rates.admin.ProjectExpertAssignmentAdmin.save_model`

Для экспертных назначений доменная логика вынесена в
`notify_expert_projects_assigned`; Django admin только вызывает общий service-layer
метод после создания batch назначения.

## Dedupe

`dedupe_key` защищает от дублей одной операции, но не блокирует реальные
повторные события:

- moderation: `moderation:{ModerationLog.id}:{action}`;
- verification: `verification:{verification_request_id}:{status/action}`;
- expert assignment: `expert_assignment:{batch_key}`.

Повторный вызов с тем же ключом не создает дубль, а новый `ModerationLog` /
новый verification request / новый batch назначения создает новое уведомление.

## Email

Новый provider не добавлялся. Отправка идет через текущий Django email backend,
то есть через Anymail Unisender Go в настройках проекта.

Добавлены HTML-шаблоны:

- `templates/email/notifications/admin_program_submitted.html`
- `templates/email/notifications/organizer_program_approved.html`
- `templates/email/notifications/organizer_program_rejected.html`
- `templates/email/notifications/admin_verification_submitted.html`
- `templates/email/notifications/organizer_verification_approved.html`
- `templates/email/notifications/organizer_verification_rejected.html`
- `templates/email/notifications/expert_projects_assigned.html`

Celery task `notifications.tasks.send_notification_email` имеет plain-text
fallback: если HTML-шаблон отсутствует или не рендерится, создание in-app
уведомления не ломается, а письмо отправляется plain text либо delivery получает
`failed` при ошибке email backend.

## Frontend

Обновлен `NotificationService`:

- список уведомлений;
- последние 7 для dropdown;
- unread count;
- mark read;
- mark all read.

Обновлен office header / dropdown:

- badge считает только `Notification.is_read=false`;
- инвайты оставлены отдельным блоком;
- последние уведомления подсвечивают unread;
- есть mark all и ссылка на полный список;
- клик по уведомлению помечает его прочитанным и ведет на `notification.url`.

Добавлена страница:

- `/office/notifications`
- фильтры: Все, Непрочитанные, Модерация, Верификация, Экспертиза;
- карточки уведомлений;
- empty state;
- mark all read.

## Ограничения MVP

Не реализованы:

- Telegram;
- SMS;
- browser push;
- WebSocket realtime;
- редактор email-шаблонов;
- сложные настройки уведомлений;
- админский просмотр чужих уведомлений.

Инвайты не смешиваются с новым unread count уведомлений.

## Проверки

Backend:

```bash
DEBUG=True poetry run python manage.py check
DEBUG=True poetry run python manage.py makemigrations notifications --check --dry-run
DEBUG=True poetry run python manage.py test notifications --keepdb
DEBUG=True poetry run python manage.py test moderation.tests --keepdb
DEBUG=True poetry run python manage.py test partner_programs.tests_verification --keepdb
```

Frontend:

```bash
node ./node_modules/@angular/cli/bin/ng.js build social_platform --configuration=development
```

Karma unit tests in this checkout currently stop on unrelated legacy spec import
errors in courses / vacancies / shared ui before running the new specs.
