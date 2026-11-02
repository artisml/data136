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
#Create acc together
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



# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



