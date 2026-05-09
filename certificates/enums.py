FONT_ROBOTO = "roboto"
FONT_OPEN_SANS = "open_sans"
FONT_PT_SANS = "pt_sans"
FONT_MONTSERRAT = "montserrat"
FONT_MANROPE = "manrope"
FONT_INTER = "inter"

FONT_CHOICES = [
    (FONT_ROBOTO, "Roboto"),
    (FONT_OPEN_SANS, "Open Sans"),
    (FONT_PT_SANS, "PT Sans"),
    (FONT_MONTSERRAT, "Montserrat"),
    (FONT_MANROPE, "Manrope"),
    (FONT_INTER, "Inter"),
]

FONT_CSS_FAMILIES = {
    FONT_ROBOTO: "Roboto, Arial, sans-serif",
    FONT_OPEN_SANS: "'Open Sans', Arial, sans-serif",
    FONT_PT_SANS: "'PT Sans', Arial, sans-serif",
    FONT_MONTSERRAT: "Montserrat, Arial, sans-serif",
    FONT_MANROPE: "Manrope, Arial, sans-serif",
    FONT_INTER: "Inter, Arial, sans-serif",
}

ISSUE_CONDITION_ALL_REGISTERED = "all_registered"
ISSUE_CONDITION_SUBMITTED_PROJECT = "submitted_project"
ISSUE_CONDITION_SCORE_THRESHOLD = "score_threshold"
ISSUE_CONDITION_TOP_POSITIONS = "top_positions"

ISSUE_CONDITION_CHOICES = [
    (ISSUE_CONDITION_ALL_REGISTERED, "All registered participants"),
    (ISSUE_CONDITION_SUBMITTED_PROJECT, "Participants with submitted projects"),
    (ISSUE_CONDITION_SCORE_THRESHOLD, "Participants with score above threshold"),
    (ISSUE_CONDITION_TOP_POSITIONS, "Prize positions"),
]

RELEASE_MODE_AFTER_PROGRAM_END = "after_program_end"
RELEASE_MODE_MANUAL = "manual"

RELEASE_MODE_CHOICES = [
    (RELEASE_MODE_AFTER_PROGRAM_END, "After program end"),
    (RELEASE_MODE_MANUAL, "Manual"),
]

CERTIFICATE_TYPE_PARTICIPATION = "participation"

CERTIFICATE_TYPE_CHOICES = [
    (CERTIFICATE_TYPE_PARTICIPATION, "Participation certificate"),
]

FIELD_PARTICIPANT_FULL_NAME = "participant_full_name"
FIELD_PROGRAM_TITLE = "program_title"
FIELD_COMPLETION_DATE = "completion_date"
FIELD_ORGANIZER_NAME = "organizer_name"
FIELD_CERTIFICATE_ID = "certificate_id"
FIELD_PROJECT_TITLE = "project_title"
FIELD_TEAM_MEMBERS = "team_members"
FIELD_RANK = "rank"
FIELD_SIGNER_NAME = "signer_name"

CERTIFICATE_FIELD_KEYS = [
    FIELD_PARTICIPANT_FULL_NAME,
    FIELD_PROGRAM_TITLE,
    FIELD_COMPLETION_DATE,
    FIELD_ORGANIZER_NAME,
    FIELD_CERTIFICATE_ID,
    FIELD_PROJECT_TITLE,
    FIELD_TEAM_MEMBERS,
    FIELD_RANK,
    FIELD_SIGNER_NAME,
]

LEGACY_FIELD_KEY_MAP = {
    "participant_name": FIELD_PARTICIPANT_FULL_NAME,
    "program_name": FIELD_PROGRAM_TITLE,
    "finish_date": FIELD_COMPLETION_DATE,
    "organization_name": FIELD_ORGANIZER_NAME,
    "team_name": FIELD_TEAM_MEMBERS,
    "rating_position": FIELD_RANK,
}


def get_default_fields_positioning():
    return {
        FIELD_PARTICIPANT_FULL_NAME: {
            "x": 0.5,
            "y": 0.43,
            "font_size": 36,
            "align": "center",
            "visible": True,
            "color": None,
        },
        FIELD_PROGRAM_TITLE: {
            "x": 0.5,
            "y": 0.55,
            "font_size": 24,
            "align": "center",
            "visible": True,
            "color": None,
        },
        FIELD_COMPLETION_DATE: {
            "x": 0.22,
            "y": 0.79,
            "font_size": 14,
            "align": "left",
            "visible": True,
            "color": None,
        },
        FIELD_ORGANIZER_NAME: {
            "x": 0.24,
            "y": 0.82,
            "font_size": 14,
            "align": "center",
            "visible": False,
            "color": None,
        },
        FIELD_CERTIFICATE_ID: {
            "x": 0.22,
            "y": 0.88,
            "font_size": 12,
            "align": "left",
            "visible": True,
            "color": None,
        },
        FIELD_PROJECT_TITLE: {
            "x": 0.5,
            "y": 0.64,
            "font_size": 14,
            "align": "center",
            "visible": True,
            "color": None,
        },
        FIELD_TEAM_MEMBERS: {
            "x": 0.5,
            "y": 0.56,
            "font_size": 14,
            "align": "center",
            "visible": False,
            "color": None,
        },
        FIELD_RANK: {
            "x": 0.5,
            "y": 0.60,
            "font_size": 18,
            "align": "center",
            "visible": False,
            "color": None,
        },
        FIELD_SIGNER_NAME: {
            "x": 0.60,
            "y": 0.88,
            "font_size": 15,
            "align": "left",
            "visible": True,
            "color": None,
        },
    }


def get_font_options():
    return [{"id": font_id, "label": label} for font_id, label in FONT_CHOICES]
