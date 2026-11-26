from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class Register(Login):
    name: str = Field(min_length=2, max_length=100)
    accepted_terms: Literal[True]

    @field_validator("accepted_terms", mode="before")
    @classmethod
    def require_agreement(cls, value):
        if value is not True:
            raise ValueError("Для регистрации примите пользовательское соглашение")
        return value


class Profile(Input):
    name: str = Field(min_length=2, max_length=100)
    bio: str = Field(default="", max_length=3000)
    institute: str = Field(default="", max_length=100)
    skills: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value):
        if any(not s.strip() or len(s.strip()) > 40 for s in value):
            raise ValueError("Навык должен содержать от 1 до 40 символов")
        return list(dict.fromkeys(s.strip() for s in value))


class VacancyInput(Input):
    id: int | None = None
    title: str = Field(min_length=2, max_length=100)
    requirements: str = Field(min_length=3, max_length=2000)
    capacity: int = Field(ge=1, le=30)


class ProjectInput(Input):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=30, max_length=10000)
    category: Literal["IT", "Инженерия", "Наука", "Социальные проекты", "Дизайн"]
    format: Literal["Онлайн", "Очно", "Гибрид"]
    skills: list[str] = Field(default_factory=list, max_length=20)
    vacancies: list[VacancyInput] = Field(min_length=1, max_length=15)
    team_contact: str = Field(default="", max_length=500)
    _skills = field_validator("skills")(Profile.clean_skills.__func__)

    @field_validator("team_contact")
    @classmethod
    def valid_contact_text(cls, value):
        if "\x00" in value:
            raise ValueError("Контакты содержат недопустимый символ")
        return value


class ApplicationInput(Input):
    message: str = Field(min_length=10, max_length=2000)


class Decision(Input):
    status: Literal["accepted", "rejected"]


class Moderation(Input):
    status: Literal["published", "rejected"]
    note: str = Field(min_length=3, max_length=1000)


class UserOut(BaseModel):
    id: int
    name: str
    bio: str
    institute: str
    skills: list[str]
    role: str


class MeOut(UserOut):
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class VacancyOut(BaseModel):
    id: int
    title: str
    requirements: str
    capacity: int
    filled: int


class TeamMember(BaseModel):
    id: int
    name: str
    vacancy: str


class ProjectOut(BaseModel):
    id: int
    owner_id: int
    owner_name: str
    title: str
    description: str
    category: str
    format: str
    skills: list[str]
    status: str
    is_demo: bool
    moderation_note: str
    recruitment_open: bool
    team_contact: str
    vacancies: list[VacancyOut]
    team: list[TeamMember]


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    total: int
    page: int
    pages: int


class ApplicationOut(BaseModel):
    id: int
    vacancy_id: int
    user_id: int
    message: str
    status: str
    applicant: UserOut
    project_id: int
    project_title: str
    vacancy_title: str


class Stats(BaseModel):
    projects: int
    open_places: int
    participants: int


class Message(BaseModel):
    detail: str


class ValidationIssue(BaseModel):
    field: str
    message: str


class ErrorOut(BaseModel):
    detail: str
    errors: list[ValidationIssue] | None = None


class Recruitment(Input):
    open: bool


class ReportInput(Input):
    target_type: Literal["project", "user"]
    target_id: int = Field(gt=0)
    reason: Literal["spam", "abuse", "fraud", "other"]
    message: str = Field(default="", max_length=2000)


class ReportDecision(Input):
    action: Literal["dismiss", "warn", "hide", "block"]
    note: str = Field(min_length=3, max_length=1000)


class BlockInput(Input):
    blocked: bool
    note: str = Field(min_length=3, max_length=1000)


class ReportOut(BaseModel):
    id: int
    target_type: str
    target_id: int
    target_name: str
    reason: str
    message: str
    status: str
    resolution: str
    created_at: int
    resolved_at: int | None
