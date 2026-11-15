   -- Make student_preference uniqueness per course, so a student
   -- enrolled in several courses can rank projects in each one.
   -- Applied to sprint3-test and production on 2026-11-15.
   BEGIN;

   ALTER TABLE public.student_preference
       DROP CONSTRAINT student_preference_student_project_key,
       DROP CONSTRAINT student_preference_student_rank_key,
       ADD CONSTRAINT student_preference_student_course_project_key
           UNIQUE (student, course, project),
       ADD CONSTRAINT student_preference_student_course_rank_key
           UNIQUE (student, course, rank);

   COMMIT;
