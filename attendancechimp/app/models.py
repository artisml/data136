
"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- CourseProfile   : extends Django User → instructor-specific data
- StudentProfile  : extends Django User → student-specific data
- Course          : a course taught by one instructor
- Enrollment      : junction table linking students to courses
- Lecture         : a single class meeting (has a QR-code identifier)
- QRCodeUpload    : a student's uploaded QR-code photograph
"""

from django.db import models
from django.contrib.auth.models import User
import uuid
import logging
import string
import random


logger = logging.getLogger(__name__) # set up tracking, auditing, and debugging
                                                               # allows using logger.warning(), logger.error(), 
                                                               # logger.info(), etc. Better than print() for debuggin... 


# ---------------------------------------------------------------------------
# User profiles - CHANGE TO INSTRUCTOR PROFILES AND STUDENT PROFILES
# ---------------------------------------------------------------------------

class InstructorProfile (models.Model):
	#""doc string - store instructor info""
	user = models.OneToOneField(
		User,
		on_delete = models.CASCADE,
	)
	department = models.CharField(max_length=100, blank=True)
	def __str__(self):
		return self.user.get_username()

class StudentProfile(models.Model):
	#""store student info and ID which is unique""
	user = models.OneToOneField(
		User,
		on_delete = models.CASCADE,
	)
	student_id = models.CharField(unique = True)
	def __str__(self):
		return self.user.get_username()


# ---------------------------------------------------------------------------
# Course
class Course(models.Model):
	#""store course with instructor name and meeting schedule""

	name = models.CharField()
	instructor = models.ForeignKey(
		InstructorProfile,
		on_delete = models.PROTECT,
	)
	meeting_schedule = models.CharField()
	def __str__(self):
		return self.name

#INCLUDE NAME INSTRUCTOR MEETING SCHEDULE
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------
class Enrollment(models.Model):
	#""links students to courses - many to many""
	student = models.ForeignKey(
		StudentProfile,
		on_delete = models.CASCADE,
	)
	course = models.ForeignKey(
		Course,
		on_delete = models.CASCADE
	)
	enrolled_in = models.DateTimeField(auto_now_add = True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields = ["student", "course"],
				name = "unique_student_course",
			)
		]
	def __str__(self):
		return f"{self.student} - {self.course}"


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

class Lecture(models.Model):
	#""store course w date, time, and qr""
	course = models.ForeignKey(
		Course,
		on_delete = models.CASCADE

	)
	date = models.DateTimeField()
	qr = models.UUIDField(
		default = uuid.uuid4,
		unique = True,
	)

	def __str__(self):
		return f"{self.course} - {self.date}"



# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------

class QRCodeUpload(models.Model):
	#""upload photo, have to verify upload, fits design requirement of being robust to cheating because it needs to verify qr, coourse enrollment, and submission time before being completed.
	student = models.ForeignKey(
		StudentProfile,
		on_delete = models.CASCADE,
	)

	lecture = models.ForeignKey(
		Lecture,
		on_delete = models.SET_NULL,
		null = True,
	)
	image = models.FileField(upload_to = "qr_uploads/") #stores path photo is uploaded in
	time_uploaded = models.DateTimeField(auto_now_add = True)
	verified = models.BooleanField(default = False)

	def __str__(self):
		return f"upload {self.pk} by {self.student}"




# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------




