import uuid
import random
import requests
import re  # For regex checking

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings  # To access API Key
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from django.urls import reverse
# Models
from .models import Shop, PasswordResetOTP

from django.contrib.auth import update_session_auth_hash # <--- NEW IMPORT



def create_admin(request):
    User = get_user_model()

    if User.objects.filter(username="admin").exists():
        return HttpResponse("Admin already exists")

    User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="Admin@123"
    )
    return HttpResponse("Superuser created successfully")
    
# --- 🛠️ HELPER: Send Email via BREVO API ---
def send_brevo_email(to_email, subject, html_content, sender_name="LedgerX"):
    url = "https://api.brevo.com/v3/smtp/email"
    
    payload = {
        "sender": {
            "name": sender_name,
            "email": settings.DEFAULT_FROM_EMAIL
        },
        "to": [
            {
                "email": to_email,
                # "name": "User" # Optional
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }
    
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        # Check if successful (Status 201 Created)
        if response.status_code in [200, 201, 202]:
            return True
        else:
            print(f"Brevo Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"Brevo Connection Error: {e}")
        return False

# --- HELPER: Rate Limiter ---
def is_rate_limited(request, key_name='otp_last_sent'):
    """Prevents spamming email APIs (60s cooldown)"""
    last_sent = request.session.get(key_name)
    if last_sent:
        elapsed = timezone.now().timestamp() - last_sent
        if elapsed < 60: # 60 seconds cooldown
            return True
    return False

def login_view(request):
    if request.method == 'POST':
        # Get the input (could be username OR email)
        login_input = request.POST.get('username') 
        password = request.POST.get('password')

        # 🟢 NEW LOGIC: Check if input looks like an email
        if '@' in login_input:
            try:
                # Try to find the user with this email
                user_obj = User.objects.get(email__iexact=login_input)
                # If found, use their actual username for authentication
                username_to_auth = user_obj.username
            except User.DoesNotExist:
                # If email doesn't exist, auth will fail naturally below
                username_to_auth = None
        else:
            # 🟢 2. CASE-INSENSITIVE USERNAME CHECK
            # This compares BOTH stored DB value and Input as if they were lowercase.
            # So 'Krish' == 'krish' is TRUE.
            user_obj = User.objects.filter(username__iexact=login_input).first()
            
            if user_obj:
                # If we found a match (e.g., found "Krish" when input was "krish")
                # we use the REAL username "Krish" to authenticate.
                username_to_auth = user_obj.username 
            else:
                username_to_auth = login_input

        # Authenticate using the resolved username
        user = authenticate(request, username=username_to_auth, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')

        messages.error(request, 'Invalid credentials')
        return redirect('login')

    return render(request, 'accounts/login.html')


def register_view(request):
    """
    Step 1: Collect Info, Validate, Send OTP via Resend.
    """
    # Default: Empty form data
    form_data = {} 

    if request.method == 'POST':
        # Capture what the user typed
        username = request.POST.get('username')
        email = request.POST.get('email').lower()
        password = request.POST.get('password')
        shop_name = request.POST.get('shop_name')
        owner_name = request.POST.get('owner_name')

        # Store it to send back if there's an error
        form_data = {
            'username': username,
            'email': email,
            'shop_name': shop_name,
            'owner_name': owner_name
        }

        # --- 🛡️ 1. EMAIL VALIDATION ---
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Invalid email address format.')
            return render(request, 'accounts/register.html', {'form_data': form_data})

        # --- 🛡️ 2. PASSWORD VALIDATION ---
        try:
            validate_password(password)
            if not re.search(r'[A-Z]', password):
                raise ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[0-9]', password):
                raise ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError("Password must contain at least one special character (!@#$).")
        except ValidationError as e:
            error_msg = str(e.messages[0]) if hasattr(e, 'messages') else str(e)
            messages.error(request, error_msg)
            return render(request, 'accounts/register.html', {'form_data': form_data})

        # --- 🛡️ 3. DUPLICATE CHECKS ---
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'accounts/register.html', {'form_data': form_data})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered. Please login.')
            return render(request, 'accounts/register.html', {'form_data': form_data})
        
        # --- RATE LIMIT CHECK ---
        if is_rate_limited(request, 'register_otp_timer'):
             messages.warning(request, "Please wait 60 seconds before requesting another code.")
             return redirect('verify_registration_otp')

        # --- SUCCESS: PROCEED TO OTP ---
        otp_code = str(random.randint(100000, 999999))
        
        request.session['register_data'] = {
            'username': username, 'email': email, 'password': password,
            'shop_name': shop_name, 'owner_name': owner_name, 'otp': otp_code, 'otp_created_at': timezone.now().timestamp() # <--- Store Time
        }
        request.session['register_otp_timer'] = timezone.now().timestamp() # Set timer

        # 🚀 SEND VIA BREVO
        html_msg = render_to_string('emails/register_otp.html', {'otp': otp_code, 'username': username})
        if send_brevo_email(email, "Verify Your LedgerX Account", html_msg):
            messages.success(request, f"OTP sent to {email}")
            return redirect('verify_registration_otp')
        else:
            messages.error(request, "Failed to send email. Please try again.")

    return render(request, 'accounts/register.html', {'form_data': form_data})


def verify_registration_otp_view(request):
    """
    Step 2: Verify OTP, Create Account, Send Welcome Email via Resend.
    """
    # Get data from session
    data = request.session.get('register_data')

    if not data:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')

    if request.method == 'POST':
        otp_input = request.POST.get('otp')

        if otp_input == data['otp']:

            created_at = data.get('otp_created_at')
            if created_at and (timezone.now().timestamp() - created_at > 600): # 600s = 10m
                messages.error(request, "OTP has expired. Please register again.")
                return redirect('register')
        
            # 1. Create User
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password']
            )

            # 2. Create Shop
            shop = Shop.objects.create(
                user=user,
                shop_name=data['shop_name'],
                owner_name=data['owner_name']
            )

            # 3. Login User
            login(request, user)

            # 🟢 GENERATE DYNAMIC LINK
        # This creates "http://127.0.0.1:8000/dashboard/" locally
        # AND "https://www.your-site.com/dashboard/" on production automatically.
            dashboard_link = request.build_absolute_uri(reverse('dashboard'))

            # 🚀 WELCOME EMAIL VIA BREVO
            html = render_to_string('emails/welcome.html', {'owner_name': data['owner_name'], 'shop_name': data['shop_name'], 'dashboard_url': dashboard_link})
            send_brevo_email(data['email'], "Welcome to LedgerX!", html)


            # 4. Cleanup Session
            del request.session['register_data']

            messages.success(request, "Account verified! Welcome to your Dashboard.")
            return redirect('dashboard')
        
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'accounts/verify_registration.html', {'email': data['email']})


def forgot_password_view(request):
    """
    Forgot Password Flow: Checks email, sends OTP via Resend.
    """
    if request.method == 'POST':
        email = request.POST.get('email').lower()

        try:
            user = User.objects.get(email=email)

            # Rate Limit
            if is_rate_limited(request, 'forgot_otp_timer'):
                messages.warning(request, "Wait 60s before resending.")
                return redirect('verify_otp')
            
            # 1. Generate OTP
            otp_code = str(random.randint(100000, 999999))
            
            # 2. Save OTP (Delete old ones first)
            PasswordResetOTP.objects.filter(user=user).delete()
            PasswordResetOTP.objects.create(user=user, otp=otp_code)

            # 3 🚀 SEND VIA BREVO
            html = render_to_string('emails/password_reset.html', {'otp': otp_code})
            if send_brevo_email(email, "Reset Your LedgerX Password", html):
                request.session['reset_email'] = email
                request.session['forgot_otp_timer'] = timezone.now().timestamp()
                messages.success(request, f"OTP sent to {email}")
                return redirect('verify_otp')
            else:
                messages.error(request, "Error sending email.")

        except User.DoesNotExist:
            messages.error(request, "This email is not registered with us.")
            return render(request, 'accounts/forgot_password.html')

    return render(request, 'accounts/forgot_password.html')


def verify_otp_view(request):
    # Get the email we stored in step 1
    email = request.session.get('reset_email')
    
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')

    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        
        try:
            user = User.objects.get(email=email)
            # Check if OTP matches the latest one in DB
            saved_otp = PasswordResetOTP.objects.filter(user=user, otp=otp_input).first()

            if saved_otp and saved_otp.otp == otp_input:
                # --- CHECK EXPIRATION (using model method) ---
                if saved_otp.is_valid():
                    request.session['otp_verified'] = True
                    saved_otp.delete() # One-time use!
                    return redirect('reset_password_confirm')
                else:
                    messages.error(request, "OTP has expired. Request a new one.")
            else:
                messages.error(request, "Invalid OTP.")

        except User.DoesNotExist:
             messages.error(request, "User not found.")

    return render(request, 'accounts/verify_otp.html')


def reset_password_confirm_view(request):
    email = request.session.get('reset_email')
    is_verified = request.session.get('otp_verified')

    # Security Check: Don't let them skip the OTP step!
    if not email or not is_verified:
        messages.error(request, "Unauthorized access. Please verify OTP first.")
        return redirect('forgot_password')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
        else:
            # Change Password
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()

            # Clean Session
            del request.session['reset_email']
            del request.session['otp_verified']

            messages.success(request, "Password changed successfully! Please Login.")
            return redirect('login')

    return render(request, 'accounts/reset_password.html')


@login_required
def logout_view(request):
    """
    Logs out the current user.
    """
    logout(request)
    return redirect('login')


@login_required
def account_settings(request):
    shop = request.user.shop
    user = request.user

    # Context dictionary to pass data (and triggers) to the template
    context = {'shop': shop}

    if request.method == 'POST':
        action = request.POST.get('action') # We use this to know WHICH form was submitted

        # ---------------------------------------------------
        # 1. CHANGE PASSWORD LOGIC (New)
        # ---------------------------------------------------
        if action == 'change_password':
            old_pass = request.POST.get('old_password')
            new_pass = request.POST.get('new_password')
            confirm_pass = request.POST.get('confirm_password')

            # Check 1: Old Password Correct?
            if not user.check_password(old_pass):
                messages.error(request, "Incorrect old password.")
                return redirect('account_settings')

            # Check 2: Match?
            if new_pass != confirm_pass:
                messages.error(request, "New passwords do not match.")
                return redirect('account_settings')

            # Check 3: Complexity?
            try:
                validate_password(new_pass, user=user)
            except ValidationError as e:
                # Get the first error message
                messages.error(request, e.messages[0])
                return redirect('account_settings')

            # SUCCESS
            user.set_password(new_pass)
            user.save()
            
            # 🔥 Important: Keep user logged in!
            update_session_auth_hash(request, user)
            
            messages.success(request, "Password changed successfully!")
            return redirect('account_settings')

        # ==========================================
        # 1. PROFILE UPDATE (Name, Shop, Photo, Username)
        # ==========================================
        if action == 'update_profile':
            new_shop_name = request.POST.get('shop_name')
            new_owner_name = request.POST.get('owner_name')
            new_username = request.POST.get('username')
            new_profile_pic = request.FILES.get('profile_pic')

            # Update Shop
            if new_shop_name: shop.shop_name = new_shop_name
            if new_owner_name: shop.owner_name = new_owner_name
            if new_profile_pic: shop.profile_pic = new_profile_pic
            
            # Update Username (Unique Check)
            if new_username and new_username != user.username:
                if User.objects.filter(username__iexact=new_username).exists():
                    # 🟢 ADDING TAG: 'modal_edit_profile'
                    messages.error(request, "Username already taken.", extra_tags='modal_edit_profile')
                    return redirect('account_settings')
                user.username = new_username
                user.save()

            shop.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('account_settings')

        # ==========================================
        # 2. REMOVE PHOTO
        # ==========================================
        elif action == 'remove_photo':
            if shop.profile_pic:
                shop.profile_pic.delete()
                shop.profile_pic = None
                shop.save()
            messages.success(request, "Profile photo removed.")
            return redirect('account_settings')

        # ==========================================
        # 3. CHANGE PASSWORD
        # ==========================================
        elif action == 'change_password':
            old_pass = request.POST.get('old_password')
            new_pass = request.POST.get('new_password')
            confirm_pass = request.POST.get('confirm_password')

            # 1. Verify Old Password
            if not user.check_password(old_pass):
                # 🟢 ADDING TAG: 'modal_change_password'
                messages.error(request, "Incorrect old password.", extra_tags='modal_change_password')
                return redirect('account_settings')

            # 2. Verify Match
            if new_pass != confirm_pass:
                messages.error(request, "New passwords do not match.", extra_tags='modal_change_password')
                return redirect('account_settings')

            # 3. 🛡️ SECURITY SHIELD (Validation)
            try:
                # A. Run Django's standard validators (Length, Common Passwords)
                validate_password(new_pass, user=user)
                
                # B. Run Custom "Pro" Checks (Capital, Number, Symbol)
                if not re.search(r'[A-Z]', new_pass):
                    raise ValidationError("Password must contain at least one uppercase letter.")
                if not re.search(r'[0-9]', new_pass):
                    raise ValidationError("Password must contain at least one number.")
                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_pass):
                    raise ValidationError("Password must contain at least one special character.")

            except ValidationError as e:
                # Show the specific error to the user (e.g., "Too short")
                error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
                messages.error(request, error_msg, extra_tags='modal_change_password')
                return redirect('account_settings')

            # 4. Success: Save
            user.set_password(new_pass)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
            return redirect('account_settings')

        # ... (Keep send_recovery_otp and verify_recovery_otp as is) ...

        # ==========================================
        # 🆕 RECOVERY FLOW (3-STEP MODAL)
        # ==========================================
        
        # --- STEP 1: SEND OTP ---
        elif action == 'send_recovery_otp':
            otp_code = str(random.randint(100000, 999999))
            
            # Save OTP
            PasswordResetOTP.objects.filter(user=user).delete()
            PasswordResetOTP.objects.create(user=user, otp=otp_code)

            # 🚀 SEND VIA BREVO
            html_msg = render_to_string('emails/password_reset.html', {'otp': otp_code})
            if send_brevo_email(user.email, "Security Verification Code", html_msg):
                messages.success(request, f"Code sent to {user.email}")
                context['show_otp_modal'] = True
            else:
                messages.error(request, "Failed to send email. Try again later.")
            return render(request, 'accounts/account_settings.html', context)

        # --- STEP 2: VERIFY OTP ---
        elif action == 'verify_recovery_otp':
            otp_input = request.POST.get('otp')
            saved_otp = PasswordResetOTP.objects.filter(user=user, otp=otp_input).first()

            if saved_otp:
                # Valid OTP!
                saved_otp.delete()
                request.session['recovery_verified'] = True # Mark as verified in session
                messages.success(request, "Identity verified. Set your new password.")
                
                # 🚀 TRIGGER FINAL MODAL
                context['show_reset_modal'] = True
                
            else:
                messages.error(request, "Invalid OTP Code.")
                # 🔄 RE-OPEN OTP MODAL
                context['show_otp_modal'] = True

            return render(request, 'accounts/account_settings.html', context)

        # --- STEP 3: SET NEW PASSWORD ---
        elif action == 'set_new_password_recovery':
            if not request.session.get('recovery_verified'):
                messages.error(request, "Session expired. Please start over.")
                return redirect('account_settings')

            new_pass = request.POST.get('new_password')
            confirm_pass = request.POST.get('confirm_password')

            if new_pass != confirm_pass:
                messages.error(request, "Passwords do not match.")
                context['show_reset_modal'] = True
                return render(request, 'accounts/account_settings.html', context)

            # 🛡️ SECURITY SHIELD (Same as above)
            try:
                validate_password(new_pass, user=user)
                if not re.search(r'[A-Z]', new_pass): raise ValidationError("Need uppercase letter.")
                if not re.search(r'[0-9]', new_pass): raise ValidationError("Need a number.")
                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_pass): raise ValidationError("Need special char.")
            except ValidationError as e:
                messages.error(request, e.messages[0] if hasattr(e, 'messages') else str(e))
                context['show_reset_modal'] = True # Keep modal open so they can retry
                return render(request, 'accounts/account_settings.html', context)

            # Success
            user.set_password(new_pass)
            user.save()
            update_session_auth_hash(request, user)
            
            if 'recovery_verified' in request.session: del request.session['recovery_verified']
            messages.success(request, "Password successfully reset!")
            return redirect('account_settings')

    return render(request, 'accounts/account_settings.html', {'shop': shop})

@login_required
def delete_shop_request_view(request):
    """
    Step 1: Show Warning & Send OTP button.
    """
    if request.method == 'POST':
        user = request.user
        email = user.email

        # 1. Generate OTP
        otp_code = str(random.randint(100000, 999999))

        # 2. Store OTP in session (Secure & Temporary)
        request.session['delete_account_otp'] = otp_code

        # 🚀 SEND VIA BREVO
        html_message = render_to_string('emails/delete_account_otp.html', {'otp': otp_code})
        if send_brevo_email(user.email, "⚠️ Confirm Account Deletion", html_message):
            messages.warning(request, f"Verification code sent to {user.email}")
            return redirect('delete_shop_verify')
        else:
            messages.error(request, "Email failed. Contact support.")

    return render(request, 'accounts/confirm_delete.html')


@login_required
def delete_shop_verify_view(request):
    """
    Step 2: Verify OTP and Nuke the Account.
    """
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        session_otp = request.session.get('delete_account_otp')

        if not session_otp:
            messages.error(request, "Session expired. Please try again.")
            return redirect('delete_shop_request')

        if otp_input == session_otp:
            # 💀 THE NUCLEAR OPTION
            user = request.user
            
            # Logout first to avoid session issues during delete
            logout(request)
            
            # Delete User (Cascades to Shop, Products, Sales, etc.)
            user.delete()

            # Clean session
            if 'delete_account_otp' in request.session:
                del request.session['delete_account_otp']

            messages.success(request, "Your account has been permanently deleted.")
            return redirect('login')
        
        else:
            messages.error(request, "Invalid Verification Code.")

    return render(request, 'accounts/verify_delete.html')


from django.http import JsonResponse

@login_required
def check_username(request):
    """
    API endpoint to check if username exists in real-time.
    """
    username = request.GET.get('username', None)
    if not username:
        return JsonResponse({'is_taken': False})

    # Check if taken by SOMEONE ELSE (ignore if it's the current user's own name)
    is_taken = User.objects.filter(username__iexact=username).exclude(username=request.user.username).exists()
    
    return JsonResponse({'is_taken': is_taken})

