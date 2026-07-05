package com.dummy.school;

import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.PostConstruct;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * One thin controller per entity. All CRUD behaviour lives in
 * {@link AbstractCrudController}; here we only declare the route and seed data.
 */
@RestController
@RequestMapping("/students")
@Tag(name = "Students")
class StudentController extends AbstractCrudController<Student> {
    protected String entityName() { return "Student"; }

    @PostConstruct
    void init() {
        Student a = new Student(); a.setName("John Doe"); a.setAge(15); a.setGrade("10"); seed(a);
        Student b = new Student(); b.setName("Mary Lee"); b.setAge(16); b.setGrade("11"); seed(b);
    }
}

@RestController
@RequestMapping("/teachers")
@Tag(name = "Teachers")
class TeacherController extends AbstractCrudController<Teacher> {
    protected String entityName() { return "Teacher"; }

    @PostConstruct
    void init() {
        Teacher a = new Teacher(); a.setName("Susan Clark"); a.setSubject("Math"); a.setEmail("susan@school.edu"); seed(a);
        Teacher b = new Teacher(); b.setName("Tom Brown"); b.setSubject("History"); b.setEmail("tom@school.edu"); seed(b);
    }
}

@RestController
@RequestMapping("/courses")
@Tag(name = "Courses")
class CourseController extends AbstractCrudController<Course> {
    protected String entityName() { return "Course"; }

    @PostConstruct
    void init() {
        Course a = new Course(); a.setTitle("Algebra I"); a.setTeacherId(1L); a.setCredits(3); seed(a);
        Course b = new Course(); b.setTitle("World History"); b.setTeacherId(2L); b.setCredits(4); seed(b);
    }
}

@RestController
@RequestMapping("/classrooms")
@Tag(name = "Classrooms")
class ClassroomController extends AbstractCrudController<Classroom> {
    protected String entityName() { return "Classroom"; }

    @PostConstruct
    void init() {
        Classroom a = new Classroom(); a.setRoomNumber("101"); a.setBuilding("Main"); a.setCapacity(30); seed(a);
        Classroom b = new Classroom(); b.setRoomNumber("202"); b.setBuilding("Science"); b.setCapacity(25); seed(b);
    }
}

@RestController
@RequestMapping("/enrollments")
@Tag(name = "Enrollments")
class EnrollmentController extends AbstractCrudController<Enrollment> {
    protected String entityName() { return "Enrollment"; }

    @PostConstruct
    void init() {
        Enrollment a = new Enrollment(); a.setStudentId(1L); a.setCourseId(1L); a.setSemester("Fall 2026"); seed(a);
        Enrollment b = new Enrollment(); b.setStudentId(2L); b.setCourseId(2L); b.setSemester("Fall 2026"); seed(b);
    }
}
