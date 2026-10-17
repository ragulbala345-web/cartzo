import hashlib
import hmac
import secrets
import time
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account was created successfully!")
            return redirect("store:home")
    else:
        form = UserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "You are now logged in!")
            return redirect("store:home")
    else:
        form = AuthenticationForm(request)

    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have logged out.")
    return redirect("store:home")


@login_required
def profile(request):
    return render(request, "accounts/profile.html")


@require_http_methods(["GET", "POST"])
def mobile_otp(request):
    if not settings.DEBUG:
        return render(
            request,
            "accounts/mobile_otp.html",
            {"error": "Local OTP testing is disabled outside development mode."},
            status=403,
        )

    now = int(time.time())
    otp_hash = request.session.get("mobile_otp_hash")
    expires_at = request.session.get("mobile_otp_expires")
    phone = request.session.get("mobile_otp_phone", "")
    attempts = request.session.get("mobile_otp_attempts", 0)
    dev_otp = request.session.get("mobile_otp_debug")

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "send":
            phone = request.POST.get("phone", "").strip()

            if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
                messages.error(
                    request,
                    "Enter a valid international number, such as +919876543210.",
                )
            else:
                # Limit OTP generation to one request per 30 seconds.
                last_sent = request.session.get("mobile_otp_last_sent", 0)
                if now - last_sent < 30:
                    messages.error(request, "Please wait 30 seconds before requesting another OTP.")
                else:
                    code = f"{secrets.randbelow(1_000_000):06d}"
                    request.session["mobile_otp_hash"] = hashlib.sha256(
                        code.encode("utf-8")
                    ).hexdigest()
                    request.session["mobile_otp_expires"] = now + 300
                    request.session["mobile_otp_phone"] = phone
                    request.session["mobile_otp_attempts"] = 0
                    request.session["mobile_otp_last_sent"] = now

                    # Never display the development code outside DEBUG mode.
                    request.session["mobile_otp_debug"] = code
                    messages.success(
                        request,
                        "Test OTP generated. It expires in 5 minutes. No SMS was sent.",
                    )
                    return redirect("accounts:mobile_otp")

        elif action == "verify":
            submitted = request.POST.get("otp", "").strip()
            saved_hash = request.session.get("mobile_otp_hash")
            expiry = request.session.get("mobile_otp_expires")
            attempts = request.session.get("mobile_otp_attempts", 0)

            if not saved_hash or not expiry:
                messages.error(request, "Generate a new OTP first.")
            elif now > expiry:
                messages.error(request, "Your OTP has expired. Generate a new one.")
                request.session.pop("mobile_otp_hash", None)
                request.session.pop("mobile_otp_debug", None)
            elif attempts >= 5:
                messages.error(request, "Too many attempts. Generate a new OTP later.")
                request.session.pop("mobile_otp_hash", None)
                request.session.pop("mobile_otp_debug", None)
            elif not re.fullmatch(r"\d{6}", submitted):
                messages.error(request, "Enter exactly 6 digits.")
            else:
                request.session["mobile_otp_attempts"] = attempts + 1
                submitted_hash = hashlib.sha256(submitted.encode("utf-8")).hexdigest()

                if hmac.compare_digest(saved_hash, submitted_hash):
                    verified_phone = request.session.get("mobile_otp_phone", "")
                    request.session["mobile_otp_verified_phone"] = verified_phone
                    request.session.pop("mobile_otp_hash", None)
                    request.session.pop("mobile_otp_debug", None)
                    request.session.pop("mobile_otp_expires", None)
                    request.session.pop("mobile_otp_attempts", None)
                    messages.success(
                        request,
                        f"Development OTP verified for {verified_phone}. "
                        "This does not send an SMS or automatically verify a user account.",
                    )
                    return redirect("accounts:mobile_otp")
                else:
                    messages.error(request, "Incorrect OTP. Please try again.")

    context = {
        "phone": phone,
        "dev_otp": request.session.get("mobile_otp_debug"),
        "verified_phone": request.session.get("mobile_otp_verified_phone", ""),
    }
    return render(request, "accounts/mobile_otp.html", context)

# ============================================================
# CARTZO EMAIL OTP LOGIN
# ============================================================

import hashlib
import hmac
import secrets
import time

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods


class CartzoRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email address",
            "autocomplete": "email",
        }),
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        User = get_user_model()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()

        if commit:
            user.save()

        return user


def register(request):
    if request.method == "POST":
        form = CartzoRegistrationForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Account created successfully! Please log in using your username and password."
            )

            return redirect("accounts:login")
    else:
        form = CartzoRegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()

            if not user.email:
                messages.error(
                    request,
                    "Your account has no email address. Please update your email in your account before using OTP login."
                )
                return render(
                    request,
                    "accounts/login.html",
                    {"form": form},
                )

            now = int(time.time())
            last_sent = request.session.get(
                "login_otp_last_sent", 0
            )

            if now - last_sent < 30:
                messages.error(
                    request,
                    "Please wait 30 seconds before requesting another OTP."
                )
                return render(
                    request,
                    "accounts/login.html",
                    {"form": form},
                )

            code = f"{secrets.randbelow(1000000):06d}"

            request.session["login_otp_user_id"] = user.pk
            request.session["login_otp_hash"] = hashlib.sha256(
                code.encode("utf-8")
            ).hexdigest()
            request.session["login_otp_expires"] = now + 300
            request.session["login_otp_attempts"] = 0
            request.session["login_otp_last_sent"] = now

            try:
                send_mail(
                    subject="Your Cartzo Login OTP",
                    message=(
                        f"Hello {user.username},\n\n"
                        f"Your Cartzo login OTP is: {code}\n\n"
                        "This OTP expires in 5 minutes.\n"
                        "Do not share this code with anyone.\n\n"
                        "If you did not request this code, you can ignore this email."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

            except Exception:
                for key in (
                    "login_otp_user_id",
                    "login_otp_hash",
                    "login_otp_expires",
                    "login_otp_attempts",
                ):
                    request.session.pop(key, None)

                messages.error(
                    request,
                    "We could not send your OTP. Please check the email configuration and try again."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {"form": form},
                )

            messages.success(
                request,
                "Your login OTP has been generated. Check the development server terminal for the test email."
            )

            return redirect("accounts:verify_otp")

    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


@require_http_methods(["GET", "POST"])
def verify_otp(request):
    user_id = request.session.get("login_otp_user_id")

    if not user_id:
        messages.error(
            request,
            "Please log in with your username and password first."
        )
        return redirect("accounts:login")

    if request.method == "POST":
        now = int(time.time())
        saved_hash = request.session.get("login_otp_hash")
        expires_at = request.session.get("login_otp_expires")
        attempts = request.session.get("login_otp_attempts", 0)

        if not saved_hash or not expires_at:
            messages.error(
                request,
                "Your OTP is unavailable. Please log in again."
            )
            return redirect("accounts:login")

        if now > expires_at:
            for key in (
                "login_otp_user_id",
                "login_otp_hash",
                "login_otp_expires",
                "login_otp_attempts",
            ):
                request.session.pop(key, None)

            messages.error(
                request,
                "Your OTP has expired. Please log in again."
            )
            return redirect("accounts:login")

        if attempts >= 5:
            for key in (
                "login_otp_user_id",
                "login_otp_hash",
                "login_otp_expires",
                "login_otp_attempts",
            ):
                request.session.pop(key, None)

            messages.error(
                request,
                "Too many incorrect attempts. Please log in again."
            )
            return redirect("accounts:login")

        submitted = request.POST.get("otp", "").strip()

        if not submitted.isdigit() or len(submitted) != 6:
            messages.error(
                request,
                "Enter a valid six-digit OTP."
            )
        else:
            request.session["login_otp_attempts"] = attempts + 1

            submitted_hash = hashlib.sha256(
                submitted.encode("utf-8")
            ).hexdigest()

            if hmac.compare_digest(saved_hash, submitted_hash):
                User = get_user_model()

                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    messages.error(
                        request,
                        "Your account could not be found. Please log in again."
                    )
                    return redirect("accounts:login")

                for key in (
                    "login_otp_user_id",
                    "login_otp_hash",
                    "login_otp_expires",
                    "login_otp_attempts",
                    "login_otp_last_sent",
                ):
                    request.session.pop(key, None)

                login(request, user)

                messages.success(
                    request,
                    "Welcome to Cartzo! Your OTP was verified successfully."
                )

                return redirect("store:home")

            messages.error(
                request,
                "Incorrect OTP. Please try again."
            )

    return render(
        request,
        "accounts/verify_otp.html",
    )

