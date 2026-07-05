package com.dummy.hospital;

import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.PostConstruct;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * One thin controller per entity. All CRUD behaviour lives in
 * {@link AbstractCrudController}; here we only declare the route and seed data.
 */
@RestController
@RequestMapping("/patients")
@Tag(name = "Patients")
class PatientController extends AbstractCrudController<Patient> {
    protected String entityName() { return "Patient"; }

    @PostConstruct
    void init() {
        Patient a = new Patient(); a.setName("Emma Wilson"); a.setAge(34); a.setBloodGroup("O+"); seed(a);
        Patient b = new Patient(); b.setName("Liam Davis"); b.setAge(45); b.setBloodGroup("A-"); seed(b);
    }
}

@RestController
@RequestMapping("/doctors")
@Tag(name = "Doctors")
class DoctorController extends AbstractCrudController<Doctor> {
    protected String entityName() { return "Doctor"; }

    @PostConstruct
    void init() {
        Doctor a = new Doctor(); a.setName("Dr. Grace Hall"); a.setSpecialization("Cardiology"); a.setDepartmentId(1L); seed(a);
        Doctor b = new Doctor(); b.setName("Dr. Henry King"); b.setSpecialization("Neurology"); b.setDepartmentId(2L); seed(b);
    }
}

@RestController
@RequestMapping("/departments")
@Tag(name = "Departments")
class DepartmentController extends AbstractCrudController<Department> {
    protected String entityName() { return "Department"; }

    @PostConstruct
    void init() {
        Department a = new Department(); a.setName("Cardiology"); a.setFloor("2"); seed(a);
        Department b = new Department(); b.setName("Neurology"); b.setFloor("3"); seed(b);
    }
}

@RestController
@RequestMapping("/appointments")
@Tag(name = "Appointments")
class AppointmentController extends AbstractCrudController<Appointment> {
    protected String entityName() { return "Appointment"; }

    @PostConstruct
    void init() {
        Appointment a = new Appointment(); a.setPatientId(1L); a.setDoctorId(1L); a.setDate("2026-06-20"); a.setReason("Checkup"); seed(a);
        Appointment b = new Appointment(); b.setPatientId(2L); b.setDoctorId(2L); b.setDate("2026-06-21"); b.setReason("Migraine"); seed(b);
    }
}

@RestController
@RequestMapping("/medications")
@Tag(name = "Medications")
class MedicationController extends AbstractCrudController<Medication> {
    protected String entityName() { return "Medication"; }

    @PostConstruct
    void init() {
        Medication a = new Medication(); a.setName("Aspirin"); a.setDosage("100mg"); a.setPrice(4.99); seed(a);
        Medication b = new Medication(); b.setName("Ibuprofen"); b.setDosage("200mg"); b.setPrice(6.49); seed(b);
    }
}
