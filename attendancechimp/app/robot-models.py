# LLM: Anthropic Claude
#[Attached: HW3-Instructions.pdf]
#    (Step 5 of the attached instructions asks for a Django models.py covering
#    InstructorProfile, StudentProfile, Course, Enrollment, Lecture, and
#    QRCodeUpload, designed to be simple to use, support attendance analytics,
#    and be robust to cheating.)


import uuid
from datetime import timedelta
 
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
 
 
# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
# Rather than one "Users" table with a role column, each role gets its own
# profile table attached 1:1 to Django's built-in auth User. This keeps
# authentication (passwords, sessions, permissions) in Django's hands, lets
# each role carry only the fields that make sense for it, and lets foreign
# keys say exactly which role they expect (a Course's instructor can't
# accidentally point at a student).
 
 
class InstructorProfile(models.Model):
    """Instructor-specific data, linked one-to-one with an auth User."""
 
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )
    department = models.CharField(max_length=100, blank=True)
    office = models.CharField(max_length=100, blank=True)
 
    def __str__(self):
        return self.user.get_full_name() or self.user.username
 
 
class StudentProfile(models.Model):
    """Student-specific data, linked one-to-one with an auth User."""
 
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    student_id = models.CharField(max_length=20, unique=True)
    major = models.CharField(max_length=100, blank=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
 
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.student_id})"
 
    def attendance_rate(self, course):
        """Fraction of a course's past lectures this student validly attended."""
        lectures = course.lectures.filter(date__lte=timezone.localdate())
        total = lectures.count()
        if total == 0:
            return None
        attended = (
            QRCodeUpload.objects.filter(
                student=self, lecture__in=lectures, is_valid=True
            )
            .values("lecture")
            .distinct()
            .count()
        )
        return attended / total
 
 
# ---------------------------------------------------------------------------
# Courses and enrollment
# ---------------------------------------------------------------------------
 
 
class Course(models.Model):
    """A course offering in a given term, taught by exactly one instructor."""
 
    code = models.CharField(max_length=20)  # e.g. "DATA 13600"
    name = models.CharField(max_length=200)
    term = models.CharField(max_length=20)  # e.g. "Autumn 2026"
    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.PROTECT,  # don't silently delete courses with an instructor
        related_name="courses",
    )
    meeting_days = models.CharField(
        max_length=7, help_text="Day letters, e.g. 'MWF' or 'TR'."
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
 
    students = models.ManyToManyField(
        StudentProfile, through="Enrollment", related_name="courses"
    )
 
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["code", "term"], name="unique_course_per_term"),
        ]
 
    def __str__(self):
        return f"{self.code}: {self.name} ({self.term})"
 
    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("end_time must be after start_time.")
 
 
class Enrollment(models.Model):
    """Join table for the Student <-> Course many-to-many relationship."""
 
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # False = dropped
 
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"], name="unique_enrollment"
            ),
        ]
 
    def __str__(self):
        return f"{self.student} in {self.course}"
 
 
# ---------------------------------------------------------------------------
# Lectures and attendance
# ---------------------------------------------------------------------------
 
 
def default_qr_expiry():
    return timezone.now() + timedelta(minutes=15)
 
 
class Lecture(models.Model):
    """
    One meeting of a course. Each lecture has an unguessable QR identifier
    (a UUID) and a short validity window, so a photo of the code shared
    after class -- or a code from a different day -- is rejected.
    """
 
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lectures")
    date = models.DateField()
    qr_identifier = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_valid_from = models.DateTimeField(default=timezone.now)
    qr_valid_until = models.DateTimeField(default=default_qr_expiry)
 
    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["course", "date"], name="one_lecture_per_day"),
        ]
 
    def __str__(self):
        return f"{self.course.code} on {self.date}"
 
    def qr_is_open(self, at=None):
        at = at or timezone.now()
        return self.qr_valid_from <= at <= self.qr_valid_until
 
    def attendance_count(self):
        return self.uploads.filter(is_valid=True).values("student").distinct().count()
 
 
class QRCodeUpload(models.Model):
    """
    A photo of a lecture's QR code uploaded by a student.
 
    `lecture` is nullable: the upload is always stored, even if the decoded
    QR value doesn't match any lecture. Keeping failed attempts gives an
    audit trail for spotting cheating (e.g. many invalid uploads).
    """
 
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="uploads"
    )
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploads",
    )
    image = models.ImageField(upload_to="qr_uploads/%Y/%m/%d/")
    decoded_value = models.CharField(max_length=64, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=False)
 
    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["student", "lecture"])]
 
    def __str__(self):
        return f"Upload by {self.student} at {self.uploaded_at:%Y-%m-%d %H:%M}"
 
    def validate(self):
        """
        Decide whether this upload counts as attendance. Sets and returns
        self.is_valid. Checks: QR matched a lecture, the student is actively
        enrolled in that lecture's course, and the upload happened inside the
        lecture's QR window.
        """
        self.is_valid = bool(
            self.lecture
            and self.decoded_value == str(self.lecture.qr_identifier)
            and Enrollment.objects.filter(
                student=self.student, course=self.lecture.course, is_active=True
            ).exists()
            and self.lecture.qr_is_open(self.uploaded_at or timezone.now())
        )
        return self.is_valid
 

