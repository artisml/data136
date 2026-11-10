"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""
import uuid

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from datetime import datetime
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError, transaction
from django.http import JsonResponse
import zoneinfo
import json
import io
from decimal import Decimal
from .models import InstructorProfile, StudentProfile


CDT = zoneinfo.ZoneInfo("America/Chicago")
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    cst = timezone(timedelta(hours=-6))
    context = {
        "current_time": datetime.now(cst).strftime("%H:%M"),
         "current_user": request.user,
    }

    return render(request, 'app/index.html', context)

def time_view(request):
    now = datetime.now(CDT)
    return HttpResponse(now.strftime("%H:%M"))
def sum_view(request):
    n1 = Decimal(request.GET.get("n1"))
    n2 = Decimal(request.GET.get("n2"))
    total = n1 + n2
    return HttpResponse(f"<p>{total}</p>")



# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------
@require_GET
def new(request):
    return render(request,"app/new.html")

@require_POST
@csrf_exempt

def createUser(request):
    username = request.POST.get("user_name", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    is_student = request.POST.get("is_student", "")

    if not username or not email or not password:
            return JsonResponse({"error": "All fields are required."}, status=400)

    if is_student not in ("1", "0"):
        return JsonResponse({"error": "Select a role."}, status=400)

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"error": "Email already registered."}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already taken."}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username = username,
                        email = email,
                password = password,
            )
            if is_student == "1":
                StudentProfile.objects.create(
                    user = user,
                    student_id=uuid.uuid4().hex[:20],
                )
            else:
                InstructorProfile.objects.create(user=user)
    except IntegrityError:
        return JsonResponse({"error": "Could not create account."}, status=400)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse({"message": "Account created successfully."})


# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------
@require_GET
def new_course(request):
    return render(request, "app/new_course.html")
@require_GET
def new_lecture(request):
    courses = Course.objects.order_by("name")
    return render(request, "app/new_lecture.html", {"courses": courses})
@require_GET
def new_qr_upload(request):
    return render(request, "app/new_qr_upload.html")

def role_profile(request, profile_model):
    if not request.user.is_authenticated:
        return None
    return profile_model.objects.filter(user=request.user).first()

@csrf_exempt
@require_POST
def createCourse(request):
    instructor = role_profile(request, InstructorProfile)
    if instructor is None:
        return JsonResponse({"error": "Instructor login required."}, status=401)
    name = request.POST.get("course-name", "").strip()
    start = request.POST.get("start-time", "").strip()
    end = request.POST.get("end-time", "").strip()
    
    days = []
    for day in ("mon", "tue", "wed", "thu", "fri"):
        if "day-" + day in request.POST:
            days.append(day.capitalize())
    if not name or not start or not end or not days:
        return JsonResponse({"error": "Enter a day of the week."}, status=400)
    try:
        start_time = clock_time.fromisoformat(start)
        end_time = clock_time.fromisoformat(end)
    except ValueError:
        return JsonResponse({"error": "Enter valid times."}, status=400)
    if start_time.tzinfo is not None or end_time.tzinfo is not None:
        return JsonResponse({"error": "Not in time zone."}, status=400)
    if end_time <= start_time:
        return JsonResponse({"error": "End time must be after start time."}, status=400)
    schedule = f"{', '.join(days)} {start}-{end}"

    if len(name) > Course._meta.get_field("name").max_length:
        return JsonResponse({"error": "Course name is too long."}, status=400)

    if len(schedule) > Course._meta.get_field("meeting_schedule").max_length:
        return JsonResponse({"error": "Schedule is too long."}, status=400)

    if Course.objects.filter(name=name).exists():
        return JsonResponse({"error": "Course name already exists."}, status=400)

    course = Course.objects.create(
        name=name,
        instructor=instructor,
        meeting_schedule=schedule,
    )
    return JsonResponse({"message": "Course created.", "id": course.pk})

@csrf_exempt
@require_POST
def createLecture(request):
    if role_profile(request, InstructorProfile) is None:
        return JsonResponse({"error": "Instructor login required."}, status=401)

    name = request.POST.get("choice", "").strip()
    course = Course.objects.filter(name=name).first()
    if course is None:
        return JsonResponse({"error": "This course doesnt exist"}, status=400)

    lecture = Lecture.objects.create(course=course, date=django_timezone.now())
    return JsonResponse({"message": "Lecture created.", "id": lecture.pk})

@csrf_exempt
@require_POST
def createQRCodeUpload(request):
    student = role_profile(request, StudentProfile)
    if student is None:
        return JsonResponse({"error": "Student login required."}, status=401)

    image = request.FILES.get("imageUpload")
    if image is None:
        return JsonResponse({"error": "Choose a file."}, status=400)

    upload = QRCodeUpload.objects.create(student=student, image=image)
    return JsonResponse({"message": "Upload confirmed.", "id": upload.pk})



@require_GET
def dumpUploads(request):
    if role_profile(request, InstructorProfile) is None:
            return JsonResponse({"error": "Instructor login required."}, status=401)
    data = []
    for upload in QRCodeUpload.objects.select_related("student__user").order_by("pk"):
        if hasattr(upload, "time_uploaded"):
            timestamp = upload.time_uploaded
        else:
            timestamp = upload.uploaded_at
        data.append({
            "username": upload.student.user.username,
            "upload_time": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return JsonResponse(data, safe=False)




# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



