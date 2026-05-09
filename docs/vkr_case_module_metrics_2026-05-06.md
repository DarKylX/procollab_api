# Метрики модуля кейс-чемпионатов

Дата подсчета: 06.05.2026.

## Методика

- Backend сравнивался с `origin/master` (`HEAD f86461a`).
- Frontend сравнивался с `origin/dev` (`HEAD 4944af67`).
- Учитывались текущие tracked-изменения и untracked-файлы рабочей копии.
- Для измененных tracked-файлов считались добавленные строки diff; измененная строка учитывается как добавленная строка новой версии.
- Для новых untracked-файлов считался весь текущий объем файла.
- Исключены `.git`, `node_modules`, `dist`, `.angular`, `media`, `log/logs`, `migrations`, docs, бинарные и автогенерированные файлы.
- Пустые строки и строки-комментарии исключены для `.py`, `.ts`, `.scss`, `.html`; Python docstring-блоки также отфильтрованы как служебные комментарии.
- Тесты/spec-файлы включены в общий объем, но выделены отдельной строкой.

## Итог по коду

| Часть | База | Файлов | Добавлено/изменено строк кода | Удалено строк кода | Production LOC | Test/spec LOC |
| --- | --- | --- | --- | --- | --- | --- |
| Backend | origin/master | 73 | 12511 | 158 | 9230 | 3281 |
| Frontend | origin/dev | 156 | 26821 | 677 | 26233 | 588 |
| Итого |  | 229 | 39332 | 835 | 35463 | 3869 |

## Разбивка по расширениям

### Backend

| Расширение | Файлов | Добавлено/изменено LOC | Удалено LOC |
| --- | --- | --- | --- |
| .html | 3 | 445 | 0 |
| .py | 70 | 12066 | 158 |

### Frontend

| Расширение | Файлов | Добавлено/изменено LOC | Удалено LOC |
| --- | --- | --- | --- |
| .html | 43 | 5323 | 225 |
| .scss | 39 | 10497 | 155 |
| .ts | 74 | 11001 | 297 |

## Записи в профильных таблицах

| Таблица | Записей |
| --- | --- |
| certificates_certificategenerationrun | 0 |
| certificates_issuedcertificate | 0 |
| certificates_programcertificatetemplate | 0 |
| files_userfile | 17 |
| moderation_moderationlog | 16 |
| partner_programs_partnerprogram | 35 |
| partner_programs_partnerprogramfield | 60 |
| partner_programs_partnerprogramfieldvalue | 150 |
| partner_programs_partnerprograminvite | 0 |
| partner_programs_partnerprogrammaterial | 38 |
| partner_programs_partnerprogramproject | 57 |
| partner_programs_partnerprogramuserprofile | 616 |
| partner_programs_partnerprogramverificationrequest | 1 |
| project_rates_criteria | 118 |
| project_rates_projectexpertassignment | 48 |
| project_rates_projectscore | 228 |
| projects_company | 101 |
| projects_project | 85 |
| users_usernotificationpreferences | 108 |
| Итого | 1678 |

Исключенные кросс-таблицы / неявные M2M:

| Таблица | Записей |
| --- | --- |
| partner_programs_partnerprogram_managers | 82 |
| partner_programs_partnerprogramverificationrequest_documents | 1 |
| projects_projectcompany | 70 |

## Backend: файлы, вошедшие в подсчет

| Статус | LOC+ | LOC- | Test | Файл |
| --- | --- | --- | --- | --- |
| A | 49 | 0 |  | certificates/admin.py |
| A | 6 | 0 |  | certificates/apps.py |
| A | 109 | 0 |  | certificates/enums.py |
| A | 154 | 0 |  | certificates/models.py |
| A | 179 | 0 |  | certificates/serializers.py |
| A | 613 | 0 |  | certificates/services.py |
| A | 33 | 0 |  | certificates/signals.py |
| A | 100 | 0 |  | certificates/tasks.py |
| A | 58 | 0 |  | certificates/templates/certificates/certificate.html |
| A | 232 | 0 |  | certificates/templates/certificates/verify.html |
| A | 248 | 0 | yes | certificates/tests.py |
| A | 340 | 0 | yes | certificates/tests_generation.py |
| A | 170 | 0 | yes | certificates/tests_verification.py |
| A | 65 | 0 |  | certificates/urls.py |
| A | 314 | 0 |  | certificates/views.py |
| A | 1281 | 0 |  | core/management/commands/seed_demo_data.py |
| M | 2 | 2 |  | files/admin.py |
| M | 65 | 6 |  | files/service.py |
| M | 70 | 0 | yes | files/tests.py |
| M | 20 | 5 |  | files/views.py |
| A | 34 | 0 |  | moderation/admin.py |
| A | 5 | 0 |  | moderation/apps.py |
| A | 130 | 0 |  | moderation/models.py |
| A | 6 | 0 |  | moderation/permissions.py |
| A | 393 | 0 |  | moderation/serializers.py |
| A | 49 | 0 |  | moderation/services.py |
| A | 28 | 0 |  | moderation/tasks.py |
| A | 627 | 0 | yes | moderation/tests.py |
| A | 87 | 0 |  | moderation/urls.py |
| A | 532 | 0 |  | moderation/views.py |
| M | 113 | 10 |  | partner_programs/admin.py |
| A | 510 | 0 |  | partner_programs/analytics.py |
| M | 2 | 0 |  | partner_programs/apps.py |
| A | 44 | 0 |  | partner_programs/invite_urls.py |
| M | 344 | 4 |  | partner_programs/models.py |
| M | 22 | 0 |  | partner_programs/serializers/__init__.py |
| A | 87 | 0 |  | partner_programs/serializers/invites.py |
| M | 456 | 3 |  | partner_programs/serializers/programs.py |
| A | 266 | 0 |  | partner_programs/serializers/verification.py |
| M | 322 | 3 |  | partner_programs/services.py |
| A | 13 | 0 |  | partner_programs/signals.py |
| M | 17 | 1 |  | partner_programs/tasks.py |
| A | 155 | 0 |  | partner_programs/templates/partner_programs/invite.html |
| M | 129 | 18 | yes | partner_programs/tests.py |
| A | 196 | 0 | yes | partner_programs/tests_analytics.py |
| A | 143 | 0 | yes | partner_programs/tests_edit_readiness.py |
| A | 241 | 0 | yes | partner_programs/tests_invites.py |
| A | 555 | 0 | yes | partner_programs/tests_verification.py |
| M | 102 | 0 |  | partner_programs/urls.py |
| A | 378 | 0 |  | partner_programs/verification_services.py |
| M | 846 | 61 |  | partner_programs/views.py |
| M | 12 | 0 |  | procollab/celery.py |
| M | 10 | 1 |  | procollab/settings.py |
| M | 13 | 0 |  | procollab/urls.py |
| M | 40 | 2 |  | project_rates/admin.py |
| M | 178 | 1 |  | project_rates/models.py |
| M | 227 | 1 |  | project_rates/serializers.py |
| A | 56 | 0 | yes | project_rates/tests_criteria_weight.py |
| A | 325 | 0 | yes | project_rates/tests_expert_evaluations.py |
| M | 31 | 1 |  | project_rates/urls.py |
| M | 288 | 4 |  | project_rates/views.py |
| A | 60 | 0 | yes | projects/tests_program_participation_rules.py |
| M | 18 | 5 |  | projects/validators.py |
| M | 44 | 3 |  | users/admin.py |
| M | 32 | 10 |  | users/filters.py |
| M | 49 | 2 |  | users/models.py |
| M | 22 | 3 |  | users/serializers.py |
| M | 15 | 2 |  | users/signals.py |
| M | 1 | 1 |  | users/tasks.py |
| M | 42 | 5 | yes | users/tests.py |
| A | 79 | 0 | yes | users/tests_filters.py |
| M | 11 | 2 |  | users/urls.py |
| M | 18 | 2 |  | users/views.py |

## Frontend: файлы, вошедшие в подсчет

| Статус | LOC+ | LOC- | Test | Файл |
| --- | --- | --- | --- | --- |
| M | 2 | 0 |  | projects/social_platform/src/app/auth/models/user.model.ts |
| M | 2 | 3 |  | projects/social_platform/src/app/auth/register/register.component.html |
| M | 3 | 5 |  | projects/social_platform/src/app/auth/register/register.component.ts |
| M | 7 | 3 |  | projects/social_platform/src/app/core/services/file.service.ts |
| A | 360 | 0 |  | projects/social_platform/src/app/office/admin/moderation/detail/moderation-detail.component.html |
| A | 561 | 0 |  | projects/social_platform/src/app/office/admin/moderation/detail/moderation-detail.component.scss |
| A | 295 | 0 |  | projects/social_platform/src/app/office/admin/moderation/detail/moderation-detail.component.ts |
| A | 14 | 0 |  | projects/social_platform/src/app/office/admin/moderation/forbidden/moderation-forbidden.component.html |
| A | 45 | 0 |  | projects/social_platform/src/app/office/admin/moderation/forbidden/moderation-forbidden.component.scss |
| A | 12 | 0 |  | projects/social_platform/src/app/office/admin/moderation/forbidden/moderation-forbidden.component.ts |
| A | 156 | 0 |  | projects/social_platform/src/app/office/admin/moderation/list/moderation-list.component.html |
| A | 312 | 0 |  | projects/social_platform/src/app/office/admin/moderation/list/moderation-list.component.scss |
| A | 213 | 0 |  | projects/social_platform/src/app/office/admin/moderation/list/moderation-list.component.ts |
| A | 14 | 0 |  | projects/social_platform/src/app/office/admin/moderation/moderation-staff.guard.ts |
| A | 171 | 0 |  | projects/social_platform/src/app/office/admin/moderation/moderation.models.ts |
| A | 40 | 0 |  | projects/social_platform/src/app/office/admin/moderation/moderation.routes.ts |
| A | 97 | 0 |  | projects/social_platform/src/app/office/admin/moderation/moderation.service.ts |
| A | 224 | 0 |  | projects/social_platform/src/app/office/admin/moderation/verification-detail/verification-detail.component.html |
| A | 270 | 0 |  | projects/social_platform/src/app/office/admin/moderation/verification-detail/verification-detail.component.scss |
| A | 181 | 0 |  | projects/social_platform/src/app/office/admin/moderation/verification-detail/verification-detail.component.ts |
| A | 134 | 0 |  | projects/social_platform/src/app/office/admin/moderation/verification-list/verification-list.component.html |
| A | 232 | 0 |  | projects/social_platform/src/app/office/admin/moderation/verification-list/verification-list.component.scss |
| A | 147 | 0 |  | projects/social_platform/src/app/office/admin/moderation/verification-list/verification-list.component.ts |
| A | 62 | 0 |  | projects/social_platform/src/app/office/expert/evaluations/expert-evaluations.component.html |
| A | 134 | 0 |  | projects/social_platform/src/app/office/expert/evaluations/expert-evaluations.component.scss |
| A | 49 | 0 |  | projects/social_platform/src/app/office/expert/evaluations/expert-evaluations.component.ts |
| M | 552 | 54 |  | projects/social_platform/src/app/office/features/detail/detail.component.html |
| M | 1182 | 0 |  | projects/social_platform/src/app/office/features/detail/detail.component.scss |
| M | 1116 | 42 |  | projects/social_platform/src/app/office/features/detail/detail.component.ts |
| M | 15 | 1 |  | projects/social_platform/src/app/office/features/nav/nav.component.html |
| M | 1 | 0 |  | projects/social_platform/src/app/office/features/nav/nav.component.ts |
| M | 3 | 1 |  | projects/social_platform/src/app/office/features/program-links/program-links.component.html |
| M | 13 | 3 |  | projects/social_platform/src/app/office/features/program-links/program-links.component.scss |
| M | 1 | 0 |  | projects/social_platform/src/app/office/features/program-links/program-links.component.ts |
| M | 3 | 0 |  | projects/social_platform/src/app/office/models/project.model.ts |
| M | 10 | 0 |  | projects/social_platform/src/app/office/office.routes.ts |
| A | 169 | 0 |  | projects/social_platform/src/app/office/program/analytics/program-analytics.component.html |
| A | 349 | 0 |  | projects/social_platform/src/app/office/program/analytics/program-analytics.component.scss |
| A | 147 | 0 | yes | projects/social_platform/src/app/office/program/analytics/program-analytics.component.spec.ts |
| A | 217 | 0 |  | projects/social_platform/src/app/office/program/analytics/program-analytics.component.ts |
| M | 19 | 5 |  | projects/social_platform/src/app/office/program/detail/detail.routes.ts |
| M | 27 | 0 |  | projects/social_platform/src/app/office/program/detail/list/list.component.ts |
| A | 339 | 0 |  | projects/social_platform/src/app/office/program/detail/main/components/program-context-actions/program-context-actions.component.html |
| A | 319 | 0 |  | projects/social_platform/src/app/office/program/detail/main/components/program-context-actions/program-context-actions.component.scss |
| A | 311 | 0 |  | projects/social_platform/src/app/office/program/detail/main/components/program-context-actions/program-context-actions.component.ts |
| A | 25 | 0 |  | projects/social_platform/src/app/office/program/detail/main/components/program-stat-cards/program-stat-cards.component.html |
| A | 81 | 0 |  | projects/social_platform/src/app/office/program/detail/main/components/program-stat-cards/program-stat-cards.component.scss |
| A | 133 | 0 |  | projects/social_platform/src/app/office/program/detail/main/components/program-stat-cards/program-stat-cards.component.ts |
| M | 529 | 102 |  | projects/social_platform/src/app/office/program/detail/main/main.component.html |
| M | 1096 | 79 |  | projects/social_platform/src/app/office/program/detail/main/main.component.scss |
| M | 779 | 116 |  | projects/social_platform/src/app/office/program/detail/main/main.component.ts |
| M | 2 | 2 |  | projects/social_platform/src/app/office/program/detail/register/register.component.html |
| M | 24 | 0 |  | projects/social_platform/src/app/office/program/detail/register/register.component.scss |
| A | 160 | 0 |  | projects/social_platform/src/app/office/program/edit/_edit-form.scss |
| A | 229 | 0 |  | projects/social_platform/src/app/office/program/edit/edit.component.html |
| A | 663 | 0 |  | projects/social_platform/src/app/office/program/edit/edit.component.scss |
| A | 557 | 0 |  | projects/social_platform/src/app/office/program/edit/edit.component.ts |
| A | 73 | 0 |  | projects/social_platform/src/app/office/program/edit/edit.routes.ts |
| A | 148 | 0 |  | projects/social_platform/src/app/office/program/edit/services/program-edit-state.service.ts |
| A | 320 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/criteria/program-edit-criteria.component.html |
| A | 509 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/criteria/program-edit-criteria.component.scss |
| A | 589 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/criteria/program-edit-criteria.component.ts |
| A | 129 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/main/program-edit-main.component.html |
| A | 196 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/main/program-edit-main.component.scss |
| A | 338 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/main/program-edit-main.component.ts |
| A | 116 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/materials/program-edit-materials.component.html |
| A | 224 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/materials/program-edit-materials.component.scss |
| A | 216 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/materials/program-edit-materials.component.ts |
| A | 8 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/placeholder/program-edit-placeholder.component.html |
| A | 14 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/placeholder/program-edit-placeholder.component.scss |
| A | 36 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/placeholder/program-edit-placeholder.component.ts |
| A | 261 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/registration/program-edit-registration.component.html |
| A | 479 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/registration/program-edit-registration.component.scss |
| A | 584 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/registration/program-edit-registration.component.ts |
| A | 156 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/schedule/program-edit-schedule.component.html |
| A | 375 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/schedule/program-edit-schedule.component.scss |
| A | 452 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/schedule/program-edit-schedule.component.ts |
| A | 280 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/verification/program-edit-verification.component.html |
| A | 423 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/verification/program-edit-verification.component.scss |
| A | 517 | 0 |  | projects/social_platform/src/app/office/program/edit/tabs/verification/program-edit-verification.component.ts |
| A | 210 | 0 |  | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-detail.component.html |
| A | 407 | 0 |  | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-detail.component.scss |
| A | 380 | 0 |  | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-detail.component.ts |
| A | 137 | 0 |  | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-list.component.html |
| A | 338 | 0 |  | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-list.component.scss |
| A | 171 | 0 |  | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-list.component.ts |
| A | 35 | 0 |  | projects/social_platform/src/app/office/program/main/components/verification-banner/verification-banner.component.html |
| A | 82 | 0 |  | projects/social_platform/src/app/office/program/main/components/verification-banner/verification-banner.component.scss |
| A | 55 | 0 |  | projects/social_platform/src/app/office/program/main/components/verification-banner/verification-banner.component.ts |
| M | 47 | 24 |  | projects/social_platform/src/app/office/program/main/main.component.html |
| M | 68 | 28 |  | projects/social_platform/src/app/office/program/main/main.component.scss |
| M | 317 | 53 |  | projects/social_platform/src/app/office/program/main/main.component.ts |
| A | 122 | 0 |  | projects/social_platform/src/app/office/program/main/sections/all-programs/all-programs.component.html |
| A | 368 | 0 |  | projects/social_platform/src/app/office/program/main/sections/all-programs/all-programs.component.scss |
| A | 111 | 0 |  | projects/social_platform/src/app/office/program/main/sections/all-programs/all-programs.component.ts |
| A | 49 | 0 |  | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.html |
| A | 124 | 0 |  | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.scss |
| A | 25 | 0 | yes | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.spec.ts |
| A | 62 | 0 |  | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.ts |
| A | 40 | 0 |  | projects/social_platform/src/app/office/program/models/program-analytics.model.ts |
| A | 29 | 0 |  | projects/social_platform/src/app/office/program/models/program-draft.model.ts |
| A | 93 | 0 |  | projects/social_platform/src/app/office/program/models/program-verification.model.ts |
| M | 105 | 7 |  | projects/social_platform/src/app/office/program/models/program.model.ts |
| A | 85 | 0 |  | projects/social_platform/src/app/office/program/models/project-evaluation.model.ts |
| A | 53 | 0 |  | projects/social_platform/src/app/office/program/models/readiness.model.ts |
| M | 1 | 4 |  | projects/social_platform/src/app/office/program/program.component.html |
| M | 14 | 1 |  | projects/social_platform/src/app/office/program/program.component.scss |
| M | 6 | 43 |  | projects/social_platform/src/app/office/program/program.component.ts |
| M | 10 | 4 |  | projects/social_platform/src/app/office/program/program.routes.ts |
| A | 52 | 0 |  | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.html |
| A | 242 | 0 |  | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.scss |
| A | 89 | 0 | yes | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.spec.ts |
| A | 167 | 0 |  | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.ts |
| M | 77 | 1 | yes | projects/social_platform/src/app/office/program/services/program.service.spec.ts |
| M | 166 | 8 |  | projects/social_platform/src/app/office/program/services/program.service.ts |
| M | 104 | 1 | yes | projects/social_platform/src/app/office/program/services/project-rating.service.spec.ts |
| M | 43 | 0 |  | projects/social_platform/src/app/office/program/services/project-rating.service.ts |
| A | 32 | 0 | yes | projects/social_platform/src/app/office/program/services/role-resolver.service.spec.ts |
| A | 56 | 0 |  | projects/social_platform/src/app/office/program/services/role-resolver.service.ts |
| M | 82 | 32 |  | projects/social_platform/src/app/office/program/shared/program-card/program-card.component.html |
| M | 176 | 44 |  | projects/social_platform/src/app/office/program/shared/program-card/program-card.component.scss |
| M | 116 | 4 |  | projects/social_platform/src/app/office/program/shared/program-card/program-card.component.ts |
| A | 7 | 0 |  | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.html |
| A | 51 | 0 |  | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.scss |
| A | 42 | 0 | yes | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.spec.ts |
| A | 35 | 0 |  | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.ts |
| A | 30 | 0 |  | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.html |
| A | 81 | 0 |  | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.scss |
| A | 27 | 0 | yes | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.spec.ts |
| A | 32 | 0 |  | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.ts |
| A | 45 | 0 | yes | projects/social_platform/src/app/office/program/wizard/services/wizard-state.service.spec.ts |
| A | 115 | 0 |  | projects/social_platform/src/app/office/program/wizard/services/wizard-state.service.ts |
| A | 100 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/basic-info-step/basic-info-step.component.html |
| A | 82 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/basic-info-step/basic-info-step.component.scss |
| A | 138 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/basic-info-step/basic-info-step.component.ts |
| A | 79 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/publish-step/publish-step.component.html |
| A | 138 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/publish-step/publish-step.component.scss |
| A | 64 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/publish-step/publish-step.component.ts |
| A | 97 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/registration-step/registration-step.component.html |
| A | 211 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/registration-step/registration-step.component.scss |
| A | 78 | 0 |  | projects/social_platform/src/app/office/program/wizard/steps/registration-step/registration-step.component.ts |
| A | 178 | 0 |  | projects/social_platform/src/app/office/program/wizard/wizard.component.html |
| A | 448 | 0 |  | projects/social_platform/src/app/office/program/wizard/wizard.component.scss |
| A | 422 | 0 |  | projects/social_platform/src/app/office/program/wizard/wizard.component.ts |
| A | 37 | 0 |  | projects/social_platform/src/app/office/program/wizard/wizard.routes.ts |
| M | 1 | 1 |  | projects/social_platform/src/app/office/projects/edit/shared/project-additional-step/project-additional-step.component.html |
| M | 4 | 1 |  | projects/social_platform/src/app/office/projects/edit/shared/project-additional-step/project-additional-step.component.ts |
| M | 2 | 0 |  | projects/social_platform/src/app/ui/components/avatar/avatar.component.html |
| M | 3 | 0 |  | projects/social_platform/src/app/ui/components/avatar/avatar.component.scss |
| M | 1 | 0 |  | projects/social_platform/src/app/ui/components/input/input.component.html |
| M | 16 | 2 |  | projects/social_platform/src/app/ui/components/input/input.component.ts |
| M | 7 | 1 |  | projects/social_platform/src/app/ui/components/search/search.component.html |
| M | 3 | 0 |  | projects/social_platform/src/app/ui/components/search/search.component.scss |
| M | 1 | 0 |  | projects/social_platform/src/app/ui/components/textarea/textarea.component.html |
| M | 8 | 2 |  | projects/social_platform/src/app/utils/helpers/export-file.ts |
| A | 41 | 0 |  | projects/social_platform/src/app/utils/phone-format.ts |

