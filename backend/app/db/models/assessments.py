from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.db.models import Base, TimestampMixin


class Class(TimestampMixin, Base):
    __tablename__ = "classes"

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    grade = Column(Integer, nullable=False)
    section = Column(String, nullable=True)
    academic_year = Column(String, nullable=False)
    class_teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)

    school = relationship("School", back_populates="classes")
    class_teacher = relationship("Teacher", back_populates="classes_teaching", foreign_keys=[class_teacher_id])
    students = relationship("Student", back_populates="class_obj", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="class_obj")


class Student(TimestampMixin, Base):
    __tablename__ = "students"

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False)
    roll_number = Column(String, nullable=False)
    gr_number = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    school = relationship("School", back_populates="students")
    class_obj = relationship("Class", back_populates="students")
    omr_sheets = relationship("OMRSheet", back_populates="student")
    student_results = relationship("StudentResult", back_populates="student")

    @property
    def school_name(self) -> str:
        return self.school.name if self.school else ""

    @property
    def class_name(self) -> str:
        if self.class_obj:
            return f"Grade {self.class_obj.grade}{' ' + self.class_obj.section if self.class_obj.section else ''}"
        return ""


class Assessment(TimestampMixin, Base):
    __tablename__ = "assessments"

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    blueprint_id = Column(Integer, ForeignKey("blueprints.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    scheduled_date = Column(Date, nullable=True)
    status = Column(String, default="scheduled")

    school = relationship("School", back_populates="assessments")
    blueprint = relationship("Blueprint", back_populates="assessments")
    class_obj = relationship("Class", back_populates="assessments")
    omr_sheets = relationship("OMRSheet", back_populates="assessment")
    student_results = relationship("StudentResult", back_populates="assessment", cascade="all, delete-orphan")


class StudentResult(TimestampMixin, Base):
    __tablename__ = "student_results"

    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    omr_result_id = Column(Integer, ForeignKey("omr_results.id"), nullable=True)
    total_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)

    assessment = relationship("Assessment", back_populates="student_results")
    student = relationship("Student", back_populates="student_results")
    omr_result = relationship("OMRResult", back_populates="student_results")
    competency_results = relationship("CompetencyResult", back_populates="student_result", cascade="all, delete-orphan")


class CompetencyResult(TimestampMixin, Base):
    __tablename__ = "competency_results"

    student_result_id = Column(Integer, ForeignKey("student_results.id"), nullable=False, index=True)
    competency_id = Column(Integer, ForeignKey("competencies.id"), nullable=False)
    questions_attempted = Column(Integer, nullable=True)
    questions_correct = Column(Integer, nullable=True)
    mastery_level = Column(String, nullable=True)

    student_result = relationship("StudentResult", back_populates="competency_results")
    competency = relationship("Competency", back_populates="competency_results")
