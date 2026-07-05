package com.dummy.hospital;

/**
 * The five hospital entities. Simple POJOs implementing {@link Identifiable}
 * so the generic CRUD controller can assign ids.
 */
class Patient implements Identifiable {
    private Long id;
    private String name;
    private Integer age;
    private String bloodGroup;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public Integer getAge() { return age; }
    public void setAge(Integer age) { this.age = age; }
    public String getBloodGroup() { return bloodGroup; }
    public void setBloodGroup(String bloodGroup) { this.bloodGroup = bloodGroup; }
}

class Doctor implements Identifiable {
    private Long id;
    private String name;
    private String specialization;
    private Long departmentId;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getSpecialization() { return specialization; }
    public void setSpecialization(String specialization) { this.specialization = specialization; }
    public Long getDepartmentId() { return departmentId; }
    public void setDepartmentId(Long departmentId) { this.departmentId = departmentId; }
}

class Department implements Identifiable {
    private Long id;
    private String name;
    private String floor;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getFloor() { return floor; }
    public void setFloor(String floor) { this.floor = floor; }
}

class Appointment implements Identifiable {
    private Long id;
    private Long patientId;
    private Long doctorId;
    private String date;
    private String reason;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getPatientId() { return patientId; }
    public void setPatientId(Long patientId) { this.patientId = patientId; }
    public Long getDoctorId() { return doctorId; }
    public void setDoctorId(Long doctorId) { this.doctorId = doctorId; }
    public String getDate() { return date; }
    public void setDate(String date) { this.date = date; }
    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
}

class Medication implements Identifiable {
    private Long id;
    private String name;
    private String dosage;
    private Double price;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDosage() { return dosage; }
    public void setDosage(String dosage) { this.dosage = dosage; }
    public Double getPrice() { return price; }
    public void setPrice(Double price) { this.price = price; }
}
