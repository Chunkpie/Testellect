
DO \$\$
DECLARE
    cls RECORD;
    i INT;
BEGIN
    FOR cls IN SELECT id, school_id FROM classes LOOP
        FOR i IN 1..10 LOOP
            INSERT INTO students (school_id, class_id, roll_number, first_name, last_name, is_active, is_deleted)
            VALUES (cls.school_id, cls.id, 'R' || cls.id || '-' || LPAD(i::text, 3, '0'), 'Student' || i, 'Class' || cls.id, true, false)
            ON CONFLICT (school_id, roll_number) DO NOTHING;
        END LOOP;
    END LOOP;
END \$\$;

