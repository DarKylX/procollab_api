import os
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Skill, SkillCategory, SkillToObject
from core.models import Specialization, SpecializationCategory
from files.models import UserFile
from files.service import CDN, get_default_storage
from industries.models import Industry
from moderation.models import ModerationLog
from notifications.models import Notification, NotificationDelivery
from partner_programs.models import (
    LegalDocument,
    PartnerProgram,
    PartnerProgramField,
    PartnerProgramFieldValue,
    PartnerProgramInvite,
    PartnerProgramLegalSettings,
    PartnerProgramMaterial,
    PartnerProgramParticipantConsent,
    PartnerProgramProject,
    PartnerProgramUserProfile,
    PartnerProgramVerificationRequest,
)
from project_rates.models import (
    Criteria,
    ProjectEvaluation,
    ProjectEvaluationScore,
    ProjectExpertAssignment,
    ProjectScore,
)
from projects.models import Collaborator, Company, Project, ProjectCompany, ProjectLink
from users.models import Expert, Member, UserNotificationPreferences

User = get_user_model()

DEFAULT_DEMO_PASSWORD = "ProcollabDemo2026!"
DEMO_EMAIL_DOMAIN = "demo.procollab.pro"
DEMO_VERSION = "selectel-preprod-2026-05"
MIN_NON_CROSS_RECORDS = 300
DEMO_PARTICIPANT_COUNT = 42
DEMO_EXPERT_COUNT = 8
DEMO_ORGANIZER_COUNT = 6
DEMO_ADMIN_COUNT = 2
DEMO_PROJECT_COUNT = 36

SKILLS_BY_CATEGORY = {
    "Разработка": [
        "Python",
        "Django",
        "Django REST Framework",
        "Angular",
        "TypeScript",
        "PostgreSQL",
        "Redis",
        "Docker",
        "Git",
        "REST API",
    ],
    "Продукт и аналитика": [
        "Product Management",
        "Customer Development",
        "User Research",
        "A/B Testing",
        "SQL Analytics",
        "BI dashboards",
        "Unit economics",
        "Roadmapping",
    ],
    "Дизайн": [
        "UX Research",
        "UI Design",
        "Figma",
        "Design Systems",
        "Prototyping",
        "Usability Testing",
        "Accessibility",
    ],
    "AI и данные": [
        "Machine Learning",
        "Data Engineering",
        "NLP",
        "Computer Vision",
        "MLOps",
        "Prompt Engineering",
        "Data Visualization",
    ],
    "Бизнес": [
        "Market Research",
        "Go-to-market",
        "B2B Sales",
        "Pitch Deck",
        "Financial Modeling",
        "Legal Basics",
        "Project Management",
        "Presentation Skills",
    ],
}

SPECIALIZATIONS_BY_CATEGORY = {
    "Разработка": [
        "Backend-разработчик",
        "Frontend-разработчик",
        "Fullstack-разработчик",
        "DevOps-инженер",
        "QA-инженер",
        "Mobile-разработчик",
    ],
    "Продукт": [
        "Product manager",
        "Project manager",
        "Product analyst",
        "Business analyst",
        "Scrum master",
    ],
    "Дизайн": [
        "UX/UI-дизайнер",
        "UX-исследователь",
        "Графический дизайнер",
        "Дизайнер презентаций",
        "Контент-дизайнер",
    ],
    "Данные и AI": [
        "Data scientist",
        "Data analyst",
        "ML-инженер",
        "Data engineer",
        "AI product specialist",
    ],
    "Бизнес и коммуникации": [
        "Маркетолог",
        "PR-специалист",
        "Sales manager",
        "Юрист проекта",
        "Финансовый аналитик",
    ],
}

PROGRAM_FIELDS = [
    {
        "name": "track",
        "label": "Направление решения",
        "field_type": "select",
        "is_required": True,
        "help_text": "Выберите трек, к которому относится проект.",
        "show_filter": True,
        "options": "AI-сервисы|Городская среда|Образование|Экология",
    },
    {
        "name": "team_role",
        "label": "Роль команды",
        "field_type": "radio",
        "is_required": True,
        "help_text": "Какую роль команда берет в пилоте.",
        "show_filter": True,
        "options": "Исследование|Прототип|MVP|Пилотирование",
    },
    {
        "name": "motivation",
        "label": "Почему команда хочет участвовать",
        "field_type": "textarea",
        "is_required": True,
        "help_text": "Коротко опишите мотивацию и ожидаемый результат.",
        "show_filter": False,
        "options": "",
    },
]

PROGRAM_CRITERIA = [
    {
        "name": "Проблема и рынок",
        "description": "Насколько ясно описана проблема, аудитория и ценность решения.",
        "type": "int",
        "min_value": 0,
        "max_value": 10,
        "weight": 30,
    },
    {
        "name": "Технологичность",
        "description": "Качество технического решения, реализуемость и масштабируемость.",
        "type": "int",
        "min_value": 0,
        "max_value": 10,
        "weight": 30,
    },
    {
        "name": "Пользовательский опыт",
        "description": "Удобство сценария, понятность интерфейса и работа с обратной связью.",
        "type": "int",
        "min_value": 0,
        "max_value": 10,
        "weight": 20,
    },
    {
        "name": "Презентация",
        "description": "Качество защиты, структура питча и ответы на вопросы.",
        "type": "int",
        "min_value": 0,
        "max_value": 10,
        "weight": 20,
    },
]

PROGRAMS = [
    {
        "tag": "demo-draft-ai-city",
        "name": "Черновик: AI-сервис для городской среды",
        "status": PartnerProgram.STATUS_DRAFT,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_NOT_REQUESTED,
        "is_private": False,
        "offset": 45,
    },
    {
        "tag": "demo-pending-edtech",
        "name": "На модерации: EdTech Challenge",
        "status": PartnerProgram.STATUS_PENDING_MODERATION,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_PENDING,
        "is_private": False,
        "offset": 30,
    },
    {
        "tag": "demo-published-smart-campus",
        "name": "PROCOLLAB Smart Campus Challenge",
        "status": PartnerProgram.STATUS_PUBLISHED,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_VERIFIED,
        "is_private": False,
        "offset": -7,
    },
    {
        "tag": "demo-rejected-fintech",
        "name": "На доработке: FinTech Data Sprint",
        "status": PartnerProgram.STATUS_REJECTED,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_REJECTED,
        "is_private": False,
        "offset": 20,
    },
    {
        "tag": "demo-private-industry",
        "name": "Закрытый чемпионат: Industrial AI Lab",
        "status": PartnerProgram.STATUS_PUBLISHED,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_VERIFIED,
        "is_private": True,
        "offset": -3,
    },
    {
        "tag": "demo-published-green-tech",
        "name": "GreenTech Product Sprint",
        "status": PartnerProgram.STATUS_PUBLISHED,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_VERIFIED,
        "is_private": False,
        "offset": -14,
    },
    {
        "tag": "demo-published-health-data",
        "name": "Health Data MVP Challenge",
        "status": PartnerProgram.STATUS_PUBLISHED,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_VERIFIED,
        "is_private": False,
        "participation_format": PartnerProgram.PARTICIPATION_FORMAT_INDIVIDUAL,
        "team_min": 1,
        "team_max": 1,
        "offset": -21,
    },
    {
        "tag": "demo-pending-logistics",
        "name": "На модерации: Logistics Optimization Cup",
        "status": PartnerProgram.STATUS_PENDING_MODERATION,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_PENDING,
        "is_private": False,
        "manager": "organizer_pending",
        "company": "pending",
        "offset": 12,
    },
    {
        "tag": "demo-rejected-culture",
        "name": "На доработке: Creative Industries Challenge",
        "status": PartnerProgram.STATUS_REJECTED,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_REJECTED,
        "is_private": False,
        "manager": "organizer_rejected",
        "company": "rejected",
        "offset": 18,
    },
    {
        "tag": "demo-draft-unverified-company",
        "name": "Черновик: Robotics Student League",
        "status": PartnerProgram.STATUS_DRAFT,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_NOT_REQUESTED,
        "is_private": False,
        "manager": "organizer_unverified",
        "company": "unverified",
        "offset": 60,
    },
    {
        "tag": "demo-completed-sustainable-campus",
        "name": "Завершен: Sustainable Campus Hack",
        "status": PartnerProgram.STATUS_COMPLETED,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_VERIFIED,
        "is_private": False,
        "offset": -90,
    },
    {
        "tag": "demo-frozen-cybersecurity",
        "name": "Заморожен: Cybersecurity Case Cup",
        "status": PartnerProgram.STATUS_FROZEN,
        "verification_status": PartnerProgram.VERIFICATION_STATUS_VERIFIED,
        "is_private": False,
        "offset": -40,
    },
]


class Command(BaseCommand):
    help = (
        "Seed Selectel pre-prod with idempotent demo data for autonomous case "
        "championships. Usage: python manage.py seed_demo_data or "
        "DEMO_PASSWORD=... python manage.py seed_demo_data"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=None,
            help="Password for all demo accounts. Defaults to DEMO_PASSWORD env.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = (
            options.get("password")
            or os.environ.get("DEMO_PASSWORD")
            or DEFAULT_DEMO_PASSWORD
        )

        specializations = self._ensure_specializations()
        skills = self._ensure_skills()
        industry = self._ensure_industry()
        users = self._ensure_demo_users(password, specializations, skills)
        companies = self._ensure_companies()
        demo_file = self._ensure_demo_file(users["organizer"])
        programs = self._ensure_programs(users, companies, demo_file)
        published_program = programs["demo-published-smart-campus"]
        self._ensure_project_submission(
            program=published_program,
            users=users,
            company=companies["verified"],
            industry=industry,
        )
        self._ensure_project_cohort(
            programs=programs,
            users=users,
            companies=companies,
            industry=industry,
        )
        self._ensure_notifications(programs, users)
        self._ensure_bulk_notifications(programs, users)
        demo_record_count = self._count_demo_records()

        self.stdout.write(self.style.SUCCESS("Selectel demo data is ready."))
        self.stdout.write("Demo login accounts:")
        for label, user in self._login_account_items(users):
            self.stdout.write(f"- {label}: {user.email}")
        self.stdout.write(f"Demo password: {password}")
        self.stdout.write(f"Published program: {published_program.name}")
        self.stdout.write(f"Material file URL: {demo_file.link}")
        self.stdout.write(
            f"Demo non-cross/domain records: {demo_record_count} "
            f"(minimum target: {MIN_NON_CROSS_RECORDS})"
        )
        if demo_record_count < MIN_NON_CROSS_RECORDS:
            self.stdout.write(
                self.style.WARNING(
                    "Demo record count is below the diploma method target."
                )
            )
        if password == DEFAULT_DEMO_PASSWORD:
            self.stdout.write(
                self.style.WARNING(
                    "Using default pre-prod password. Override with DEMO_PASSWORD=..."
                )
            )

    def _ensure_specializations(self):
        specializations = []
        for category_name, names in SPECIALIZATIONS_BY_CATEGORY.items():
            category = self._upsert_first(
                SpecializationCategory,
                {"name": category_name},
                {},
            )
            for name in names:
                specializations.append(
                    self._upsert_first(
                        Specialization,
                        {"category": category, "name": name},
                        {},
                    )
                )
        return specializations

    def _ensure_skills(self):
        skills = []
        for category_name, names in SKILLS_BY_CATEGORY.items():
            category = self._upsert_first(SkillCategory, {"name": category_name}, {})
            for name in names:
                skills.append(
                    self._upsert_first(Skill, {"category": category, "name": name}, {})
                )
        return skills

    def _ensure_industry(self):
        return self._upsert_first(
            Industry,
            {"name": "Цифровые продукты и городские сервисы"},
            {},
        )

    def _ensure_demo_users(self, password, specializations, skills):
        users = {
            "admin": self._ensure_user(
                email=f"admin@{DEMO_EMAIL_DOMAIN}",
                first_name="Алина",
                last_name="Платформенная",
                password=password,
                user_type=User.MEMBER,
                is_staff=True,
                is_superuser=True,
                specialization=specializations[0],
            ),
            "staff": self._ensure_user(
                email=f"staff@{DEMO_EMAIL_DOMAIN}",
                first_name="Степан",
                last_name="Модераторов",
                password=password,
                user_type=User.MEMBER,
                is_staff=True,
                specialization=specializations[4],
            ),
            "organizer": self._ensure_user(
                email=f"organizer@{DEMO_EMAIL_DOMAIN}",
                first_name="Олег",
                last_name="Организаторов",
                password=password,
                user_type=User.MEMBER,
                specialization=specializations[1],
            ),
            "organizer_pending": self._ensure_user(
                email=f"organizer.pending@{DEMO_EMAIL_DOMAIN}",
                first_name="Полина",
                last_name="Проверяемая",
                password=password,
                user_type=User.MEMBER,
                specialization=specializations[6],
            ),
            "organizer_rejected": self._ensure_user(
                email=f"organizer.rejected@{DEMO_EMAIL_DOMAIN}",
                first_name="Роман",
                last_name="Доработкин",
                password=password,
                user_type=User.MEMBER,
                specialization=specializations[7],
            ),
            "organizer_unverified": self._ensure_user(
                email=f"organizer.unverified@{DEMO_EMAIL_DOMAIN}",
                first_name="Ульяна",
                last_name="Черновикова",
                password=password,
                user_type=User.MEMBER,
                specialization=specializations[8],
            ),
            "expert": self._ensure_user(
                email=f"expert@{DEMO_EMAIL_DOMAIN}",
                first_name="Элина",
                last_name="Экспертова",
                password=password,
                user_type=User.EXPERT,
                specialization=specializations[-5],
            ),
            "expert_product": self._ensure_user(
                email=f"expert.product@{DEMO_EMAIL_DOMAIN}",
                first_name="Петр",
                last_name="Продуктов",
                password=password,
                user_type=User.EXPERT,
                specialization=specializations[-4],
            ),
            "participant": self._ensure_user(
                email=f"participant@{DEMO_EMAIL_DOMAIN}",
                first_name="Павел",
                last_name="Участников",
                password=password,
                user_type=User.MEMBER,
                specialization=specializations[2],
            ),
            "teammate": self._ensure_user(
                email=f"teammate@{DEMO_EMAIL_DOMAIN}",
                first_name="Тамара",
                last_name="Командная",
                password=password,
                user_type=User.MEMBER,
                specialization=specializations[3],
            ),
        }

        users["participant_pool"] = [
            users["participant"],
            users["teammate"],
            *self._ensure_user_cohort(
                prefix="participant",
                count=DEMO_PARTICIPANT_COUNT,
                password=password,
                user_type=User.MEMBER,
                specializations=specializations,
            ),
        ]
        users["expert_pool"] = [
            users["expert"],
            users["expert_product"],
            *self._ensure_user_cohort(
                prefix="expert",
                count=DEMO_EXPERT_COUNT,
                password=password,
                user_type=User.EXPERT,
                specializations=specializations,
            ),
        ]
        users["organizer_pool"] = [
            users["organizer"],
            users["organizer_pending"],
            users["organizer_rejected"],
            users["organizer_unverified"],
            *self._ensure_user_cohort(
                prefix="organizer",
                count=DEMO_ORGANIZER_COUNT,
                password=password,
                user_type=User.MEMBER,
                specializations=specializations,
            ),
        ]
        users["admin_pool"] = [
            users["admin"],
            users["staff"],
            *self._ensure_user_cohort(
                prefix="admin",
                count=DEMO_ADMIN_COUNT,
                password=password,
                user_type=User.MEMBER,
                specializations=specializations,
                is_staff=True,
            ),
        ]

        for index, user in enumerate(self._iter_unique_users(users)):
            start = index % max(len(skills), 1)
            rotated_skills = skills[start:] + skills[:start]
            self._ensure_user_skills(user, rotated_skills[:5])
        return users

    def _ensure_user_cohort(
        self,
        *,
        prefix,
        count,
        password,
        user_type,
        specializations,
        is_staff=False,
    ):
        cohort = []
        for index in range(1, count + 1):
            cohort.append(
                self._ensure_user(
                    email=f"{prefix}.{index:03d}@{DEMO_EMAIL_DOMAIN}",
                    first_name=f"Demo{index:03d}",
                    last_name=prefix.capitalize(),
                    password=password,
                    user_type=user_type,
                    specialization=specializations[index % len(specializations)],
                    is_staff=is_staff,
                )
            )
        return cohort

    def _iter_unique_users(self, users):
        seen = set()
        for value in users.values():
            values = value if isinstance(value, list) else [value]
            for user in values:
                if not hasattr(user, "id") or user.id in seen:
                    continue
                seen.add(user.id)
                yield user

    def _login_account_items(self, users):
        labels = (
            "admin",
            "staff",
            "organizer",
            "organizer_pending",
            "organizer_rejected",
            "organizer_unverified",
            "expert",
            "expert_product",
            "participant",
            "teammate",
        )
        return [(label, users[label]) for label in labels]

    def _ensure_user(
        self,
        *,
        email,
        first_name,
        last_name,
        password,
        user_type,
        specialization,
        is_staff=False,
        is_superuser=False,
    ):
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User(email=email)

        user.first_name = first_name
        user.last_name = last_name
        user.birthday = date(1998, 1, 1)
        user.city = "Москва"
        user.region = "Москва"
        user.about_me = (
            "Демо-профиль для Selectel pre-prod стенда автономных "
            "кейс-чемпионатов PROCOLLAB."
        )
        user.status = "Готов к демо-сценарию"
        user.user_type = user_type
        user.v2_speciality = specialization
        user.speciality = specialization.name
        user.onboarding_stage = None
        user.is_active = True
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()

        UserNotificationPreferences.objects.get_or_create(user=user)
        if user_type == User.EXPERT:
            Expert.objects.get_or_create(
                user=user,
                defaults={
                    "preferred_industries": "EdTech, AI, Smart City",
                    "useful_to_project": "Оценка продуктовой гипотезы и архитектуры.",
                },
            )
        else:
            Member.objects.get_or_create(user=user)
        return user

    def _ensure_user_skills(self, user, skills):
        content_type = ContentType.objects.get_for_model(User)
        for skill in skills:
            exists = SkillToObject.objects.filter(
                content_type=content_type,
                object_id=user.id,
                skill=skill,
            ).exists()
            if not exists:
                SkillToObject.objects.create(
                    content_type=content_type,
                    object_id=user.id,
                    skill=skill,
                )

    def _ensure_companies(self):
        return {
            "verified": self._upsert_first(
                Company,
                {"inn": "7707083893"},
                {"name": 'ООО "Цифровые городские решения"'},
            ),
            "pending": self._upsert_first(
                Company,
                {"inn": "7802870820"},
                {"name": 'ООО "Образовательные лаборатории"'},
            ),
            "rejected": self._upsert_first(
                Company,
                {"inn": "7714783093"},
                {"name": 'ООО "Креативные индустрии"'},
            ),
            "unverified": self._upsert_first(
                Company,
                {"inn": "5406567890"},
                {"name": 'ООО "Робототехника кампуса"'},
            ),
        }

    def _ensure_demo_file(self, owner):
        existing = UserFile.objects.filter(
            user=owner,
            name="selectel-demo-championship-rules",
            extension="txt",
        ).first()
        if existing:
            return existing

        content = ContentFile(
            (
                "PROCOLLAB Selectel pre-prod demo material\n\n"
                "This file is generated by seed_demo_data and saved through "
                "the configured FILE_STORAGE backend. It is safe demo content "
                "for checking local media delivery under /media/uploads/.\n"
            ).encode("utf-8"),
            name="selectel-demo-championship-rules.txt",
        )
        uploaded = SimpleUploadedFile(
            content.name,
            content.read(),
            content_type="text/plain",
        )
        file_info = CDN(get_default_storage()).upload(
            uploaded,
            owner,
            preserve_original=True,
        )
        return UserFile.objects.create(
            link=file_info.url,
            user=owner,
            name=file_info.name,
            extension=file_info.extension,
            mime_type=file_info.mime_type,
            size=file_info.size,
        )

    def _ensure_programs(self, users, companies, demo_file):
        programs = {}
        expert_profiles = [user.expert for user in users["expert_pool"][:4]]
        for program_data in PROGRAMS:
            manager = users[program_data.get("manager", "organizer")]
            company = companies[program_data.get("company", "verified")]
            program = self._ensure_program(
                program_data=program_data,
                manager=manager,
                company=company,
            )
            program.managers.set([manager])
            program.experts.set(expert_profiles)
            for expert_profile in expert_profiles:
                expert_profile.programs.add(program)
            self._ensure_program_fields(program)
            self._ensure_program_materials(program, demo_file)
            if program.presentation_address != demo_file.link:
                program.presentation_address = demo_file.link
                program.save(update_fields=["presentation_address", "datetime_updated"])
            self._ensure_program_criteria(program)
            self._ensure_program_legal_settings(program, manager, demo_file)
            self._ensure_verification_request(
                program,
                users,
                company,
                demo_file,
                manager=manager,
            )
            self._ensure_moderation_log(program, users["admin"])
            if program.is_private:
                self._ensure_invite(program, users)
            program.readiness = program.calculate_readiness()
            program.save(update_fields=["readiness", "datetime_updated"])
            programs[program.tag] = program
        return programs

    def _ensure_program(self, *, program_data, manager, company):
        now = timezone.now()
        started = now + timedelta(days=program_data["offset"])
        registration_ends = started + timedelta(days=21)
        submission_ends = registration_ends + timedelta(days=14)
        evaluation_ends = submission_ends + timedelta(days=14)
        finished = evaluation_ends + timedelta(days=7)
        status = program_data["status"]

        defaults = {
            "name": program_data["name"],
            "description": self._program_description(program_data["name"]),
            "is_competitive": True,
            "city": "Москва",
            "image_address": (
                "https://picsum.photos/seed/"
                f"{program_data['tag']}-avatar/640/640"
            ),
            "cover_image_address": (
                "https://picsum.photos/seed/"
                f"{program_data['tag']}-cover/1280/480"
            ),
            "advertisement_image_address": (
                "https://picsum.photos/seed/"
                f"{program_data['tag']}-ad/1080/540"
            ),
            "presentation_address": "https://procollab.pro/media/demo/pitch-template.pdf",
            "registration_link": "",
            "max_project_rates": 1,
            "is_distributed_evaluation": False,
            "data_schema": {
                "team_role": {"type": "select"},
                "track": {"type": "select"},
                "motivation": {"type": "textarea"},
            },
            "draft": status == PartnerProgram.STATUS_DRAFT,
            "status": status,
            "verification_status": program_data["verification_status"],
            "is_private": program_data["is_private"],
            "projects_availability": "all_users",
            "publish_projects_after_finish": True,
            "participation_format": program_data.get(
                "participation_format",
                PartnerProgram.PARTICIPATION_FORMAT_TEAM,
            ),
            "project_team_min_size": program_data.get("team_min", 2),
            "project_team_max_size": program_data.get("team_max", 4),
            "company": company,
            "datetime_started": started,
            "datetime_registration_ends": registration_ends,
            "datetime_project_submission_ends": submission_ends,
            "datetime_evaluation_ends": evaluation_ends,
            "datetime_finished": finished,
            "frozen_at": None,
        }
        return self._upsert_first(
            PartnerProgram,
            {"tag": program_data["tag"]},
            defaults,
        )

    def _program_description(self, name):
        return (
            f"{name} — демонстрационный кейс-чемпионат PROCOLLAB для защиты "
            "дипломного сценария. Участники собирают команду, регистрируют "
            "проект, заполняют дополнительные поля, прикладывают материалы и "
            "отправляют решение на экспертную оценку. Организатор видит "
            "состояния модерации, готовность программы, материалы, критерии, "
            "экспертов и отправленные проекты. Описание специально длиннее "
            "минимального порога, чтобы readiness-проверка базовой информации "
            "считалась выполненной на pre-prod стенде."
        )

    def _ensure_program_fields(self, program):
        for field_data in PROGRAM_FIELDS:
            self._upsert_first(
                PartnerProgramField,
                {"partner_program": program, "name": field_data["name"]},
                {
                    "label": field_data["label"],
                    "field_type": field_data["field_type"],
                    "is_required": field_data["is_required"],
                    "help_text": field_data["help_text"],
                    "show_filter": field_data["show_filter"],
                    "options": field_data["options"],
                },
            )

    def _ensure_program_materials(self, program, demo_file):
        self._upsert_first(
            PartnerProgramMaterial,
            {"program": program, "title": "Регламент демо-чемпионата"},
            {"file": demo_file, "url": demo_file.link},
        )
        self._upsert_first(
            PartnerProgramMaterial,
            {"program": program, "title": "Шаблон презентации проекта"},
            {"file": demo_file, "url": demo_file.link},
        )

    def _ensure_program_criteria(self, program):
        for criterion_data in PROGRAM_CRITERIA:
            self._upsert_first(
                Criteria,
                {"partner_program": program, "name": criterion_data["name"]},
                {
                    "description": criterion_data["description"],
                    "type": criterion_data["type"],
                    "min_value": criterion_data["min_value"],
                    "max_value": criterion_data["max_value"],
                    "weight": criterion_data["weight"],
                },
            )

    def _ensure_program_legal_settings(self, program, organizer, demo_file):
        legal_settings, _ = PartnerProgramLegalSettings.objects.update_or_create(
            program=program,
            defaults={
                "participation_rules_file": demo_file,
                "participation_rules_link": "",
                "additional_terms_text": (
                    "Демо-условия участия для pre-prod стенда. Не являются "
                    "публичной офертой и используются только для показа ВКР."
                ),
                "organizer_terms_accepted_by": organizer,
                "organizer_terms_accepted_at": timezone.now(),
                "organizer_terms_version": DEMO_VERSION,
            },
        )
        for document_type, title in (
            (LegalDocument.TYPE_PRIVACY_POLICY, "Демо-политика обработки данных"),
            (LegalDocument.TYPE_PARTICIPANT_CONSENT, "Демо-согласие участника"),
            (LegalDocument.TYPE_PARTICIPATION_TERMS, "Демо-правила участия"),
            (LegalDocument.TYPE_ORGANIZER_TERMS, "Демо-условия организатора"),
        ):
            self._upsert_first(
                LegalDocument,
                {"type": document_type, "version": DEMO_VERSION},
                {
                    "title": title,
                    "content_url": demo_file.link,
                    "content_html": "",
                    "is_active": True,
                },
            )
        return legal_settings

    def _ensure_verification_request(self, program, users, company, demo_file, manager):
        status_map = {
            PartnerProgram.VERIFICATION_STATUS_PENDING: (
                PartnerProgramVerificationRequest.STATUS_PENDING,
                None,
                "",
            ),
            PartnerProgram.VERIFICATION_STATUS_VERIFIED: (
                PartnerProgramVerificationRequest.STATUS_APPROVED,
                users["admin"],
                "Компания подтверждена для демо-стенда.",
            ),
            PartnerProgram.VERIFICATION_STATUS_REJECTED: (
                PartnerProgramVerificationRequest.STATUS_REJECTED,
                users["admin"],
                "Демо-пример заявки на доработку.",
            ),
        }
        request_status, decided_by, admin_comment = status_map.get(
            program.verification_status,
            (None, None, ""),
        )
        if request_status is None:
            return None

        verification_request = PartnerProgramVerificationRequest.objects.filter(
            program=program,
            status=request_status,
        ).first()
        defaults = {
            "company": company,
            "company_name": company.name,
            "inn": company.inn,
            "legal_name": company.name,
            "ogrn": "1027700132195",
            "website": "https://procollab.pro",
            "region": "Москва",
            "initiator": manager,
            "contact_full_name": manager.get_full_name(),
            "contact_position": "Руководитель образовательных программ",
            "contact_email": manager.email,
            "contact_phone": "+7 999 000-00-01",
            "status": request_status,
            "decided_at": timezone.now() if decided_by else None,
            "decided_by": decided_by,
            "admin_comment": admin_comment,
            "rejection_reason": (
                PartnerProgramVerificationRequest.REJECTION_OTHER
                if request_status == PartnerProgramVerificationRequest.STATUS_REJECTED
                else ""
            ),
        }
        if verification_request is None:
            verification_request = PartnerProgramVerificationRequest.objects.create(
                program=program,
                **defaults,
            )
        else:
            for field, value in defaults.items():
                setattr(verification_request, field, value)
            verification_request.save()
        verification_request.documents.add(demo_file)
        return verification_request

    def _ensure_moderation_log(self, program, admin):
        if program.status == PartnerProgram.STATUS_DRAFT:
            return None

        action_by_status = {
            PartnerProgram.STATUS_PENDING_MODERATION: (
                ModerationLog.ACTION_SUBMIT_TO_MODERATION,
                PartnerProgram.STATUS_DRAFT,
                PartnerProgram.STATUS_PENDING_MODERATION,
                "Демо-чемпионат отправлен на модерацию.",
                "",
            ),
            PartnerProgram.STATUS_PUBLISHED: (
                ModerationLog.ACTION_APPROVE,
                PartnerProgram.STATUS_PENDING_MODERATION,
                PartnerProgram.STATUS_PUBLISHED,
                "Демо-чемпионат одобрен для публикации.",
                "",
            ),
            PartnerProgram.STATUS_REJECTED: (
                ModerationLog.ACTION_REJECT,
                PartnerProgram.STATUS_PENDING_MODERATION,
                PartnerProgram.STATUS_REJECTED,
                "Демо-чемпионат требует доработки материалов.",
                ModerationLog.REJECTION_REASON_INSUFFICIENT_DATA,
            ),
        }
        if program.status not in action_by_status:
            return None
        action, before, after, comment, rejection_reason = action_by_status[program.status]
        log = ModerationLog.objects.filter(
            program=program,
            action=action,
            status_after=after,
        ).first()
        if log:
            log.status_before = before
            log.comment = comment
            log.rejection_reason = rejection_reason
            log.save()
            return log
        return ModerationLog.objects.create(
            program=program,
            author=admin,
            action=action,
            status_before=before,
            status_after=after,
            comment=comment,
            rejection_reason=rejection_reason,
        )

    def _ensure_invite(self, program, users):
        invite = PartnerProgramInvite.objects.filter(
            program=program,
            email=users["participant"].email,
        ).first()
        if invite is None:
            invite = PartnerProgramInvite.objects.create(
                program=program,
                email=users["participant"].email,
                status=PartnerProgramInvite.STATUS_PENDING,
                created_by=users["organizer"],
                expires_at=timezone.now() + timedelta(days=30),
            )
        else:
            invite.status = PartnerProgramInvite.STATUS_PENDING
            invite.created_by = users["organizer"]
            invite.expires_at = timezone.now() + timedelta(days=30)
            invite.save()
        return invite

    def _ensure_project_submission(self, *, program, users, company, industry):
        project = self._upsert_first(
            Project,
            {"name": "Demo Smart Campus Assistant", "leader": users["participant"]},
            {
                "description": (
                    "Проект команды участника для демо кейс-чемпионата: сервис "
                    "помогает студентам находить аудитории, события, дедлайны и "
                    "партнерские возможности на кампусе."
                ),
                "region": "Москва",
                "actuality": "Кампусные сервисы разрознены, студентам сложно быстро находить нужные действия.",
                "target_audience": "Студенты, наставники и организаторы образовательных программ.",
                "trl": 5,
                "implementation_deadline": date.today() + timedelta(days=120),
                "problem": "Нет единой точки доступа к событиям, дедлайнам и сервисам кампуса.",
                "industry": industry,
                "presentation_address": self._program_file_url(program),
                "image_address": "https://picsum.photos/seed/demo-project-avatar/640/640",
                "cover_image_address": "https://picsum.photos/seed/demo-project-cover/1280/480",
                "draft": False,
                "is_company": False,
                "is_public": True,
            },
        )
        self._upsert_first(
            ProjectCompany,
            {"project": project, "company": company},
            {
                "contribution": "Компания предоставляет кейс, экспертов и обратную связь.",
                "decision_maker": users["organizer"],
            },
        )
        self._upsert_first(
            ProjectLink,
            {"project": project, "link": "https://procollab.pro"},
            {},
        )

        for user in (users["participant"], users["teammate"]):
            self._ensure_program_profile(program, user, project)
        self._ensure_participant_consent(program, users["participant"])

        self._upsert_first(
            Collaborator,
            {"project": project, "user": users["teammate"]},
            {
                "role": "Frontend и UX",
                "specialization": "UX/UI-дизайн и Angular",
            },
        )

        program_project = PartnerProgramProject.objects.filter(
            partner_program=program,
            project=project,
        ).first()
        if program_project is None:
            program_project = PartnerProgramProject.objects.create(
                partner_program=program,
                project=project,
                submitted=False,
                datetime_submitted=None,
            )

        if program_project.submitted:
            program_project.submitted = False
            program_project.datetime_submitted = None
            program_project.save(update_fields=["submitted", "datetime_submitted"])

        field_values = {
            "track": "AI-сервисы",
            "team_role": "MVP",
            "motivation": (
                "Команда хочет проверить, как автономные чемпионаты помогают "
                "быстро собирать проекты вокруг реальных кейсов."
            ),
        }
        for field in program.fields.all():
            if field.name in field_values:
                self._upsert_first(
                    PartnerProgramFieldValue,
                    {"program_project": program_project, "field": field},
                    {"value_text": field_values[field.name]},
                )

        program_project.submitted = True
        program_project.datetime_submitted = timezone.now() - timedelta(days=1)
        program_project.save(update_fields=["submitted", "datetime_submitted"])

        self._ensure_project_evaluation(program, program_project, users)
        return program_project

    def _ensure_project_cohort(self, *, programs, users, companies, industry):
        candidate_programs = [
            program
            for program in programs.values()
            if program.status
            in (PartnerProgram.STATUS_PUBLISHED, PartnerProgram.STATUS_COMPLETED)
        ]
        participants = users["participant_pool"]
        experts = users["expert_pool"]
        company_values = list(companies.values())

        for index in range(1, DEMO_PROJECT_COUNT + 1):
            program = candidate_programs[(index - 1) % len(candidate_programs)]
            leader = participants[(index - 1) % len(participants)]
            teammate = participants[(index + 5) % len(participants)]
            company = company_values[(index - 1) % len(company_values)]
            project = self._upsert_first(
                Project,
                {"name": f"Demo Case Project {index:03d}", "leader": leader},
                {
                    "description": (
                        "Расширенный демо-проект для наполнения Selectel pre-prod "
                        "данными кейс-чемпионатов и проверки списков, карточек, "
                        "оценок, уведомлений и кабинетов разных ролей."
                    ),
                    "region": "Москва",
                    "actuality": (
                        "Проект демонстрирует, как участники проходят полный "
                        "цикл от регистрации до экспертной оценки."
                    ),
                    "target_audience": "Студенты, эксперты и организаторы программ.",
                    "trl": (index % 8) + 1,
                    "implementation_deadline": date.today()
                    + timedelta(days=90 + index),
                    "problem": "Нужно показать богатую базу данных для дипломной демонстрации.",
                    "industry": industry,
                    "presentation_address": self._program_file_url(program),
                    "image_address": (
                        f"https://picsum.photos/seed/demo-case-{index:03d}/640/640"
                    ),
                    "cover_image_address": (
                        f"https://picsum.photos/seed/demo-case-cover-{index:03d}/1280/480"
                    ),
                    "draft": False,
                    "is_company": False,
                    "is_public": True,
                },
            )
            self._upsert_first(
                ProjectCompany,
                {"project": project, "company": company},
                {
                    "contribution": "Демо-партнерство для проверки карточки проекта.",
                    "decision_maker": users["organizer"],
                },
            )
            self._upsert_first(
                ProjectLink,
                {"project": project, "link": f"https://procollab.pro/demo/{index:03d}"},
                {},
            )

            self._ensure_program_profile(program, leader, project)
            self._ensure_participant_consent(program, leader)
            if (
                program.participation_format
                == PartnerProgram.PARTICIPATION_FORMAT_TEAM
            ):
                self._ensure_program_profile(program, teammate, project)
                self._ensure_participant_consent(program, teammate)
                self._upsert_first(
                    Collaborator,
                    {"project": project, "user": teammate},
                    {
                        "role": "Demo teammate",
                        "specialization": "Product and frontend",
                    },
                )

            program_project = PartnerProgramProject.objects.filter(
                partner_program=program,
                project=project,
            ).first()
            if program_project is None:
                program_project = PartnerProgramProject.objects.create(
                    partner_program=program,
                    project=project,
                    submitted=False,
                    datetime_submitted=None,
                )
            if program_project.submitted:
                program_project.submitted = False
                program_project.datetime_submitted = None
                program_project.save(update_fields=["submitted", "datetime_submitted"])

            for field in program.fields.all():
                value = {
                    "track": "AI-сервисы" if index % 2 else "Образование",
                    "team_role": "MVP" if index % 3 else "Пилотирование",
                    "motivation": (
                        "Демо-команда участвует, чтобы проверить полный "
                        "процесс кейс-чемпионата на pre-prod стенде."
                    ),
                }.get(field.name)
                if value is not None:
                    self._upsert_first(
                        PartnerProgramFieldValue,
                        {"program_project": program_project, "field": field},
                        {"value_text": value},
                    )

            program_project.submitted = True
            program_project.datetime_submitted = timezone.now() - timedelta(
                days=index % 10
            )
            program_project.save(update_fields=["submitted", "datetime_submitted"])

            expert_user = experts[(index - 1) % len(experts)]
            self._ensure_project_evaluation(
                program,
                program_project,
                users,
                expert_user=expert_user,
            )

    def _program_file_url(self, program):
        material = (
            program.materials.filter(file__isnull=False).select_related("file").first()
        )
        return material.file.link if material and material.file else "https://procollab.pro"

    def _ensure_participant_consent(self, program, participant):
        consent = PartnerProgramParticipantConsent.objects.filter(
            program=program,
            user=participant,
            participation_terms_version=DEMO_VERSION,
        ).first()
        defaults = {
            "consent_document_version": DEMO_VERSION,
            "privacy_policy_version": DEMO_VERSION,
            "consent_text_snapshot": (
                "Демо-согласие участника на обработку персональных данных и "
                "участие в кейс-чемпионате для Selectel pre-prod стенда."
            ),
            "ip_address": "127.0.0.1",
            "user_agent": "seed_demo_data",
        }
        if consent is None:
            return PartnerProgramParticipantConsent.objects.create(
                program=program,
                user=participant,
                participation_terms_version=DEMO_VERSION,
                **defaults,
            )
        for field, value in defaults.items():
            setattr(consent, field, value)
        consent.save()
        return consent

    def _ensure_program_profile(self, program, user, project=None):
        return self._upsert_first(
            PartnerProgramUserProfile,
            {"partner_program": program, "user": user},
            {
                "project": project,
                "partner_program_data": {
                    "track": "AI-сервисы",
                    "team_role": "MVP",
                    "motivation": "Демо-регистрация для Selectel pre-prod стенда.",
                },
            },
        )

    def _ensure_project_evaluation(self, program, program_project, users, expert_user=None):
        expert_user = expert_user or users["expert"]
        expert_profile = expert_user.expert
        expert_profile.programs.add(program)
        self._upsert_first(
            ProjectExpertAssignment,
            {
                "partner_program": program,
                "project": program_project.project,
                "expert": expert_profile,
            },
            {},
        )

        evaluation, _ = ProjectEvaluation.objects.update_or_create(
            program_project=program_project,
            user=expert_user,
            defaults={
                "status": ProjectEvaluation.STATUS_DRAFT,
                "comment": (
                    "Демо-оценка: у решения понятная проблема, хороший MVP и "
                    "реалистичный план пилотирования."
                ),
            },
        )
        score_values = {
            "Проблема и рынок": "8",
            "Технологичность": "9",
            "Пользовательский опыт": "8",
            "Презентация": "9",
        }
        for criterion in Criteria.objects.filter(partner_program=program):
            value = score_values.get(criterion.name, "8")
            self._upsert_first(
                ProjectEvaluationScore,
                {"evaluation": evaluation, "criterion": criterion},
                {"value": value},
            )
            self._upsert_first(
                ProjectScore,
                {
                    "criteria": criterion,
                    "user": expert_user,
                    "project": program_project.project,
                },
                {"value": value},
            )
        evaluation.total_score = evaluation.calculate_total_score(require_complete=True)
        evaluation.mark_submitted()
        evaluation.save(update_fields=["status", "submitted_at", "total_score", "comment"])
        return evaluation

    def _ensure_notifications(self, programs, users):
        self._ensure_notification(
            recipient=users["organizer"],
            notification_type=Notification.Type.PROGRAM_MODERATION_APPROVED,
            title="Демо-чемпионат опубликован",
            message="PROCOLLAB Smart Campus Challenge доступен на витрине.",
            object_type="partner_program",
            object_id=programs["demo-published-smart-campus"].id,
            url="/office/program",
            dedupe_key="demo-published-smart-campus-approved",
        )
        self._ensure_notification(
            recipient=users["participant"],
            notification_type=Notification.Type.PROGRAM_SUBMITTED_TO_MODERATION,
            title="Проект принят на проверку",
            message="Demo Smart Campus Assistant отправлен экспертам.",
            object_type="partner_program_project",
            object_id=programs["demo-published-smart-campus"].id,
            url="/office/program",
            dedupe_key="demo-project-submitted",
        )
        self._ensure_notification(
            recipient=users["expert"],
            notification_type=Notification.Type.EXPERT_PROJECTS_ASSIGNED,
            title="Назначен проект на оценку",
            message="Проверьте демо-проект участника в Smart Campus Challenge.",
            object_type="partner_program",
            object_id=programs["demo-published-smart-campus"].id,
            url="/office/program",
            dedupe_key="demo-expert-assignment",
        )

    def _ensure_bulk_notifications(self, programs, users):
        published_program = programs["demo-published-smart-campus"]
        for index, participant in enumerate(users["participant_pool"], start=1):
            self._ensure_notification(
                recipient=participant,
                notification_type=Notification.Type.PROGRAM_MODERATION_APPROVED,
                title=f"Демо-чемпионат #{index:03d} доступен",
                message=(
                    "На стенде доступен опубликованный кейс-чемпионат с "
                    "регистрацией, проектами и экспертной оценкой."
                ),
                object_type="partner_program",
                object_id=published_program.id,
                url="/office/program",
                dedupe_key=f"demo-participant-feed-{index:03d}",
            )

        for index, expert in enumerate(users["expert_pool"], start=1):
            self._ensure_notification(
                recipient=expert,
                notification_type=Notification.Type.EXPERT_PROJECTS_ASSIGNED,
                title=f"Демо-назначение эксперта #{index:03d}",
                message="Проверьте назначенные демо-проекты в кабинете эксперта.",
                object_type="partner_program",
                object_id=published_program.id,
                url="/office/program",
                dedupe_key=f"demo-expert-feed-{index:03d}",
            )

        for index, organizer in enumerate(users["organizer_pool"], start=1):
            self._ensure_notification(
                recipient=organizer,
                notification_type=Notification.Type.COMPANY_VERIFICATION_SUBMITTED,
                title=f"Демо-статус компании #{index:03d}",
                message=(
                    "В демо-данных есть организаторы с подтвержденной, "
                    "ожидающей и отклоненной компанией."
                ),
                object_type="partner_program",
                object_id=published_program.id,
                url="/office/program",
                dedupe_key=f"demo-organizer-feed-{index:03d}",
            )

    def _count_demo_records(self):
        demo_project_filter = {
            "name__in": [
                "Demo Smart Campus Assistant",
                *[
                    f"Demo Case Project {index:03d}"
                    for index in range(1, DEMO_PROJECT_COUNT + 1)
                ],
            ]
        }
        demo_company_inns = ["7707083893", "7802870820", "7714783093", "5406567890"]
        return sum(
            (
                SkillCategory.objects.filter(name__in=SKILLS_BY_CATEGORY.keys()).count(),
                Skill.objects.filter(
                    category__name__in=SKILLS_BY_CATEGORY.keys()
                ).count(),
                SpecializationCategory.objects.filter(
                    name__in=SPECIALIZATIONS_BY_CATEGORY.keys()
                ).count(),
                Specialization.objects.filter(
                    category__name__in=SPECIALIZATIONS_BY_CATEGORY.keys()
                ).count(),
                Industry.objects.filter(
                    name="Цифровые продукты и городские сервисы"
                ).count(),
                User.objects.filter(email__endswith=f"@{DEMO_EMAIL_DOMAIN}").count(),
                UserNotificationPreferences.objects.filter(
                    user__email__endswith=f"@{DEMO_EMAIL_DOMAIN}"
                ).count(),
                Member.objects.filter(
                    user__email__endswith=f"@{DEMO_EMAIL_DOMAIN}"
                ).count(),
                Expert.objects.filter(
                    user__email__endswith=f"@{DEMO_EMAIL_DOMAIN}"
                ).count(),
                Company.objects.filter(inn__in=demo_company_inns).count(),
                UserFile.objects.filter(
                    name="selectel-demo-championship-rules"
                ).count(),
                PartnerProgram.objects.filter(tag__startswith="demo-").count(),
                PartnerProgramField.objects.filter(
                    partner_program__tag__startswith="demo-"
                ).count(),
                PartnerProgramMaterial.objects.filter(
                    program__tag__startswith="demo-"
                ).count(),
                Criteria.objects.filter(partner_program__tag__startswith="demo-").count(),
                LegalDocument.objects.filter(version=DEMO_VERSION).count(),
                PartnerProgramLegalSettings.objects.filter(
                    program__tag__startswith="demo-"
                ).count(),
                PartnerProgramVerificationRequest.objects.filter(
                    program__tag__startswith="demo-"
                ).count(),
                ModerationLog.objects.filter(program__tag__startswith="demo-").count(),
                PartnerProgramInvite.objects.filter(
                    program__tag__startswith="demo-"
                ).count(),
                PartnerProgramParticipantConsent.objects.filter(
                    program__tag__startswith="demo-"
                ).count(),
                Project.objects.filter(**demo_project_filter).count(),
                ProjectCompany.objects.filter(
                    project__name__in=demo_project_filter["name__in"]
                ).count(),
                ProjectLink.objects.filter(
                    project__name__in=demo_project_filter["name__in"]
                ).count(),
                Collaborator.objects.filter(
                    project__name__in=demo_project_filter["name__in"]
                ).count(),
                PartnerProgramUserProfile.objects.filter(
                    partner_program__tag__startswith="demo-"
                ).count(),
                PartnerProgramProject.objects.filter(
                    partner_program__tag__startswith="demo-"
                ).count(),
                PartnerProgramFieldValue.objects.filter(
                    program_project__partner_program__tag__startswith="demo-"
                ).count(),
                ProjectExpertAssignment.objects.filter(
                    partner_program__tag__startswith="demo-"
                ).count(),
                ProjectEvaluation.objects.filter(
                    program_project__partner_program__tag__startswith="demo-"
                ).count(),
                ProjectEvaluationScore.objects.filter(
                    evaluation__program_project__partner_program__tag__startswith="demo-"
                ).count(),
                ProjectScore.objects.filter(
                    criteria__partner_program__tag__startswith="demo-"
                ).count(),
                Notification.objects.filter(dedupe_key__startswith="demo-").count(),
                NotificationDelivery.objects.filter(
                    notification__dedupe_key__startswith="demo-"
                ).count(),
            )
        )

    def _ensure_notification(
        self,
        *,
        recipient,
        notification_type,
        title,
        message,
        object_type,
        object_id,
        url,
        dedupe_key,
    ):
        notification, _ = Notification.objects.update_or_create(
            recipient=recipient,
            type=notification_type,
            dedupe_key=dedupe_key,
            defaults={
                "title": title,
                "message": message,
                "object_type": object_type,
                "object_id": object_id,
                "url": url,
                "is_read": False,
            },
        )
        NotificationDelivery.objects.update_or_create(
            notification=notification,
            channel=NotificationDelivery.Channel.IN_APP,
            defaults={"status": NotificationDelivery.Status.SENT, "sent_at": timezone.now()},
        )
        return notification

    def _upsert_first(self, model, lookup, defaults):
        obj = model.objects.filter(**lookup).first()
        if obj is None:
            return model.objects.create(**lookup, **defaults)

        changed_fields = []
        for field, value in defaults.items():
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed_fields.append(field)

        if changed_fields:
            model_fields = {field.name for field in obj._meta.fields}
            update_fields = [field for field in changed_fields if field in model_fields]
            if "datetime_updated" in model_fields and "datetime_updated" not in update_fields:
                update_fields.append("datetime_updated")
            if "updated_at" in model_fields and "updated_at" not in update_fields:
                update_fields.append("updated_at")
            obj.save(update_fields=update_fields or None)
        return obj
