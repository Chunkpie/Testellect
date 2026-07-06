import json
import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.core.constants import UserRole, Difficulty, BloomLevel, ApprovalStatus, QuestionType, BookProcessingStatus
from app.models.models import (
    User, School, District, Student, Class, Subject, Book, Chapter, Topic, Concept,
    Competency, QuestionBank, QuestionOption, Blueprint, Paper, PaperQuestion,
    Assessment, StudentResult, CompetencyResult, OMRSheet, OMRResult,
    Report, AnalyticsCache, Teacher,
)


async def seed_demo_data():
    async with async_session_factory() as db:
        result = await db.execute(select(func.count()).select_from(User))
        count = result.scalar()
        if count and count > 0:
            return

        district = District(name="Gandhinagar")
        db.add(district)
        await db.flush()

        school = School(name="Model High School", district_id=district.id, udise_code="GJ240001", medium="English", board="GSEB")
        db.add(school)
        await db.flush()
        school_id = school.id

        school2 = School(name="Adarsh Vidyalaya", district_id=district.id, udise_code="GJ240002", medium="Gujarati", board="GSEB")
        db.add(school2)
        await db.flush()
        school2_id = school2.id

        users_data = [
            User(full_name="Admin User", email="admin@gseb.org", password_hash=hash_password("Admin@123"), role=UserRole.ADMINISTRATOR),
            User(full_name="Rahul Sharma", email="r.sharma@gseb.org", password_hash=hash_password("Teacher@123"), role=UserRole.TEACHER, school_id=school_id),
            User(full_name="Anita Patel", email="a.patel@gseb.org", password_hash=hash_password("Principal@123"), role=UserRole.PRINCIPAL, school_id=school_id),
            User(full_name="Vikram Singh", email="v.singh@gseb.org", password_hash=hash_password("Deo@123"), role=UserRole.DEO, district_id=district.id),
        ]
        for u in users_data:
            db.add(u)
        await db.flush()

        subject_science = Subject(name_en="Science", code="SCI10", grade=10)
        subject_math = Subject(name_en="Mathematics", code="MATH10", grade=10)
        subject_evs = Subject(name_en="Environmental Studies", code="EVS5", grade=5)
        subject_eng = Subject(name_en="English", code="ENG", grade=10)
        subject_guj = Subject(name_en="Gujarati", code="GUJ", grade=10)
        subject_hin = Subject(name_en="Hindi", code="HIN", grade=10)
        subject_sst = Subject(name_en="Social Science", code="SST", grade=10)
        subject_cs = Subject(name_en="Computer Science", code="CS", grade=10)
        subject_san = Subject(name_en="Sanskrit", code="SAN", grade=10)

        db.add_all([
            subject_science, subject_math, subject_evs, 
            subject_eng, subject_guj, subject_hin, 
            subject_sst, subject_cs, subject_san
        ])
        await db.flush()

        class_ids_school1 = []
        for grade_num in range(6, 8):
            cls1 = Class(school_id=school_id, grade=grade_num, section="A", academic_year="2026-27")
            db.add(cls1)
            await db.flush()
            class_ids_school1.append(cls1.id)
            
        class_ids_school2 = []
        for grade_num in range(6, 8):
            cls2 = Class(school_id=school2_id, grade=grade_num, section="A", academic_year="2026-27")
            db.add(cls2)
            await db.flush()
            class_ids_school2.append(cls2.id)

        all_class_ids = class_ids_school1 + class_ids_school2

        student_ids = []
        for i in range(1, 101):
            s_school_id = school_id if i <= 50 else school2_id
            s_class_id = all_class_ids[0] if i <= 25 else all_class_ids[1] if i <= 50 else all_class_ids[2] if i <= 75 else all_class_ids[3]
            s = Student(
                full_name=f"Student {i}",
                roll_number=f"ROLL{i:04d}",
                school_id=s_school_id,
                class_id=s_class_id,
                gender=random.choice(["M", "F", "O"]),
            )
            db.add(s)
            await db.flush()
            student_ids.append(s.id)

        book_math = Book(
            school_id=school_id,
            subject_id=subject_math.id,
            grade=10,
            title="Mathematics Textbook Grade 10",
            file_path="/data/storage/books/math10.pdf",
            source_type="textbook",
            processing_status=BookProcessingStatus.READY,
            uploaded_by=users_data[0].id,
        )
        db.add(book_math)
        await db.flush()

        book_science = Book(
            school_id=school_id,
            subject_id=subject_science.id,
            grade=10,
            title="Science Textbook Grade 10",
            file_path="/data/storage/books/science10.pdf",
            source_type="textbook",
            processing_status=BookProcessingStatus.READY,
            uploaded_by=users_data[0].id,
        )
        db.add(book_science)
        await db.flush()

        chapter = Chapter(
            book_id=book_math.id,
            title_en="Polynomials",
            unit_name="Algebra",
            sequence=1,
        )
        db.add(chapter)
        await db.flush()

        chapter2 = Chapter(
            book_id=book_science.id,
            title_en="Chemical Reactions and Equations",
            unit_name="Chemistry",
            sequence=2,
        )
        db.add(chapter2)
        await db.flush()

        topic = Topic(chapter_id=chapter2.id, sequence=1, title_en="Types of Chemical Reactions")
        db.add(topic)
        await db.flush()

        concepts_data = [
            Concept(topic_id=topic.id, name_en="Combination Reaction", description="Two or more substances combine to form a single product"),
            Concept(topic_id=topic.id, name_en="Decomposition Reaction", description="A compound breaks down into simpler substances"),
            Concept(topic_id=topic.id, name_en="Displacement Reaction", description="More reactive element displaces a less reactive one"),
            Concept(topic_id=topic.id, name_en="Oxidation and Reduction", description="Loss and gain of electrons in chemical reactions"),
        ]
        for c in concepts_data:
            db.add(c)
        await db.flush()

        competencies = [
            Competency(name_en="Scientific Inquiry", nas_parakh_code="SCI.INQ.1", description="Ability to conduct scientific investigations"),
            Competency(name_en="Data Analysis", nas_parakh_code="SCI.DA.1", description="Ability to analyze experimental data"),
            Competency(name_en="Conceptual Understanding", nas_parakh_code="SCI.CU.1", description="Understanding of core scientific concepts"),
            Competency(name_en="Numerical Problem Solving", nas_parakh_code="MATH.NPS.1", description="Solve numerical problems using mathematical concepts"),
        ]
        for c in competencies:
            db.add(c)
        await db.flush()

        question_templates = [
            {"text": "What is the product of a combination reaction between magnesium and oxygen?", "options": {"A": "MgO", "B": "MgO2", "C": "Mg2O", "D": "Mg2O3"}, "correct": "A", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "Which of the following is an example of a decomposition reaction?", "options": {"A": "2H2 + O2 -> 2H2O", "B": "2H2O -> 2H2 + O2", "C": "NaOH + HCl -> NaCl + H2O", "D": "AgNO3 + NaCl -> AgCl + NaNO3"}, "correct": "B", "difficulty": Difficulty.EASY, "concept": concepts_data[1]},
            {"text": "In the reaction Fe + CuSO4 -> FeSO4 + Cu, which element is displaced?", "options": {"A": "Iron displaces Copper", "B": "Copper displaces Iron", "C": "Sulfur displaces Oxygen", "D": "No displacement occurs"}, "correct": "A", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[2]},
            {"text": "What is the oxidation state of oxygen in H2O2?", "options": {"A": "-2", "B": "-1", "C": "0", "D": "+2"}, "correct": "B", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[3]},
            {"text": "A chemical reaction releases 250 kJ of energy. This is an example of:", "options": {"A": "Endothermic reaction", "B": "Exothermic reaction", "C": "Photochemical reaction", "D": "Catalytic reaction"}, "correct": "B", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "What happens to the rate of reaction when temperature is increased?", "options": {"A": "Decreases", "B": "Increases", "C": "Remains same", "D": "First increases then decreases"}, "correct": "B", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "Which of the following statements about catalysts is correct?", "options": {"A": "Catalysts are consumed in the reaction", "B": "Catalysts increase activation energy", "C": "Catalysts provide an alternative pathway with lower activation energy", "D": "Catalysts change the equilibrium constant"}, "correct": "C", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[1]},
            {"text": "Balance the equation: Fe + H2O -> Fe3O4 + H2. What is the coefficient of H2?", "options": {"A": "2", "B": "3", "C": "4", "D": "6"}, "correct": "C", "difficulty": Difficulty.HARD, "concept": concepts_data[1]},
            {"text": "Which type of reaction is represented by: AgNO3 + NaCl -> AgCl + NaNO3?", "options": {"A": "Combination", "B": "Decomposition", "C": "Double Displacement", "D": "Redox"}, "correct": "C", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[2]},
            {"text": "What is the Law of Conservation of Mass?", "options": {"A": "Mass can be created but not destroyed", "B": "Mass can be destroyed but not created", "C": "Mass is neither created nor destroyed in a chemical reaction", "D": "Mass is converted to energy in all reactions"}, "correct": "C", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "What is the value of x if 2x + 5 = 15?", "options": {"A": "3", "B": "5", "C": "7", "D": "10"}, "correct": "B", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "If a polynomial p(x) = x^2 - 5x + 6, what are its zeroes?", "options": {"A": "2, 3", "B": "-2, -3", "C": "1, 6", "D": "-1, -6"}, "correct": "A", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[0]},
            {"text": "What is the degree of the polynomial 3x^4 + 2x^2 - x + 7?", "options": {"A": "2", "B": "3", "C": "4", "D": "7"}, "correct": "C", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "If alpha and beta are zeroes of x^2 - 3x + 2, what is alpha + beta?", "options": {"A": "2", "B": "3", "C": "-3", "D": "-2"}, "correct": "B", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[0]},
            {"text": "What is the remainder when x^3 - 3x^2 + 2x - 1 is divided by (x - 1)?", "options": {"A": "-1", "B": "0", "C": "1", "D": "2"}, "correct": "A", "difficulty": Difficulty.HARD, "concept": concepts_data[0]},
            {"text": "Which of the following is a quadratic polynomial?", "options": {"A": "x + 1", "B": "x^2 + 2x + 1", "C": "x^3 + 1", "D": "x^4 + x^2"}, "correct": "B", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "The graph of a linear polynomial is a:", "options": {"A": "Straight line", "B": "Parabola", "C": "Circle", "D": "Hyperbola"}, "correct": "A", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
            {"text": "If p(x) = 2x^2 - 4x + 2, what is p(2)?", "options": {"A": "0", "B": "2", "C": "4", "D": "8"}, "correct": "B", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[0]},
            {"text": "What is the sum of zeroes of the polynomial x^2 - 5x + 6?", "options": {"A": "5", "B": "-5", "C": "6", "D": "-6"}, "correct": "A", "difficulty": Difficulty.MEDIUM, "concept": concepts_data[0]},
            {"text": "How many zeroes can a quadratic polynomial have at most?", "options": {"A": "0", "B": "1", "C": "2", "D": "3"}, "correct": "C", "difficulty": Difficulty.EASY, "concept": concepts_data[0]},
        ]

        question_objects = []
        for i, qt in enumerate(question_templates):
            q = QuestionBank(
                school_id=school_id,
                question_text_en=qt["text"],
                difficulty=qt["difficulty"],
                question_type=QuestionType.MCQ,
                bloom_level=BloomLevel.REMEMBER,
                marks=1.0,
                concept_id=qt["concept"].id,
                approval_status=ApprovalStatus.APPROVED,
                confidence_score=0.9,
            )
            db.add(q)
            await db.flush()
            question_objects.append(q)

            for opt_key, opt_text in qt["options"].items():
                option = QuestionOption(
                    question_id=q.id,
                    option_text_en=opt_text,
                    is_correct=(opt_key == qt["correct"]),
                    sequence=ord(opt_key) - ord("A"),
                )
                db.add(option)
        await db.flush()

        blueprint = Blueprint(
            school_id=school_id,
            name="Science Practice Test - Grade 10",
            grade=10,
            subject_id=subject_science.id,
            total_questions=10,
            total_marks=10,
            difficulty_distribution=json.dumps({"easy": 40, "medium": 40, "hard": 20}),
            bloom_distribution=json.dumps({"remember": 30, "understand": 30, "apply": 20, "analyze": 10, "evaluate": 10}),
            duration_minutes=60,
        )
        db.add(blueprint)
        await db.flush()

        for vi in range(2):
            paper = Paper(
                blueprint_id=blueprint.id,
                variant_label=chr(65 + vi),
            )
            db.add(paper)
            await db.flush()

            for qi, q in enumerate(question_objects[:10]):
                pq = PaperQuestion(
                    paper_id=paper.id,
                    question_id=q.id,
                    sequence=qi + 1,
                    option_order=json.dumps(["A", "B", "C", "D"]),
                )
                db.add(pq)
        await db.flush()

        class_obj = Class(school_id=school_id, grade=10, section="A", academic_year="2026-27")
        db.add(class_obj)
        await db.flush()

        assessment = Assessment(
            name="Science Mid-Term Examination 2026",
            blueprint_id=blueprint.id,
            school_id=school_id,
            class_id=class_obj.id,
            status="conducted",
        )
        db.add(assessment)
        await db.flush()

        for i in range(30):
            omr = OMRSheet(
                paper_id=paper.id,
                assessment_id=assessment.id,
                student_id=student_ids[i],
                status="scanned",
            )
            db.add(omr)
            await db.flush()

            result = OMRResult(
                omr_sheet_id=omr.id,
                raw_score=random.randint(5, 10),
                max_score=10,
                detected_answers=json.dumps({}),
            )
            db.add(result)

            sr = StudentResult(
                assessment_id=assessment.id,
                student_id=student_ids[i],
                omr_result_id=result.id,
                total_score=result.raw_score,
                max_score=10,
                percentage=(result.raw_score / 10) * 100,
            )
            db.add(sr)
        await db.flush()

        report = Report(
            school_id=school_id,
            report_type="school",
            reference_id=school_id,
        )
        db.add(report)

        cache = AnalyticsCache(
            cache_key="demo-seeded-hash",
            payload=json.dumps({
                "chapter_name": "Chemical Reactions",
                "concepts": [
                    {"name": "Combination Reaction", "bloom_level": "remember"},
                    {"name": "Decomposition Reaction", "bloom_level": "understand"},
                    {"name": "Displacement Reaction", "bloom_level": "apply"},
                ],
                "learning_outcomes": ["Understand types of chemical reactions", "Balance chemical equations"],
                "competencies": [{"name": "Scientific Inquiry", "code": "SCI.INQ.1", "description": "Scientific investigation skills"}],
                "misconceptions": ["All reactions are reversible", "Catalysts change product yield"],
            }),
        )
        db.add(cache)

        await db.commit()
