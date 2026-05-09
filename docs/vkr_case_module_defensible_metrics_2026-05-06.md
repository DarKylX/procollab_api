# Защитоспособные метрики модуля кейс-чемпионатов

Дата подсчета: 06.05.2026.

## База сравнения и правила

- Backend: сравнение с `origin/master`, текущий `HEAD f86461a`.
- Frontend: сравнение с `origin/dev`, текущий `HEAD 4944af67`.
- `DIFF ADDED LOC` — добавленные строки в diff. Измененная строка считается как удаленная старая строка + добавленная новая строка, поэтому этот показатель нельзя называть уникально написанными строками с нуля.
- `CURRENT MODULE LOC` — текущий объем кода в файлах/частях файлов модуля: новые модульные файлы считаются целиком, существующие backend/shared файлы считаются только по модульным добавленным строкам; для Angular `office/program/**` считается текущий файл целиком как frontend-footprint модуля.
- `NEW FILES LOC` — только новые файлы, которых не было в исходной ветке.
- Исключены `node_modules`, `dist`, `.angular`, `.git`, `media`, `log/logs`, `migrations`, docs, бинарные/офисные/медиа файлы, пустые строки, строки-комментарии, Python docstring-блоки.
- Production LOC не включает test/spec. HTML/SCSS/Python/TypeScript LOC — разбивка по расширениям внутри соответствующей метрики и может пересекаться с production/test по смыслу.

## 1. DIFF ADDED LOC

| Метрика | Backend | Frontend | Итого |
| --- | --- | --- | --- |
| Production LOC | 7940 | 26517 | 34457 |
| Test/spec LOC | 3283 | 588 | 3871 |
| HTML LOC | 445 | 5366 | 5811 |
| SCSS LOC | 0 | 10685 | 10685 |
| Python LOC | 10778 | 0 | 10778 |
| TypeScript LOC | 0 | 11054 | 11054 |

Удаленные строки в отфильтрованном diff: backend 157, frontend 770, итого 927.

## 2. CURRENT MODULE LOC

| Метрика | Backend | Frontend | Итого |
| --- | --- | --- | --- |
| Production LOC | 7940 | 27845 | 35785 |
| Test/spec LOC | 3283 | 618 | 3901 |
| HTML LOC | 445 | 5453 | 5898 |
| SCSS LOC | 0 | 10842 | 10842 |
| Python LOC | 10778 | 0 | 10778 |
| TypeScript LOC | 0 | 12168 | 12168 |

## 3. NEW FILES LOC

| Метрика | Backend | Frontend | Итого |
| --- | --- | --- | --- |
| Production LOC | 4629 | 19676 | 24305 |
| Test/spec LOC | 3042 | 407 | 3449 |
| HTML LOC | 445 | 4078 | 4523 |
| SCSS LOC | 0 | 7945 | 7945 |
| Python LOC | 7226 | 0 | 7226 |
| TypeScript LOC | 0 | 8060 | 8060 |

## 10 самых крупных файлов по CURRENT MODULE LOC

| LOC | Repo | Ext | Test | Mode | Файл |
| --- | --- | --- | --- | --- | --- |
| 1188 | Frontend | .scss |  | current full file | projects/social_platform/src/app/office/program/detail/main/main.component.scss |
| 1182 | Frontend | .scss |  | changed module lines only | projects/social_platform/src/app/office/features/detail/detail.component.scss |
| 1118 | Frontend | .ts |  | changed module lines only | projects/social_platform/src/app/office/features/detail/detail.component.ts |
| 989 | Frontend | .ts |  | current full file | projects/social_platform/src/app/office/program/detail/main/main.component.ts |
| 846 | Backend | .py |  | changed module lines only | partner_programs/views.py |
| 663 | Frontend | .scss |  | current full file | projects/social_platform/src/app/office/program/edit/edit.component.scss |
| 627 | Backend | .py | yes | current full file | moderation/tests.py |
| 613 | Backend | .py |  | current full file | certificates/services.py |
| 589 | Frontend | .ts |  | current full file | projects/social_platform/src/app/office/program/edit/tabs/criteria/program-edit-criteria.component.ts |
| 586 | Frontend | .html |  | current full file | projects/social_platform/src/app/office/program/detail/main/main.component.html |

## Записи в профильных таблицах БД

| Таблица | Записей |
| --- | --- |
| certificates_certificategenerationrun | 0 |
| certificates_issuedcertificate | 0 |
| certificates_programcertificatetemplate | 0 |
| files_userfile | 18 |
| moderation_moderationlog | 18 |
| partner_programs_partnerprogram | 35 |
| partner_programs_partnerprogramfield | 60 |
| partner_programs_partnerprogramfieldvalue | 150 |
| partner_programs_partnerprograminvite | 0 |
| partner_programs_partnerprogrammaterial | 38 |
| partner_programs_partnerprogramproject | 57 |
| partner_programs_partnerprogramuserprofile | 617 |
| partner_programs_partnerprogramverificationrequest | 1 |
| project_rates_criteria | 118 |
| project_rates_projectexpertassignment | 48 |
| project_rates_projectscore | 228 |
| projects_company | 101 |
| projects_project | 85 |
| users_usernotificationpreferences | 108 |
| Итого | 1682 |

Исключенные кросс-таблицы / неявные M2M:

| Таблица | Записей |
| --- | --- |
| partner_programs_partnerprogram_managers | 82 |
| partner_programs_partnerprogramverificationrequest_documents | 1 |
| projects_projectcompany | 70 |

## Файлы, вошедшие в подсчет

### Backend

| Status | Reason | Файл |
| --- | --- | --- |
| A | certificates subsystem | certificates/__init__.py |
| A | certificates subsystem | certificates/admin.py |
| A | certificates subsystem | certificates/apps.py |
| A | certificates subsystem | certificates/enums.py |
| A | certificates subsystem | certificates/models.py |
| A | certificates subsystem | certificates/serializers.py |
| A | certificates subsystem | certificates/services.py |
| A | certificates subsystem | certificates/signals.py |
| A | certificates subsystem | certificates/tasks.py |
| A | certificates subsystem | certificates/templates/certificates/certificate.html |
| A | certificates subsystem | certificates/templates/certificates/verify.html |
| A | certificates subsystem | certificates/tests.py |
| A | certificates subsystem | certificates/tests_generation.py |
| A | certificates subsystem | certificates/tests_verification.py |
| A | certificates subsystem | certificates/urls.py |
| A | certificates subsystem | certificates/views.py |
| M | file upload/delete support for module | files/admin.py |
| M | file upload/delete support for module | files/service.py |
| M | file upload/delete support for module | files/tests.py |
| M | file upload/delete support for module | files/views.py |
| A | moderation subsystem | moderation/__init__.py |
| A | moderation subsystem | moderation/admin.py |
| A | moderation subsystem | moderation/apps.py |
| A | moderation subsystem | moderation/models.py |
| A | moderation subsystem | moderation/permissions.py |
| A | moderation subsystem | moderation/serializers.py |
| A | moderation subsystem | moderation/services.py |
| A | moderation subsystem | moderation/tasks.py |
| A | moderation subsystem | moderation/tests.py |
| A | moderation subsystem | moderation/urls.py |
| A | moderation subsystem | moderation/views.py |
| M | partner_programs module changes | partner_programs/admin.py |
| A | partner_programs module changes | partner_programs/analytics.py |
| M | partner_programs module changes | partner_programs/apps.py |
| A | partner_programs module changes | partner_programs/invite_urls.py |
| M | partner_programs module changes | partner_programs/models.py |
| M | partner_programs module changes | partner_programs/serializers/__init__.py |
| A | partner_programs module changes | partner_programs/serializers/invites.py |
| M | partner_programs module changes | partner_programs/serializers/programs.py |
| A | partner_programs module changes | partner_programs/serializers/verification.py |
| M | partner_programs module changes | partner_programs/services.py |
| A | partner_programs module changes | partner_programs/signals.py |
| M | partner_programs module changes | partner_programs/tasks.py |
| A | partner_programs module changes | partner_programs/templates/partner_programs/invite.html |
| M | partner_programs module changes | partner_programs/tests.py |
| A | partner_programs module changes | partner_programs/tests_analytics.py |
| A | partner_programs module changes | partner_programs/tests_edit_readiness.py |
| A | partner_programs module changes | partner_programs/tests_invites.py |
| A | partner_programs module changes | partner_programs/tests_verification.py |
| M | partner_programs module changes | partner_programs/urls.py |
| A | partner_programs module changes | partner_programs/verification_services.py |
| M | partner_programs module changes | partner_programs/views.py |
| M | module wiring in project config | procollab/celery.py |
| M | module wiring in project config | procollab/settings.py |
| M | module wiring in project config | procollab/urls.py |
| M | criteria/expert evaluation changes | project_rates/admin.py |
| M | criteria/expert evaluation changes | project_rates/models.py |
| M | criteria/expert evaluation changes | project_rates/serializers.py |
| A | criteria/expert evaluation changes | project_rates/tests_criteria_weight.py |
| A | criteria/expert evaluation changes | project_rates/tests_expert_evaluations.py |
| M | criteria/expert evaluation changes | project_rates/urls.py |
| M | criteria/expert evaluation changes | project_rates/views.py |
| A | company INN / participation rules support | projects/tests_program_participation_rules.py |
| M | company INN / participation rules support | projects/validators.py |
| M | notification preferences / expert search support | users/admin.py |
| M | notification preferences / expert search support | users/filters.py |
| M | notification preferences / expert search support | users/models.py |
| M | notification preferences / expert search support | users/serializers.py |
| M | notification preferences / expert search support | users/signals.py |
| M | notification preferences / expert search support | users/tests.py |
| A | notification preferences / expert search support | users/tests_filters.py |
| M | notification preferences / expert search support | users/urls.py |
| M | notification preferences / expert search support | users/views.py |

### Frontend

| Status | Reason | Файл |
| --- | --- | --- |
| M | isStaff for moderation routing | projects/social_platform/src/app/auth/models/user.model.ts |
| M | file upload support | projects/social_platform/src/app/core/services/file.service.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/detail/moderation-detail.component.html |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/detail/moderation-detail.component.scss |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/detail/moderation-detail.component.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/forbidden/moderation-forbidden.component.html |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/forbidden/moderation-forbidden.component.scss |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/forbidden/moderation-forbidden.component.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/list/moderation-list.component.html |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/list/moderation-list.component.scss |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/list/moderation-list.component.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/moderation-staff.guard.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/moderation.models.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/moderation.routes.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/moderation.service.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/verification-detail/verification-detail.component.html |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/verification-detail/verification-detail.component.scss |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/verification-detail/verification-detail.component.ts |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/verification-list/verification-list.component.html |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/verification-list/verification-list.component.scss |
| A | admin moderation UI | projects/social_platform/src/app/office/admin/moderation/verification-list/verification-list.component.ts |
| A | expert evaluations UI | projects/social_platform/src/app/office/expert/evaluations/expert-evaluations.component.html |
| A | expert evaluations UI | projects/social_platform/src/app/office/expert/evaluations/expert-evaluations.component.scss |
| A | expert evaluations UI | projects/social_platform/src/app/office/expert/evaluations/expert-evaluations.component.ts |
| M | program registration/project binding UI in detail page | projects/social_platform/src/app/office/features/detail/detail.component.html |
| M | program registration/project binding styles in detail page | projects/social_platform/src/app/office/features/detail/detail.component.scss |
| M | program registration/project binding logic in detail page | projects/social_platform/src/app/office/features/detail/detail.component.ts |
| M | navigation link for expert evaluations | projects/social_platform/src/app/office/features/nav/nav.component.html |
| M | navigation link for expert evaluations | projects/social_platform/src/app/office/features/nav/nav.component.ts |
| M | program links widget support | projects/social_platform/src/app/office/features/program-links/program-links.component.html |
| M | program links widget styles | projects/social_platform/src/app/office/features/program-links/program-links.component.scss |
| M | program links widget support | projects/social_platform/src/app/office/features/program-links/program-links.component.ts |
| M | program project submission flags | projects/social_platform/src/app/office/models/project.model.ts |
| M | module navigation shell | projects/social_platform/src/app/office/office.component.html |
| M | module navigation shell styles | projects/social_platform/src/app/office/office.component.scss |
| M | module navigation shell logic | projects/social_platform/src/app/office/office.component.ts |
| M | program/admin/expert routes | projects/social_platform/src/app/office/office.routes.ts |
| A | office/program module | projects/social_platform/src/app/office/program/analytics/program-analytics.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/analytics/program-analytics.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/analytics/program-analytics.component.spec.ts |
| A | office/program module | projects/social_platform/src/app/office/program/analytics/program-analytics.component.ts |
| M | office/program module | projects/social_platform/src/app/office/program/detail/detail.routes.ts |
| M | office/program module | projects/social_platform/src/app/office/program/detail/list/list.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/detail/main/components/program-context-actions/program-context-actions.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/detail/main/components/program-context-actions/program-context-actions.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/detail/main/components/program-context-actions/program-context-actions.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/detail/main/components/program-stat-cards/program-stat-cards.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/detail/main/components/program-stat-cards/program-stat-cards.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/detail/main/components/program-stat-cards/program-stat-cards.component.ts |
| M | office/program module | projects/social_platform/src/app/office/program/detail/main/main.component.html |
| M | office/program module | projects/social_platform/src/app/office/program/detail/main/main.component.scss |
| M | office/program module | projects/social_platform/src/app/office/program/detail/main/main.component.ts |
| M | office/program module | projects/social_platform/src/app/office/program/detail/register/register.component.html |
| M | office/program module | projects/social_platform/src/app/office/program/detail/register/register.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/_edit-form.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/edit.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/edit.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/edit.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/edit.routes.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/services/program-edit-state.service.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/criteria/program-edit-criteria.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/criteria/program-edit-criteria.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/criteria/program-edit-criteria.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/main/program-edit-main.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/main/program-edit-main.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/main/program-edit-main.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/materials/program-edit-materials.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/materials/program-edit-materials.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/materials/program-edit-materials.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/placeholder/program-edit-placeholder.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/placeholder/program-edit-placeholder.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/placeholder/program-edit-placeholder.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/registration/program-edit-registration.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/registration/program-edit-registration.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/registration/program-edit-registration.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/schedule/program-edit-schedule.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/schedule/program-edit-schedule.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/schedule/program-edit-schedule.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/verification/program-edit-verification.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/verification/program-edit-verification.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/edit/tabs/verification/program-edit-verification.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-detail.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-detail.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-detail.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-list.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-list.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/expert-evaluation/expert-evaluation-list.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/main/components/verification-banner/verification-banner.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/main/components/verification-banner/verification-banner.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/main/components/verification-banner/verification-banner.component.ts |
| M | office/program module | projects/social_platform/src/app/office/program/main/main.component.html |
| M | office/program module | projects/social_platform/src/app/office/program/main/main.component.scss |
| M | office/program module | projects/social_platform/src/app/office/program/main/main.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/main/sections/all-programs/all-programs.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/main/sections/all-programs/all-programs.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/main/sections/all-programs/all-programs.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.spec.ts |
| A | office/program module | projects/social_platform/src/app/office/program/main/sections/my-programs/my-programs.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/models/program-analytics.model.ts |
| A | office/program module | projects/social_platform/src/app/office/program/models/program-draft.model.ts |
| A | office/program module | projects/social_platform/src/app/office/program/models/program-verification.model.ts |
| M | office/program module | projects/social_platform/src/app/office/program/models/program.model.ts |
| A | office/program module | projects/social_platform/src/app/office/program/models/project-evaluation.model.ts |
| A | office/program module | projects/social_platform/src/app/office/program/models/readiness.model.ts |
| M | office/program module | projects/social_platform/src/app/office/program/program.component.html |
| M | office/program module | projects/social_platform/src/app/office/program/program.component.scss |
| M | office/program module | projects/social_platform/src/app/office/program/program.component.ts |
| M | office/program module | projects/social_platform/src/app/office/program/program.routes.ts |
| A | office/program module | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.spec.ts |
| A | office/program module | projects/social_platform/src/app/office/program/readiness-widget/readiness-widget.component.ts |
| M | office/program module | projects/social_platform/src/app/office/program/services/program.service.spec.ts |
| M | office/program module | projects/social_platform/src/app/office/program/services/program.service.ts |
| M | office/program module | projects/social_platform/src/app/office/program/services/project-rating.service.spec.ts |
| M | office/program module | projects/social_platform/src/app/office/program/services/project-rating.service.ts |
| A | office/program module | projects/social_platform/src/app/office/program/services/role-resolver.service.spec.ts |
| A | office/program module | projects/social_platform/src/app/office/program/services/role-resolver.service.ts |
| M | office/program module | projects/social_platform/src/app/office/program/shared/program-card/program-card.component.html |
| M | office/program module | projects/social_platform/src/app/office/program/shared/program-card/program-card.component.scss |
| M | office/program module | projects/social_platform/src/app/office/program/shared/program-card/program-card.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.spec.ts |
| A | office/program module | projects/social_platform/src/app/office/program/shared/program-status-badge/program-status-badge.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.spec.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/components/wizard-progress/wizard-progress.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/services/wizard-state.service.spec.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/services/wizard-state.service.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/basic-info-step/basic-info-step.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/basic-info-step/basic-info-step.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/basic-info-step/basic-info-step.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/publish-step/publish-step.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/publish-step/publish-step.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/publish-step/publish-step.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/registration-step/registration-step.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/registration-step/registration-step.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/steps/registration-step/registration-step.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/wizard.component.html |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/wizard.component.scss |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/wizard.component.ts |
| A | office/program module | projects/social_platform/src/app/office/program/wizard/wizard.routes.ts |
| M | program project additional fields | projects/social_platform/src/app/office/projects/edit/shared/project-additional-step/project-additional-step.component.html |
| M | program project additional fields | projects/social_platform/src/app/office/projects/edit/shared/project-additional-step/project-additional-step.component.ts |
| M | shared UI adjustment used in module | projects/social_platform/src/app/ui/components/avatar/avatar.component.html |
| M | shared UI adjustment used in module | projects/social_platform/src/app/ui/components/avatar/avatar.component.scss |
| M | shared UI adjustment used in module | projects/social_platform/src/app/ui/components/input/input.component.html |
| M | shared UI adjustment used in module | projects/social_platform/src/app/ui/components/input/input.component.ts |
| M | shared UI adjustment used in module | projects/social_platform/src/app/ui/components/search/search.component.html |
| M | shared UI adjustment used in module | projects/social_platform/src/app/ui/components/search/search.component.scss |
| M | shared UI adjustment used in module | projects/social_platform/src/app/ui/components/textarea/textarea.component.html |
| M | analytics export helper | projects/social_platform/src/app/utils/helpers/export-file.ts |
| A | registration phone formatting helper | projects/social_platform/src/app/utils/phone-format.ts |

## Файлы, исключенные из подсчета

### Backend

| Status | Reason | Файл |
| --- | --- | --- |
| M | неподдерживаемое расширение для LOC-подсчета | .env.example |
| M | неподдерживаемое расширение для LOC-подсчета | Dockerfile |
| M | неподдерживаемое расширение для LOC-подсчета | Makefile |
| A | migration-файл Django | certificates/migrations/0001_initial.py |
| A | migration-файл Django | certificates/migrations/0002_certificategenerationrun_issuedcertificate_and_more.py |
| A | migration-файл Django | certificates/migrations/__init__.py |
| A | outside defended backend module scope | core/management/__init__.py |
| A | outside defended backend module scope | core/management/commands/__init__.py |
| A | demo/seed script, не production-функционал модуля | core/management/commands/seed_demo_data.py |
| A | неподдерживаемое расширение для LOC-подсчета | docker-compose.local.yml |
| A | документация, не код модуля | docs/event_new_message.png |
| D | документация, не код модуля | docs/img/event_new_message.png |
| M | документация, не код модуля | docs/readme.md |
| A | документация, не код модуля | docs/vkr_backend_sections.md |
| A | документация, не код модуля | docs/vkr_case_championship_class_diagram.md |
| A | документация, не код модуля | docs/vkr_case_module_metrics_2026-05-06.md |
| A | документация, не код модуля | docs/vkr_chapter3_fact_reference.md |
| A | документация, не код модуля | docs/vkr_fact_pack_3_1_3_3.md |
| A | документация, не код модуля | docs/vkr_implementation_fact_sheet.md |
| A | исключенный каталог: media | media/uploads/2394475190026574791/5281308769219334356_958477822814830249.xlsx |
| A | исключенный каталог: media | media/uploads/346826438792592092/4269530436392559137_1300328082517782490.webp |
| A | исключенный каталог: media | media/uploads/346826438792592092/4269530436392559137_1378001432194575929.webp |
| A | исключенный каталог: media | media/uploads/346826438792592092/4269530436392559137_2093509723481436235.webp |
| A | исключенный каталог: media | media/uploads/346826438792592092/4269530436392559137_941134676153593457.webp |
| A | исключенный каталог: media | media/uploads/5483599611995116977/2553403184151069013_1206243972040705988.webp |
| A | исключенный каталог: media | media/uploads/5483599611995116977/2553403184151069013_1855536924323825584.webp |
| A | исключенный каталог: media | media/uploads/7128191035012563013/1117115275445963590_754705332839279897.png |
| A | исключенный каталог: media | media/uploads/7128191035012563013/6652894554411779159_2175937911193234675.webp |
| A | исключенный каталог: media | media/uploads/7128191035012563013/7337056980775564389_1785506279972302065.webp |
| A | исключенный каталог: media | media/uploads/7128191035012563013/8587525820074953722_1050888476594695413.webp |
| A | исключенный каталог: media | media/uploads/7313098430035730136/2268652618852259992_924720616818850144.xlsx |
| A | исключенный каталог: media | media/uploads/7313098430035730136/4708263898070464088_1108998215878293871.webp |
| A | исключенный каталог: media | media/uploads/7313098430035730136/4708263898070464088_1681485333158935119.webp |
| A | исключенный каталог: media | media/uploads/7313098430035730136/4708263898070464088_1818761558910024320.webp |
| A | исключенный каталог: media | media/uploads/7313098430035730136/4708263898070464088_2256899350392715910.webp |
| A | исключенный каталог: media | media/uploads/7313098430035730136/4708263898070464088_527332925284792964.webp |
| A | исключенный каталог: media | media/uploads/7313098430035730136/4708263898070464088_687246446184348297.webp |
| A | исключенный каталог: media | media/uploads/7661041481428638865/5179994385857470432_1374696849997296111.pdf |
| A | исключенный каталог: media | media/uploads/7661041481428638865/7534929383385515916_1624289837793145224.webp |
| A | исключенный каталог: media | media/uploads/7661041481428638865/7661928318062145986_88620089220264435.webp |
| A | исключенный каталог: media | media/uploads/907991477247903368/1806639590340926846_859943988780234858.webp |
| A | migration-файл Django | moderation/migrations/0001_initial.py |
| A | migration-файл Django | moderation/migrations/0002_alter_moderationlog_action.py |
| A | migration-файл Django | moderation/migrations/0003_alter_moderationlog_action.py |
| A | migration-файл Django | moderation/migrations/0004_alter_moderationlog_action_and_verbose.py |
| A | migration-файл Django | moderation/migrations/0005_moderationlog_sections_to_fix.py |
| A | migration-файл Django | moderation/migrations/__init__.py |
| A | migration-файл Django | partner_programs/migrations/0017_partnerprogram_company_partnerprogram_frozen_at_and_more.py |
| A | migration-файл Django | partner_programs/migrations/0018_data_migration_draft_to_status.py |
| A | migration-файл Django | partner_programs/migrations/0019_partnerprogramverificationrequest.py |
| A | migration-файл Django | partner_programs/migrations/0020_partnerprograminvite.py |
| A | migration-файл Django | partner_programs/migrations/0021_partnerprogram_participation_rules.py |
| A | migration-файл Django | partner_programs/migrations/0022_verification_request_snapshot_fields.py |
| A | неподдерживаемое расширение для LOC-подсчета | partner_programs/templates/partner_programs/email/invite.txt |
| A | migration-файл Django | project_rates/migrations/0004_criteria_weight.py |
| A | migration-файл Django | project_rates/migrations/0005_projectevaluation_projectevaluationscore.py |
| A | migration-файл Django | projects/migrations/0033_alter_company_inn.py |
| A | migration-файл Django | users/migrations/0061_alter_customuser_about_me.py |
| A | migration-файл Django | users/migrations/0062_usernotificationpreferences.py |
| A | migration-файл Django | users/migrations/0063_create_existing_notification_preferences.py |
| M | users file outside notification/expert support scope | users/tasks.py |

### Frontend

| Status | Reason | Файл |
| --- | --- | --- |
| A | лог запуска/сервера | frontend.analytics.serve.err.log |
| A | лог запуска/сервера | frontend.analytics.serve.log |
| A | лог запуска/сервера | frontend.current.err.log |
| A | лог запуска/сервера | frontend.current.log |
| A | лог запуска/сервера | frontend.err.log |
| A | лог запуска/сервера | frontend.expert-evaluation.serve.err.log |
| A | лог запуска/сервера | frontend.expert-evaluation.serve.log |
| A | лог запуска/сервера | frontend.f02.err.log |
| A | лог запуска/сервера | frontend.f02.log |
| A | лог запуска/сервера | frontend.log |
| A | лог запуска/сервера | frontend.mobile-cjm.serve.err.log |
| A | лог запуска/сервера | frontend.mobile-cjm.serve.log |
| A | лог запуска/сервера | frontend.moderation.serve.err.log |
| A | лог запуска/сервера | frontend.moderation.serve.log |
| A | лог запуска/сервера | frontend.platform.serve.err.log |
| A | лог запуска/сервера | frontend.platform.serve.log |
| A | лог запуска/сервера | frontend.verification.serve.err.log |
| A | лог запуска/сервера | frontend.verification.serve.log |
| A | лог запуска/сервера | frontend.wizard.err.log |
| A | лог запуска/сервера | frontend.wizard.log |
| M | outside defended frontend module scope | projects/social_platform/src/app/app.component.html |
| M | outside defended frontend module scope | projects/social_platform/src/app/auth/register/register.component.html |
| M | outside defended frontend module scope | projects/social_platform/src/app/auth/register/register.component.ts |
| M | outside defended frontend module scope | projects/social_platform/src/app/office/feed/shared/open-vacancy/open-vacancy.component.ts |
| M | outside defended frontend module scope | projects/social_platform/src/app/office/members/members.component.ts |
| M | outside defended frontend module scope | projects/social_platform/src/app/office/profile/edit/edit.component.html |
| M | outside defended frontend module scope | projects/social_platform/src/app/office/profile/edit/edit.component.ts |
| A | outside defended frontend module scope | projects/social_platform/src/app/utils/helpers/russian-plural.ts |
| M | outside defended frontend module scope | projects/social_platform/src/environments/environment.ts |
| M | outside defended frontend module scope | projects/social_platform/src/index.html |
| M | outside defended frontend module scope | projects/social_platform/src/styles.scss |

## Рекомендация для ВКР

Самая защитоспособная основная формулировка — использовать DIFF ADDED LOC по отфильтрованным файлам модуля: около 38328 строк добавленного и измененного кода, включая 34457 строк production-кода и 3871 строк тестового/spec-кода.

Формулировка: "Объем добавленного и измененного кода по файлам разработанного модуля кейс-чемпионатов составил около 38328 строк, включая 34457 строк production-кода и 3871 строк тестового/spec-кода. Показатель рассчитан по diff относительно исходной ветки; измененная строка учитывалась как удаленная старая и добавленная новая, поэтому метрика отражает объем доработки, а не число уникально написанных с нуля строк."
