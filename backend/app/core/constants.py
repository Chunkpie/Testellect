from enum import StrEnum


class UserRole(StrEnum):
    ADMINISTRATOR = "administrator"
    TEACHER = "teacher"
    PRINCIPAL = "principal"
    DEO = "deo"


class ApprovalStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_EDIT = "needs_edit"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BloomLevel(StrEnum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class QuestionType(StrEnum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"


class MasteryLevel(StrEnum):
    WEAK = "weak"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    ADVANCED = "advanced"


class BookProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    EXTRACTING_TEXT = "extracting_text"
    BUILDING_CURRICULUM = "building_curriculum"
    EXTRACTING_CONCEPTS = "extracting_concepts"
    MAPPING_COMPETENCIES = "mapping_competencies"
    READY = "ready"
    FAILED = "failed"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
