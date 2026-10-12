from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum, F  # Add F here
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
import qrcode
from io import BytesIO
import json
import base64
import folium
from folium import plugins
from .models import *

# ============ PUBLIC PAGES ============

def home(request):
    """Homepage with beautiful hero section"""
    total_farms = Farm.objects.count()
    total_cattle = Cattle.objects.count()
    vaccinated = Cattle.objects.filter(vaccination_status='fully').count()
    active_alerts = DiseaseAlert.objects.filter(is_active=True).count()
    
    if total_cattle > 0:
        vax_percentage = round((vaccinated / total_cattle) * 100)
    else:
        vax_percentage = 0
    
    recent_alerts = DiseaseAlert.objects.filter(is_active=True)[:3]
    
    context = {
        'total_farms': total_farms,
        'total_cattle': total_cattle,
        'vax_percentage': vax_percentage,
        'active_alerts': active_alerts,
        'recent_alerts': recent_alerts,
    }
    return render(request, 'core/home.html', context)

def about(request):
    return render(request, 'core/about.html')

def services(request):
    return render(request, 'core/services.html')

def alerts(request):
    """Disease alerts page"""
    alerts_list = DiseaseAlert.objects.filter(is_active=True).order_by('-severity', '-date_reported')
    return render(request, 'core/alerts.html', {'alerts': alerts_list})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        messages.success(request, 'Thank you for your message! We will get back to you soon.')
        return redirect('contact')
    return render(request, 'core/contact.html')

def login_view(request):
    if request.user.is_authenticated:
        # Redirect to role-specific dashboard if already logged in
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role == 'vet':
                return redirect('vet_dashboard')
            elif profile.role == 'exporter':
                return redirect('exporter_dashboard')
            elif profile.role == 'official':
                return redirect('official_dashboard')
            elif profile.role == 'distributor':
                return redirect('distributor_dashboard')
            elif profile.role == 'inspector':
                return redirect('inspector_dashboard')
            else:
                return redirect('dashboard')
        except:
            return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            try:
                profile = UserProfile.objects.get(user=user)
                if profile.role == 'vet':
                    return redirect('vet_dashboard')
                elif profile.role == 'exporter':
                    return redirect('exporter_dashboard')
                elif profile.role == 'official':
                    return redirect('official_dashboard')
                elif profile.role == 'distributor':
                    return redirect('distributor_dashboard')
                elif profile.role == 'inspector':
                    return redirect('inspector_dashboard')
                else:
                    return redirect('dashboard')
            except UserProfile.DoesNotExist:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'core/login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role', 'farmer')
        phone = request.POST.get('phone')
        id_number = request.POST.get('id_number')
        province = request.POST.get('province')
        district = request.POST.get('district')
        
        # Password validation
        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')
        
        # Check password requirements
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('register')
        
        if not any(c.isupper() for c in password):
            messages.error(request, 'Password must contain at least one uppercase letter.')
            return redirect('register')
        
        if not any(c.isdigit() for c in password):
            messages.error(request, 'Password must contain at least one number.')
            return redirect('register')
        
        if not any(c in '!@#$%^&*' for c in password):
            messages.error(request, 'Password must contain at least one special character (!@#$%^&*).')
            return redirect('register')
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('register')
        
        # Create user
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            first_name=first_name, 
            last_name=last_name
        )
        
        # Create profile
        UserProfile.objects.create(
            user=user, 
            role=role, 
            phone_number=phone, 
            id_number=id_number,
            province=province, 
            district=district,
            practice_number=request.POST.get('practice_number', '') if role == 'vet' else '',
            company_name=request.POST.get('company_name', '') if role in ['exporter', 'distributor'] else ''
        )
        
        messages.success(request, 'Registration successful! Please login.')
        return redirect('login')
    
    return render(request, 'core/register.html')

def vet_register(request):
    """Dedicated registration page for veterinarians"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        id_number = request.POST.get('id_number')
        province = request.POST.get('province')
        district = request.POST.get('district')
        practice_number = request.POST.get('practice_number')
        
        # Password validation
        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('vet_register')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('vet_register')
        
        if not any(c.isupper() for c in password):
            messages.error(request, 'Password must contain at least one uppercase letter.')
            return redirect('vet_register')
        
        if not any(c.isdigit() for c in password):
            messages.error(request, 'Password must contain at least one number.')
            return redirect('vet_register')
        
        if not any(c in '!@#$%^&*' for c in password):
            messages.error(request, 'Password must contain at least one special character (!@#$%^&*).')
            return redirect('vet_register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('vet_register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('vet_register')
        
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            first_name=first_name, 
            last_name=last_name
        )
        
        UserProfile.objects.create(
            user=user, 
            role='vet',
            phone_number=phone, 
            id_number=id_number,
            province=province, 
            district=district,
            practice_number=practice_number
        )
        
        messages.success(request, 'Veterinarian registration successful! Please login.')
        return redirect('login')
    
    return render(request, 'core/vet_register.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

# ============ MAIN DASHBOARD ============

@login_required
def national_progress(request):
    total_cattle = Cattle.objects.count()
    fully_vaccinated = Cattle.objects.filter(vaccination_status='fully').count()
    partially_vaccinated = Cattle.objects.filter(vaccination_status='partial').count()
    unvaccinated = Cattle.objects.filter(vaccination_status='unvaccinated').count()
    
    national_rate = round((fully_vaccinated / total_cattle * 100) if total_cattle > 0 else 0)
    target_80_percent = total_cattle * 0.8
    remaining_to_target = max(0, target_80_percent - fully_vaccinated)
    
    provinces = Farm.objects.values('province').annotate(
        total=Count('cattle'),
        vaccinated=Count('cattle', filter=Q(cattle__vaccination_status='fully')),
        partial=Count('cattle', filter=Q(cattle__vaccination_status='partial'))
    )
    
    for p in provinces:
        p['rate'] = round((p['vaccinated'] / p['total'] * 100) if p['total'] > 0 else 0)
    
    # Weekly data for chart
    last_8_weeks = []
    for i in range(7, -1, -1):
        week_date = date.today() - timedelta(days=i*7)
        week_vaccinations = VaccinationRecord.objects.filter(
            vaccination_date__gte=week_date,
            vaccination_date__lt=week_date + timedelta(days=7)
        ).count()
        last_8_weeks.append({
            'week': week_date.strftime('W%W'),
            'count': week_vaccinations
        })
    
    context = {
        'total_cattle': total_cattle,
        'fully_vaccinated': fully_vaccinated,
        'partially_vaccinated': partially_vaccinated,
        'unvaccinated': unvaccinated,
        'national_rate': national_rate,
        'remaining_to_target': int(remaining_to_target),
        'provinces': provinces,
        'weekly_data': json.dumps(last_8_weeks),
    }
    return render(request, 'core/national_progress.html', context)

@login_required
def dashboard(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        # Redirect to role-specific dashboard
        if profile.role == 'vet':
            return redirect('vet_dashboard')
        elif profile.role == 'exporter':
            return redirect('exporter_dashboard')
        elif profile.role == 'official':
            return redirect('official_dashboard')
        elif profile.role == 'distributor':
            return redirect('distributor_dashboard')
        elif profile.role == 'inspector':
            return redirect('inspector_dashboard')
        
        # Farmer dashboard (default)
        if profile.role == 'farmer':
            farms = Farm.objects.filter(farmer=profile)
            cattle = Cattle.objects.filter(farm__in=farms)
            total_cattle = cattle.count()
            vaccinated = cattle.filter(vaccination_status='fully').count()
            partial = cattle.filter(vaccination_status='partial').count()
            unvaccinated = cattle.filter(vaccination_status='unvaccinated').count()
            
            recent_vaccinations = VaccinationRecord.objects.filter(
                cattle__farm__in=farms
            ).order_by('-vaccination_date')[:5]
            
            today = date.today()
            upcoming_boosters = ReminderSchedule.objects.filter(
                vaccination__cattle__farm__in=farms,
                due_date__gte=today,
                due_date__lte=today + timedelta(days=7),
                completed=False
            )
            
            appointments = VetAppointment.objects.filter(
                farmer=profile, status='pending'
            )[:5]
            
            context = {
                'profile': profile,
                'total_cattle': total_cattle,
                'vaccinated': vaccinated,
                'partial': partial,
                'unvaccinated': unvaccinated,
                'vaccination_rate': round((vaccinated / total_cattle * 100) if total_cattle > 0 else 0),
                'recent_vaccinations': recent_vaccinations,
                'upcoming_boosters': upcoming_boosters,
                'appointments': appointments,
            }
            return render(request, 'core/dashboard.html', context)
        
        # Default fallback
        context = {
            'profile': profile,
            'total_cattle': Cattle.objects.count(),
            'vaccinated': Cattle.objects.filter(vaccination_status='fully').count(),
            'vaccination_rate': 0,
            'recent_vaccinations': [],
        }
        return render(request, 'core/dashboard.html', context)
        
    except UserProfile.DoesNotExist:
        context = {'profile': None, 'total_cattle': 0, 'vaccinated': 0}
        return render(request, 'core/dashboard.html', context)

# ============ FARM MANAGEMENT ============

@login_required
def my_farms(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.role == 'farmer':
        farms = Farm.objects.filter(farmer=profile)
    else:
        farms = Farm.objects.all()
    return render(request, 'core/farms.html', {'farms': farms})

@login_required
def add_farm(request):
    if request.method == 'POST':
        profile = UserProfile.objects.get(user=request.user)
        farm = Farm.objects.create(
            farmer=profile,
            farm_name=request.POST.get('farm_name'),
            gps_latitude=request.POST.get('gps_latitude'),
            gps_longitude=request.POST.get('gps_longitude'),
            province=request.POST.get('province'),
            district=request.POST.get('district'),
            farm_size=request.POST.get('farm_size'),
            owner_contact=request.POST.get('owner_contact')
        )
        messages.success(request, f'Farm {farm.farm_name} registered successfully!')
        return redirect('my_farms')
    return render(request, 'core/add_farm.html')

# ============ CATTLE MANAGEMENT ============

@login_required
def my_cattle(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.role == 'farmer':
        farms = Farm.objects.filter(farmer=profile)
        cattle = Cattle.objects.filter(farm__in=farms)
    else:
        cattle = Cattle.objects.all()
    
    status_filter = request.GET.get('status')
    if status_filter:
        cattle = cattle.filter(vaccination_status=status_filter)
    
    return render(request, 'core/cattle.html', {'cattle': cattle, 'profile': profile})

@login_required
def add_cattle(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        farm_name = request.POST.get('farm_name', '').strip()
        tag_number = request.POST.get('tag_number', '').strip()
        name = request.POST.get('name', '').strip()
        breed = request.POST.get('breed')
        sex = request.POST.get('sex')
        date_of_birth = request.POST.get('date_of_birth')
        weight = request.POST.get('weight', '')
        gps_latitude = request.POST.get('gps_latitude', '')
        gps_longitude = request.POST.get('gps_longitude', '')
        farm_size = request.POST.get('farm_size', '')
        
        # Validate required fields
        if not farm_name:
            messages.error(request, 'Please enter a farm name.')
            return render(request, 'core/add_cattle.html')
        
        if not tag_number:
            messages.error(request, 'Please enter a tag number.')
            return render(request, 'core/add_cattle.html')
        
        if not breed:
            messages.error(request, 'Please select a breed.')
            return render(request, 'core/add_cattle.html')
        
        if not sex:
            messages.error(request, 'Please select sex.')
            return render(request, 'core/add_cattle.html')
        
        if not date_of_birth:
            messages.error(request, 'Please enter date of birth.')
            return render(request, 'core/add_cattle.html')
        
        # Handle decimal fields - convert empty strings to None
        weight_value = None
        if weight and weight.strip():
            try:
                weight_value = float(weight)
            except ValueError:
                messages.error(request, 'Invalid weight value.')
                return render(request, 'core/add_cattle.html')
        
        # Handle GPS and farm size for new farms (only if farmer role)
        gps_lat_value = None
        gps_lng_value = None
        farm_size_value = None
        
        if profile.role == 'farmer':
            if gps_latitude and gps_latitude.strip():
                try:
                    gps_lat_value = float(gps_latitude)
                except ValueError:
                    gps_lat_value = -26.195  # Default for South Africa
            
            if gps_longitude and gps_longitude.strip():
                try:
                    gps_lng_value = float(gps_longitude)
                except ValueError:
                    gps_lng_value = 28.034  # Default for South Africa
            
            if farm_size and farm_size.strip():
                try:
                    farm_size_value = float(farm_size)
                except ValueError:
                    farm_size_value = 0
        
        # Get or create farm by name
        if profile.role == 'farmer':
            # For farmers: create new farm or use existing one
            farm, created = Farm.objects.get_or_create(
                farm_name=farm_name,
                farmer=profile,
                defaults={
                    'gps_latitude': gps_lat_value if gps_lat_value else -26.195,
                    'gps_longitude': gps_lng_value if gps_lng_value else 28.034,
                    'province': profile.province,
                    'district': profile.district,
                    'farm_size': farm_size_value if farm_size_value else 0,
                    'owner_contact': profile.phone_number
                }
            )
            if created:
                messages.success(request, f'New farm "{farm.farm_name}" created!')
        else:
            # For admins/vets: use existing farm
            try:
                farm = Farm.objects.get(farm_name=farm_name)
            except Farm.DoesNotExist:
                messages.error(request, f'Farm "{farm_name}" not found. Please create the farm first.')
                return redirect('add_cattle')
        
        # Check if tag number already exists
        if Cattle.objects.filter(tag_number=tag_number).exists():
            messages.error(request, f'Cattle with tag number "{tag_number}" already exists!')
            return render(request, 'core/add_cattle.html')
        
        # Create cattle
        try:
            cattle = Cattle.objects.create(
                farm=farm,
                tag_number=tag_number,
                name=name if name else None,
                breed=breed,
                sex=sex,
                date_of_birth=date_of_birth,
                weight=weight_value
            )
            messages.success(request, f'Cattle {cattle.tag_number} registered to farm "{farm.farm_name}"!')
            return redirect('my_cattle')
        except Exception as e:
            messages.error(request, f'Error creating cattle: {str(e)}')
            return render(request, 'core/add_cattle.html')
    
    # GET request - show form
    return render(request, 'core/add_cattle.html')

# ============ VACCINE BATCH MANAGEMENT ============

@login_required
def vaccine_batches(request):
    batches = VaccineBatch.objects.all().order_by('-arrival_date')
    low_stock_threshold = 5000
    low_stock_batches = batches.filter(quantity_remaining__lt=low_stock_threshold, status='in_storage')
    
    context = {
        'batches': batches,
        'low_stock_batches': low_stock_batches,
        'low_stock_threshold': low_stock_threshold,
    }
    return render(request, 'core/batches.html', context)

@login_required
def add_vaccine_batch(request):
    if request.method == 'POST':
        batch = VaccineBatch.objects.create(
            batch_number=request.POST.get('batch_number'),
            manufacturer=request.POST.get('manufacturer'),
            country_of_origin=request.POST.get('country_of_origin'),
            quantity=int(request.POST.get('quantity')),
            quantity_remaining=int(request.POST.get('quantity')),
            production_date=request.POST.get('production_date'),
            expiry_date=request.POST.get('expiry_date'),
            storage_location=request.POST.get('storage_location')
        )
        messages.success(request, f'Batch {batch.batch_number} added!')
        return redirect('vaccine_batches')
    return render(request, 'core/add_batch.html')

@login_required
def cold_chain_monitoring(request):
    if request.method == 'POST':
        batch_id = request.POST.get('batch')
        temperature = float(request.POST.get('temperature'))
        location = request.POST.get('location')
        
        batch = VaccineBatch.objects.get(id=batch_id)
        log = ColdChainLog.objects.create(
            batch=batch,
            temperature=temperature,
            location=location
        )
        
        if log.is_breach:
            messages.warning(request, f'⚠️ Cold chain breach detected for batch {batch.batch_number}!')
        else:
            messages.success(request, 'Temperature recorded successfully.')
        
        return redirect('cold_chain_monitoring')
    
    batches = VaccineBatch.objects.all()
    logs = ColdChainLog.objects.all().order_by('-timestamp')[:20]
    return render(request, 'core/cold_chain.html', {'batches': batches, 'logs': logs})

# ============ VACCINATION RECORDING ============

@login_required
def record_vaccination(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        cattle_id = request.POST.get('cattle')
        batch_id = request.POST.get('vaccine_batch')
        dose_number = int(request.POST.get('dose_number'))
        vaccination_date = request.POST.get('vaccination_date')
        
        try:
            cattle = Cattle.objects.get(id=cattle_id)
            batch = VaccineBatch.objects.get(id=batch_id)
            
            if batch.expiry_date < date.today():
                messages.error(request, 'Vaccine batch has expired!')
            elif batch.status == 'cold_chain_breach':
                messages.error(request, 'Vaccine batch has cold chain breach!')
            elif batch.quantity_remaining <= 0:
                messages.error(request, 'Insufficient vaccine doses!')
            else:
                VaccinationRecord.objects.create(
                    cattle=cattle,
                    vaccine_batch=batch,
                    vet=profile if profile.role == 'vet' else None,
                    dose_number=dose_number,
                    vaccination_date=vaccination_date,
                    gps_latitude=request.POST.get('gps_latitude', -26.195),
                    gps_longitude=request.POST.get('gps_longitude', 28.034)
                )
                messages.success(request, f'Dose {dose_number} recorded for {cattle.tag_number}!')
                return redirect('vaccination_history')
        except Exception as e:
            messages.error(request, str(e))
    
    if profile.role == 'farmer':
        farms = Farm.objects.filter(farmer=profile)
        cattle = Cattle.objects.filter(farm__in=farms)
    else:
        cattle = Cattle.objects.all()
    
    batches = VaccineBatch.objects.filter(
        status='in_storage',
        expiry_date__gt=date.today(),
        quantity_remaining__gt=0
    )
    
    return render(request, 'core/record_vaccination.html', {
        'cattle': cattle,
        'batches': batches
    })

@login_required
def vaccination_history(request):
    profile = UserProfile.objects.get(user=request.user)
    
    cattle_id = request.GET.get('cattle')
    if cattle_id:
        records = VaccinationRecord.objects.filter(cattle_id=cattle_id).order_by('-vaccination_date')
    elif profile.role == 'farmer':
        farms = Farm.objects.filter(farmer=profile)
        records = VaccinationRecord.objects.filter(cattle__farm__in=farms).order_by('-vaccination_date')
    else:
        records = VaccinationRecord.objects.all().order_by('-vaccination_date')
    
    return render(request, 'core/vaccination_history.html', {'records': records})

@login_required
def reminders(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role == 'farmer':
        farms = Farm.objects.filter(farmer=profile)
        reminders_list = ReminderSchedule.objects.filter(
            vaccination__cattle__farm__in=farms,
            completed=False
        ).order_by('due_date')
    else:
        reminders_list = ReminderSchedule.objects.filter(completed=False).order_by('due_date')
    
    return render(request, 'core/reminders.html', {'reminders': reminders_list})

# ============ QR CODE VERIFICATION ============

@login_required
def qr_verification(request):
    return render(request, 'core/qr_verification.html')

def verify_qr_api(request, qr_data):
    if qr_data.startswith('CATTLE:'):
        tag_number = qr_data.replace('CATTLE:', '')
        try:
            cattle = Cattle.objects.get(tag_number=tag_number)
            return JsonResponse({
                'type': 'cattle',
                'exists': True,
                'tag_number': cattle.tag_number,
                'farm': cattle.farm.farm_name,
                'vaccination_status': cattle.vaccination_status,
            })
        except Cattle.DoesNotExist:
            return JsonResponse({'exists': False}, status=404)
    return JsonResponse({'error': 'Invalid QR code'}, status=400)

# ============ EXPORT CERTIFICATE ============

@login_required
def export_certificate_generator(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        cattle_id = request.POST.get('cattle_id')
        cattle = get_object_or_404(Cattle, id=cattle_id)
        
        vaccinations = VaccinationRecord.objects.filter(cattle=cattle)
        has_dose1 = vaccinations.filter(dose_number=1).exists()
        has_dose2 = vaccinations.filter(dose_number=2).exists()
        
        if has_dose1 and has_dose2:
            certificate = ExportCertificate.objects.create(
                cattle=cattle,
                exporter=profile if profile.role == 'exporter' else None,
                expiry_date=date.today() + timedelta(days=365),
                is_compliant=True
            )
            return redirect('download_certificate', certificate.id)
        else:
            messages.error(request, 'Cattle is not fully vaccinated!')
    
    if profile.role == 'farmer':
        farms = Farm.objects.filter(farmer=profile)
        cattle = Cattle.objects.filter(farm__in=farms)
    else:
        cattle = Cattle.objects.all()
    
    return render(request, 'core/export_certificate.html', {'cattle': cattle})

@login_required
def download_certificate(request, cert_id):
    certificate = get_object_or_404(ExportCertificate, id=cert_id)
    cattle = certificate.cattle
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{cattle.tag_number}.pdf"'
    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    p.setFillColor(HexColor('#1a472a'))
    p.rect(0, height - 60, width, 60, fill=1)
    p.setFillColor(HexColor('#ffffff'))
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 40, "UGCINO EXPORT CERTIFICATE")
    
    p.setFillColor(HexColor('#000000'))
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 80, f"Certificate: {certificate.certificate_number}")
    p.drawString(50, height - 95, f"Verification: {certificate.verification_code}")
    p.drawString(50, height - 110, f"Issue Date: {certificate.issue_date}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 160, "ANIMAL DETAILS")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 190, f"Tag Number: {cattle.tag_number}")
    p.drawString(50, height - 210, f"Breed: {cattle.get_breed_display()}")
    p.drawString(50, height - 230, f"Farm: {cattle.farm.farm_name}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 280, "VACCINATION HISTORY")
    
    vaccinations = VaccinationRecord.objects.filter(cattle=cattle).order_by('dose_number')
    y = height - 310
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Dose")
    p.drawString(120, y, "Date")
    p.drawString(220, y, "Batch Number")
    
    y -= 20
    p.setFont("Helvetica", 10)
    for vax in vaccinations:
        p.drawString(50, y, str(vax.dose_number))
        p.drawString(120, y, str(vax.vaccination_date))
        p.drawString(220, y, vax.vaccine_batch.batch_number)
        y -= 20
    
    y -= 20
    if certificate.is_compliant:
        p.setFillColor(HexColor('#27ae60'))
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "✓ COMPLIANT - Approved for Export")
    
    p.showPage()
    p.save()
    return response

# ============ VET DASHBOARD ============

@login_required
def vet_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'vet':
        messages.error(request, 'Access denied. Veterinarian only.')
        return redirect('dashboard')
    
    total_vaccinations = VaccinationRecord.objects.filter(vet=profile).count()
    today_vaccinations = VaccinationRecord.objects.filter(vet=profile, vaccination_date=date.today()).count()
    this_week_vaccinations = VaccinationRecord.objects.filter(
        vet=profile,
        vaccination_date__gte=date.today() - timedelta(days=7)
    ).count()
    
    pending_appointments = VetAppointment.objects.filter(
        vet=profile, 
        status='pending',
        appointment_date__gte=datetime.now()
    ).order_by('appointment_date')[:10]
    
    today_appointments = VetAppointment.objects.filter(
        vet=profile,
        appointment_date__date=date.today()
    ).order_by('appointment_date')
    
    recent_vaccinations = VaccinationRecord.objects.filter(
        vet=profile
    ).order_by('-vaccination_date')[:10]
    
    upcoming_boosters = ReminderSchedule.objects.filter(
        completed=False,
        due_date__gte=date.today(),
        due_date__lte=date.today() + timedelta(days=7)
    )[:10]
    
    low_stock_batches = VaccineBatch.objects.filter(
        quantity_remaining__lt=1000,
        status='in_storage',
        expiry_date__gt=date.today()
    )
    
    recent_breaches = ColdChainLog.objects.filter(is_breach=True).order_by('-timestamp')[:5]
    
    context = {
        'profile': profile,
        'total_vaccinations': total_vaccinations,
        'today_vaccinations': today_vaccinations,
        'this_week_vaccinations': this_week_vaccinations,
        'pending_appointments': pending_appointments,
        'today_appointments': today_appointments,
        'recent_vaccinations': recent_vaccinations,
        'upcoming_boosters': upcoming_boosters,
        'low_stock_batches': low_stock_batches,
        'recent_breaches': recent_breaches,
        'total_cattle': Cattle.objects.count(),
        'fully_vaccinated': Cattle.objects.filter(vaccination_status='fully').count(),
    }
    return render(request, 'core/vet_dashboard.html', context)

@login_required
def vet_appointments(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'vet':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    status_filter = request.GET.get('status', 'all')
    date_filter = request.GET.get('date', '')
    
    appointments = VetAppointment.objects.filter(vet=profile)
    
    if status_filter != 'all':
        appointments = appointments.filter(status=status_filter)
    
    if date_filter:
        appointments = appointments.filter(appointment_date__date=date_filter)
    
    appointments = appointments.order_by('-appointment_date')
    
    context = {
        'appointments': appointments,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    return render(request, 'core/vet_appointments.html', context)

@login_required
def vet_cattle_records(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'vet':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    breed_filter = request.GET.get('breed', '')
    
    cattle = Cattle.objects.all()
    
    if search_query:
        cattle = cattle.filter(
            Q(tag_number__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(farm__farm_name__icontains=search_query)
        )
    
    if status_filter:
        cattle = cattle.filter(vaccination_status=status_filter)
    
    if breed_filter:
        cattle = cattle.filter(breed=breed_filter)
    
    for animal in cattle:
        animal.vaccinations_count = animal.vaccinations.count()
        last_vax = animal.vaccinations.order_by('-vaccination_date').first()
        animal.last_vaccination_date = last_vax.vaccination_date if last_vax else None
    
    context = {
        'cattle': cattle,
        'search_query': search_query,
        'status_filter': status_filter,
        'breed_filter': breed_filter,
        'total_count': cattle.count(),
        'breed_choices': Cattle.BREED_CHOICES,
        'status_choices': Cattle.VACCINATION_STATUS,
    }
    return render(request, 'core/vet_cattle_records.html', context)

@login_required
def vet_cattle_detail(request, cattle_id):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'vet':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    cattle = get_object_or_404(Cattle, id=cattle_id)
    vaccinations = VaccinationRecord.objects.filter(cattle=cattle).order_by('-vaccination_date')
    
    qr_data = f"CATTLE:{cattle.tag_number}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    booster = ReminderSchedule.objects.filter(
        vaccination__cattle=cattle,
        completed=False
    ).first()
    
    context = {
        'cattle': cattle,
        'vaccinations': vaccinations,
        'qr_base64': qr_base64,
        'booster': booster,
    }
    return render(request, 'core/vet_cattle_detail.html', context)

@login_required
def vet_perform_vaccination(request, cattle_id=None):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'vet':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        cattle_id = request.POST.get('cattle_id')
        batch_id = request.POST.get('vaccine_batch')
        dose_number = int(request.POST.get('dose_number'))
        vaccination_date = request.POST.get('vaccination_date')
        adverse_reaction = request.POST.get('adverse_reaction', '')
        
        try:
            cattle = Cattle.objects.get(id=cattle_id)
            batch = VaccineBatch.objects.get(id=batch_id)
            
            if batch.expiry_date < date.today():
                messages.error(request, 'Vaccine batch has expired!')
            elif batch.status == 'cold_chain_breach':
                messages.error(request, 'Cold chain breach detected for this batch!')
            elif batch.quantity_remaining <= 0:
                messages.error(request, 'Insufficient vaccine doses remaining!')
            else:
                VaccinationRecord.objects.create(
                    cattle=cattle,
                    vaccine_batch=batch,
                    vet=profile,
                    dose_number=dose_number,
                    vaccination_date=vaccination_date,
                    gps_latitude=0,
                    gps_longitude=0,
                    adverse_reaction=adverse_reaction
                )
                
                messages.success(request, f'✓ Vaccination recorded for {cattle.tag_number} (Dose {dose_number})')
                
                appointment_id = request.POST.get('appointment_id')
                if appointment_id:
                    try:
                        appointment = VetAppointment.objects.get(id=appointment_id)
                        appointment.status = 'completed'
                        appointment.save()
                    except:
                        pass
                
                return redirect('vet_dashboard')
        except Exception as e:
            messages.error(request, str(e))
    
    all_cattle = Cattle.objects.all()
    batches = VaccineBatch.objects.filter(
        status='in_storage',
        expiry_date__gt=date.today(),
        quantity_remaining__gt=0
    )
    
    context = {
        'all_cattle': all_cattle,
        'batches': batches,
        'selected_cattle': cattle_id,
        'today': date.today().isoformat(),
    }
    return render(request, 'core/vet_vaccinate.html', context)

@login_required
def vet_reports(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'vet':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        vaccinations = VaccinationRecord.objects.filter(
            vet=profile,
            vaccination_date__range=[start, end]
        )
    else:
        vaccinations = VaccinationRecord.objects.filter(vet=profile)
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
    
    total_vaccinations = vaccinations.count()
    dose1_count = vaccinations.filter(dose_number=1).count()
    dose2_count = vaccinations.filter(dose_number=2).count()
    
    monthly_stats = {}
    for vax in vaccinations:
        month_key = vax.vaccination_date.strftime('%Y-%m')
        if month_key not in monthly_stats:
            monthly_stats[month_key] = 0
        monthly_stats[month_key] += 1
    
    context = {
        'total_vaccinations': total_vaccinations,
        'dose1_count': dose1_count,
        'dose2_count': dose2_count,
        'monthly_stats': monthly_stats,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'core/vet_reports.html', context)

@login_required
def vet_batch_tracking(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'vet':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    batches = VaccineBatch.objects.all().order_by('-arrival_date')
    return render(request, 'core/vet_batch_tracking.html', {'batches': batches})

# ============ APPOINTMENT MANAGEMENT ============

@login_required
def vet_directory(request):
    vets = UserProfile.objects.filter(role='vet')
    return render(request, 'core/vet_directory.html', {'vets': vets})

@login_required
def book_appointment(request, vet_id):
    vet = get_object_or_404(UserProfile, id=vet_id, role='vet')
    profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        appointment_date = request.POST.get('appointment_date')
        cattle_id = request.POST.get('cattle')
        notes = request.POST.get('notes', '')
        
        VetAppointment.objects.create(
            farmer=profile,
            vet=vet,
            cattle_id=cattle_id if cattle_id else None,
            appointment_date=appointment_date,
            notes=notes
        )
        messages.success(request, f'Appointment requested with Dr. {vet.user.get_full_name()}')
        return redirect('dashboard')
    
    farms = Farm.objects.filter(farmer=profile)
    cattle = Cattle.objects.filter(farm__in=farms)
    
    return render(request, 'core/book_appointment.html', {'vet': vet, 'cattle': cattle})

@login_required
def my_appointments(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role == 'farmer':
        appointments = VetAppointment.objects.filter(farmer=profile).order_by('-appointment_date')
    elif profile.role == 'vet':
        appointments = VetAppointment.objects.filter(vet=profile).order_by('-appointment_date')
    else:
        appointments = VetAppointment.objects.all().order_by('-appointment_date')
    
    return render(request, 'core/appointments.html', {'appointments': appointments})

@login_required
def update_appointment(request, appointment_id):
    appointment = get_object_or_404(VetAppointment, id=appointment_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        appointment.status = status
        appointment.save()
        messages.success(request, f'Appointment {status}')
    
    return redirect('my_appointments')

# ============ EXPORTER DASHBOARD ============

@login_required
def exporter_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'exporter':
        messages.error(request, 'Access denied. Exporter only.')
        return redirect('dashboard')
    
    eligible_cattle = Cattle.objects.filter(vaccination_status='fully')
    certificates = ExportCertificate.objects.filter(exporter=profile).order_by('-issue_date')
    
    this_month = date.today().replace(day=1)
    monthly_exports = certificates.filter(issue_date__gte=this_month).count()
    
    context = {
        'profile': profile,
        'eligible_cattle': eligible_cattle,
        'eligible_count': eligible_cattle.count(),
        'certificates': certificates[:10],
        'total_certificates': certificates.count(),
        'monthly_exports': monthly_exports,
    }
    return render(request, 'core/exporter_dashboard.html', context)

@login_required
def exporter_export_cattle(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'exporter':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        cattle_ids = request.POST.getlist('cattle_ids')
        cattle_list = Cattle.objects.filter(id__in=cattle_ids)
        
        all_compliant = True
        non_compliant_list = []
        
        for cattle in cattle_list:
            vaccinations = VaccinationRecord.objects.filter(cattle=cattle)
            has_dose1 = vaccinations.filter(dose_number=1).exists()
            has_dose2 = vaccinations.filter(dose_number=2).exists()
            
            if not (has_dose1 and has_dose2):
                all_compliant = False
                non_compliant_list.append(cattle.tag_number)
        
        if all_compliant and cattle_list.exists():
            for cattle in cattle_list:
                ExportCertificate.objects.create(
                    cattle=cattle,
                    exporter=profile,
                    expiry_date=date.today() + timedelta(days=365),
                    is_compliant=True
                )
            messages.success(request, f'Export certificates generated for {cattle_list.count()} cattle!')
            return redirect('exporter_certificates')
        else:
            messages.error(request, f'Non-compliant cattle: {", ".join(non_compliant_list)}')
    
    cattle = Cattle.objects.filter(vaccination_status='fully')
    return render(request, 'core/exporter_export.html', {'cattle': cattle})

@login_required
def exporter_certificates(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'exporter':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    certificates = ExportCertificate.objects.filter(exporter=profile).order_by('-issue_date')
    return render(request, 'core/exporter_certificates.html', {'certificates': certificates})

# ============ GOVERNMENT OFFICIAL DASHBOARD ============

@login_required
def official_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'official':
        messages.error(request, 'Access denied. Government Official only.')
        return redirect('dashboard')
    
    total_cattle = Cattle.objects.count()
    fully_vaccinated = Cattle.objects.filter(vaccination_status='fully').count()
    partially_vaccinated = Cattle.objects.filter(vaccination_status='partial').count()
    unvaccinated = Cattle.objects.filter(vaccination_status='unvaccinated').count()
    national_rate = round((fully_vaccinated / total_cattle * 100) if total_cattle > 0 else 0)
    
    provinces = Farm.objects.values('province').annotate(
        total=Count('cattle'),
        vaccinated=Count('cattle', filter=Q(cattle__vaccination_status='fully')),
        partial=Count('cattle', filter=Q(cattle__vaccination_status='partial')),
        farms=Count('id', distinct=True)
    )
    
    for p in provinces:
        p['rate'] = round((p['vaccinated'] / p['total'] * 100) if p['total'] > 0 else 0)
    
    active_alerts = DiseaseAlert.objects.filter(is_active=True).count()
    recent_alerts = DiseaseAlert.objects.filter(is_active=True).order_by('-date_reported')[:5]
    low_stock_batches = VaccineBatch.objects.filter(quantity_remaining__lt=5000, status='in_storage')
    recent_breaches = ColdChainLog.objects.filter(is_breach=True).order_by('-timestamp')[:5]
    
    context = {
        'profile': profile,
        'total_cattle': total_cattle,
        'fully_vaccinated': fully_vaccinated,
        'partially_vaccinated': partially_vaccinated,
        'unvaccinated': unvaccinated,
        'national_rate': national_rate,
        'provinces': provinces,
        'active_alerts': active_alerts,
        'recent_alerts': recent_alerts,
        'low_stock_batches': low_stock_batches,
        'recent_breaches': recent_breaches,
    }
    return render(request, 'core/official_dashboard.html', context)

@login_required
def official_reports(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'official':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        vaccinations = VaccinationRecord.objects.filter(vaccination_date__range=[start, end])
    else:
        vaccinations = VaccinationRecord.objects.all()
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
    
    report_data = {
        'total_vaccinations': vaccinations.count(),
        'dose1_count': vaccinations.filter(dose_number=1).count(),
        'dose2_count': vaccinations.filter(dose_number=2).count(),
        'total_farms': Farm.objects.count(),
        'total_cattle': Cattle.objects.count(),
        'fully_vaccinated': Cattle.objects.filter(vaccination_status='fully').count(),
        'active_alerts': DiseaseAlert.objects.filter(is_active=True).count(),
    }
    
    context = {
        'report_data': report_data,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'core/official_reports.html', context)

@login_required
def official_manage_alerts(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'official':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        disease_type = request.POST.get('disease_type')
        location = request.POST.get('location')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        radius_km = request.POST.get('radius_km', 30)
        severity = request.POST.get('severity')
        
        alert = DiseaseAlert.objects.create(
            title=title,
            description=description,
            disease_type=disease_type,
            location=location,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            severity=severity,
            reported_by=profile,
            is_active=True
        )
        messages.success(request, f'Disease alert "{alert.title}" issued!')
        return redirect('official_dashboard')
    
    alerts = DiseaseAlert.objects.all().order_by('-date_reported')
    return render(request, 'core/official_manage_alerts.html', {'alerts': alerts})

@login_required
def official_under_vaccinated(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'official':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    under_vaccinated = Farm.objects.values('province', 'district').annotate(
        total=Count('cattle'),
        vaccinated=Count('cattle', filter=Q(cattle__vaccination_status='fully'))
    ).filter(total__gt=0)
    
    under_vaccinated_zones = []
    for zone in under_vaccinated:
        rate = (zone['vaccinated'] / zone['total'] * 100) if zone['total'] > 0 else 0
        if rate < 50:
            under_vaccinated_zones.append({
                'province': zone['province'],
                'district': zone['district'],
                'total': zone['total'],
                'vaccinated': zone['vaccinated'],
                'rate': round(rate, 1)
            })
    
    return render(request, 'core/official_under_vaccinated.html', {'zones': under_vaccinated_zones})

# ============ DISTRIBUTOR DASHBOARD ============

@login_required
def distributor_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'distributor':
        messages.error(request, 'Access denied. Distributor only.')
        return redirect('dashboard')
    
    batches = VaccineBatch.objects.all().order_by('-arrival_date')
    total_doses = batches.aggregate(total=Sum('quantity_remaining'))['total'] or 0
    total_batches = batches.count()
    expiring_soon = batches.filter(expiry_date__lte=date.today() + timedelta(days=90)).count()
    low_stock_batches = batches.filter(quantity_remaining__lt=5000, status='in_storage')
    recent_breaches = ColdChainLog.objects.filter(is_breach=True).order_by('-timestamp')[:5]
    
    context = {
        'profile': profile,
        'batches': batches[:10],
        'total_doses': total_doses,
        'total_batches': total_batches,
        'expiring_soon': expiring_soon,
        'low_stock_batches': low_stock_batches,
        'low_stock_count': low_stock_batches.count(),
        'recent_breaches': recent_breaches,
    }
    return render(request, 'core/distributor_dashboard.html', context)

@login_required
def distributor_batch_management(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'distributor':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    batches = VaccineBatch.objects.all().order_by('-arrival_date')
    
    if request.method == 'POST':
        batch_id = request.POST.get('batch_id')
        new_status = request.POST.get('status')
        new_location = request.POST.get('storage_location')
        
        try:
            batch = VaccineBatch.objects.get(id=batch_id)
            batch.status = new_status
            if new_location:
                batch.storage_location = new_location
            batch.save()
            messages.success(request, f'Batch {batch.batch_number} updated!')
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('distributor_batch_management')
    
    return render(request, 'core/distributor_batch_management.html', {'batches': batches})

@login_required
def distributor_cold_chain(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'distributor':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        batch_id = request.POST.get('batch')
        temperature = float(request.POST.get('temperature'))
        location = request.POST.get('location')
        
        batch = VaccineBatch.objects.get(id=batch_id)
        log = ColdChainLog.objects.create(
            batch=batch,
            temperature=temperature,
            location=location
        )
        
        if log.is_breach:
            messages.warning(request, f'⚠️ Cold chain breach detected for batch {batch.batch_number}!')
        else:
            messages.success(request, 'Temperature recorded successfully.')
        
        return redirect('distributor_cold_chain')
    
    batches = VaccineBatch.objects.all()
    logs = ColdChainLog.objects.all().order_by('-timestamp')[:50]
    
    return render(request, 'core/distributor_cold_chain.html', {'batches': batches, 'logs': logs})

@login_required
def distributor_stock_alerts(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'distributor':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    low_stock_batches = VaccineBatch.objects.filter(
        quantity_remaining__lt=5000, status='in_storage'
    )
    expiring_batches = VaccineBatch.objects.filter(
        expiry_date__lte=date.today() + timedelta(days=90), status='in_storage'
    )
    
    context = {
        'low_stock_batches': low_stock_batches,
        'expiring_batches': expiring_batches,
    }
    return render(request, 'core/distributor_stock_alerts.html', context)

# ============ INSPECTOR DASHBOARD ============

@login_required
def inspector_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'inspector':
        messages.error(request, 'Access denied. Inspector only.')
        return redirect('dashboard')
    
    total_cattle = Cattle.objects.count()
    fully_vaccinated = Cattle.objects.filter(vaccination_status='fully').count()
    partially_vaccinated = Cattle.objects.filter(vaccination_status='partial').count()
    unvaccinated = Cattle.objects.filter(vaccination_status='unvaccinated').count()
    
    cattle_with_issues = Cattle.objects.filter(
        Q(vaccination_status='unvaccinated') | Q(vaccination_status='partial')
    )[:10]
    
    cold_chain_breaches = ColdChainLog.objects.filter(is_breach=True).count()
    
    context = {
        'profile': profile,
        'total_cattle': total_cattle,
        'fully_vaccinated': fully_vaccinated,
        'partially_vaccinated': partially_vaccinated,
        'unvaccinated': unvaccinated,
        'vaccination_rate': round((fully_vaccinated / total_cattle * 100) if total_cattle > 0 else 0),
        'cattle_with_issues': cattle_with_issues,
        'cold_chain_breaches': cold_chain_breaches,
    }
    return render(request, 'core/inspector_dashboard.html', context)

@login_required
def inspector_verify_cattle(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'inspector':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    verification_result = None
    cattle = None
    
    if request.method == 'POST':
        tag_number = request.POST.get('tag_number')
        
        try:
            cattle = Cattle.objects.get(tag_number=tag_number)
            vaccinations = VaccinationRecord.objects.filter(cattle=cattle)
            has_dose1 = vaccinations.filter(dose_number=1).exists()
            has_dose2 = vaccinations.filter(dose_number=2).exists()
            
            if has_dose1 and has_dose2:
                verification_result = 'compliant'
            elif has_dose1:
                verification_result = 'partial'
            else:
                verification_result = 'non_compliant'
                
        except Cattle.DoesNotExist:
            messages.error(request, 'Cattle not found!')
    
    return render(request, 'core/inspector_verify_cattle.html', {
        'cattle': cattle,
        'verification_result': verification_result
    })

@login_required
def inspector_verify_batch(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'inspector':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    batch = None
    issues = []
    
    if request.method == 'POST':
        batch_number = request.POST.get('batch_number')
        
        try:
            batch = VaccineBatch.objects.get(batch_number=batch_number)
            
            if batch.status == 'cold_chain_breach':
                issues.append('Cold chain breach detected')
            if batch.expiry_date <= date.today():
                issues.append('Batch has expired')
            if batch.quantity_remaining <= 0:
                issues.append('No doses remaining')
                
        except VaccineBatch.DoesNotExist:
            messages.error(request, 'Batch not found!')
    
    return render(request, 'core/inspector_verify_batch.html', {
        'batch': batch,
        'issues': issues
    })

def disease_map_view(request):
    """Interactive map showing affected areas and vaccination status"""
    
    import folium
    from folium import plugins
    
    # Create base map centered on South Africa
    m = folium.Map(
        location=[-28.0, 24.0],
        zoom_start=5,
        tiles='OpenStreetMap'
    )
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(m)
    
    # ============ DISEASE OUTBREAK ZONES ============
    disease_alerts = DiseaseAlert.objects.filter(is_active=True)
    
    for alert in disease_alerts:
        try:
            # Get radius based on severity
            if alert.severity == 'critical':
                radius = 50000
                color = '#8B0000'
            elif alert.severity == 'high':
                radius = 30000
                color = '#FF0000'
            elif alert.severity == 'medium':
                radius = 20000
                color = '#FF6600'
            else:
                radius = 10000
                color = '#FFAA00'
            
            # Create popup text
            popup_text = f"""
                <b>⚠️ {alert.get_disease_type_display()}</b><br>
                <b>Location:</b> {alert.location}<br>
                <b>Severity:</b> {alert.get_severity_display()}<br>
                <b>Reported:</b> {alert.date_reported.strftime('%Y-%m-%d') if alert.date_reported else 'Unknown'}<br>
                <b>Alert:</b> {alert.title}
            """
            
            # Add circle to map
            folium.Circle(
                radius=radius,
                location=[float(alert.latitude), float(alert.longitude)],
                popup=popup_text,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.3,
                weight=3,
            ).add_to(m)
            
            # Add marker at center
            folium.Marker(
                location=[float(alert.latitude), float(alert.longitude)],
                popup=f"""
                    <b>🔥 OUTBREAK</b><br>
                    {alert.location}<br>
                    <span style="color: red;">⚠️ Keep cattle away</span>
                """,
                icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa')
            ).add_to(m)
        except Exception as e:
            print(f"Error adding outbreak: {e}")
    
    # ============ FARMS BY VACCINATION STATUS ============
    # Get all farms with cattle counts
    farms = Farm.objects.all()
    
    green_farms = []
    orange_farms = []
    red_farms = []
    
    for farm in farms:
        try:
            # Get cattle count for this farm
            cattle_count = Cattle.objects.filter(farm=farm).count()
            
            if cattle_count > 0:
                # Get vaccinated count
                vaccinated_count = Cattle.objects.filter(
                    farm=farm, 
                    vaccination_status='fully'
                ).count()
                
                vax_rate = (vaccinated_count / cattle_count) * 100
                
                # Skip if no GPS coordinates
                if not farm.gps_latitude or not farm.gps_longitude:
                    continue
                
                if vax_rate >= 80:
                    green_farms.append({
                        'farm': farm,
                        'cattle_count': cattle_count,
                        'vaccinated_count': vaccinated_count,
                        'vax_rate': vax_rate
                    })
                elif vax_rate >= 50:
                    orange_farms.append({
                        'farm': farm,
                        'cattle_count': cattle_count,
                        'vaccinated_count': vaccinated_count,
                        'vax_rate': vax_rate
                    })
                else:
                    red_farms.append({
                        'farm': farm,
                        'cattle_count': cattle_count,
                        'vaccinated_count': vaccinated_count,
                        'vax_rate': vax_rate
                    })
        except Exception as e:
            print(f"Error processing farm {farm.farm_name}: {e}")
    
    # Add green farms (well vaccinated)
    for farm_data in green_farms:
        farm = farm_data['farm']
        popup_text = f"""
            <div style="min-width: 200px;">
                <b>🏠 {farm.farm_name}</b><br>
                <b>📍 Location:</b> {farm.province}, {farm.district}<br>
                <b>📊 Status:</b> ✅ WELL VACCINATED<br>
                <hr>
                <b>🐄 Total Cattle:</b> {farm_data['cattle_count']}<br>
                <b>✅ Vaccinated:</b> {farm_data['vaccinated_count']} ({farm_data['vax_rate']:.1f}%)<br>
                <b>👨‍🌾 Farmer:</b> {farm.farmer.user.get_full_name() if farm.farmer.user else 'Unknown'}<br>
            </div>
        """
        
        folium.CircleMarker(
            radius=10,
            location=[float(farm.gps_latitude), float(farm.gps_longitude)],
            popup=popup_text,
            color='#2ecc71',
            fill=True,
            fill_color='#2ecc71',
            fill_opacity=0.7,
            weight=3,
        ).add_to(m)
    
    # Add orange farms (partially vaccinated)
    for farm_data in orange_farms:
        farm = farm_data['farm']
        popup_text = f"""
            <div style="min-width: 200px;">
                <b>🏠 {farm.farm_name}</b><br>
                <b>📍 Location:</b> {farm.province}, {farm.district}<br>
                <b>📊 Status:</b> ⚠️ PARTIALLY VACCINATED<br>
                <hr>
                <b>🐄 Total Cattle:</b> {farm_data['cattle_count']}<br>
                <b>✅ Vaccinated:</b> {farm_data['vaccinated_count']} ({farm_data['vax_rate']:.1f}%)<br>
                <b>👨‍🌾 Farmer:</b> {farm.farmer.user.get_full_name() if farm.farmer.user else 'Unknown'}<br>
            </div>
        """
        
        folium.CircleMarker(
            radius=10,
            location=[float(farm.gps_latitude), float(farm.gps_longitude)],
            popup=popup_text,
            color='#f39c12',
            fill=True,
            fill_color='#f39c12',
            fill_opacity=0.7,
            weight=3,
        ).add_to(m)
    
    # Add red farms (low vaccination - high risk)
    for farm_data in red_farms:
        farm = farm_data['farm']
        popup_text = f"""
            <div style="min-width: 200px;">
                <b>🏠 {farm.farm_name}</b><br>
                <b>📍 Location:</b> {farm.province}, {farm.district}<br>
                <b>📊 Status:</b> 🔴 LOW VACCINATION - HIGH RISK<br>
                <hr>
                <b>🐄 Total Cattle:</b> {farm_data['cattle_count']}<br>
                <b>✅ Vaccinated:</b> {farm_data['vaccinated_count']} ({farm_data['vax_rate']:.1f}%)<br>
                <b>👨‍🌾 Farmer:</b> {farm.farmer.user.get_full_name() if farm.farmer.user else 'Unknown'}<br>
            </div>
        """
        
        folium.CircleMarker(
            radius=12,
            location=[float(farm.gps_latitude), float(farm.gps_longitude)],
            popup=popup_text,
            color='#e74c3c',
            fill=True,
            fill_color='#e74c3c',
            fill_opacity=0.7,
            weight=3,
        ).add_to(m)
    
    # ============ HEATMAP ============
    heat_data = []
    for farm_data in green_farms + orange_farms + red_farms:
        farm = farm_data['farm']
        if farm.gps_latitude and farm.gps_longitude:
            # Higher intensity for better vaccinated areas
            intensity = farm_data['vax_rate'] / 100
            heat_data.append([float(farm.gps_latitude), float(farm.gps_longitude), intensity])
    
    if heat_data:
        plugins.HeatMap(
            heat_data,
            radius=25,
            blur=15,
            min_opacity=0.3
        ).add_to(m)
    
    # ============ LEGEND ============
    legend_html = '''
    <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; 
                background: white; padding: 15px; border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 12px;
                min-width: 180px;">
        <b style="font-size: 14px;">📊 Map Legend</b><br>
        <hr style="margin: 5px 0;">
        <div style="margin: 5px 0;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: #2ecc71; border-radius: 50%; margin-right: 8px;"></span>
            ✅ Well Vaccinated (80%+)
        </div>
        <div style="margin: 5px 0;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: #f39c12; border-radius: 50%; margin-right: 8px;"></span>
            ⚠️ Partially Vaccinated (50-80%)
        </div>
        <div style="margin: 5px 0;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: #e74c3c; border-radius: 50%; margin-right: 8px;"></span>
            🔴 Low Vaccination (&lt;50%)
        </div>
        <div style="margin: 5px 0;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: #ff0000; border-radius: 50%; margin-right: 8px;"></span>
            🔥 Disease Outbreak Zone
        </div>
        <hr style="margin: 5px 0;">
        <div style="font-size: 10px; color: gray;">
            <i class="fas fa-info-circle"></i> Click markers for details
        </div>
    </div>
    '''
    
    from folium import Element
    m.get_root().html.add_child(Element(legend_html))
    
    # Convert map to HTML
    map_html = m._repr_html_()
    
    # Calculate statistics
    total_farms = farms.count()
    outbreak_count = disease_alerts.count()
    total_cattle = Cattle.objects.count()
    fully_vaccinated = Cattle.objects.filter(vaccination_status='fully').count()
    national_rate = (fully_vaccinated / total_cattle * 100) if total_cattle > 0 else 0
    
    context = {
        'map_html': map_html,
        'total_farms': total_farms,
        'outbreak_count': outbreak_count,
        'national_rate': round(national_rate, 1),
        'total_cattle': total_cattle,
        'fully_vaccinated': fully_vaccinated,
    }
    
    return render(request, 'core/disease_map.html', context)
# ============ NATIONAL PROGRESS ============

@login_required
def national_progress(request):
    total_cattle = Cattle.objects.count()
    fully_vaccinated = Cattle.objects.filter(vaccination_status='fully').count()
    partially_vaccinated = Cattle.objects.filter(vaccination_status='partial').count()
    unvaccinated = Cattle.objects.filter(vaccination_status='unvaccinated').count()
    
    national_rate = round((fully_vaccinated / total_cattle * 100) if total_cattle > 0 else 0)
    target_80_percent = total_cattle * 0.8
    remaining_to_target = max(0, target_80_percent - fully_vaccinated)
    
    provinces = Farm.objects.values('province').annotate(
        total=Count('cattle'),
        vaccinated=Count('cattle', filter=Q(cattle__vaccination_status='fully')),
        partial=Count('cattle', filter=Q(cattle__vaccination_status='partial'))
    )
    
    for p in provinces:
        p['rate'] = round((p['vaccinated'] / p['total'] * 100) if p['total'] > 0 else 0)
    
    last_8_weeks = []
    for i in range(7, -1, -1):
        week_date = date.today() - timedelta(days=i*7)
        week_vaccinations = VaccinationRecord.objects.filter(
            vaccination_date__gte=week_date,
            vaccination_date__lt=week_date + timedelta(days=7)
        ).count()
        last_8_weeks.append({
            'week': week_date.strftime('W%W'),
            'count': week_vaccinations
        })
    
    context = {
        'total_cattle': total_cattle,
        'fully_vaccinated': fully_vaccinated,
        'partially_vaccinated': partially_vaccinated,
        'unvaccinated': unvaccinated,
        'national_rate': national_rate,
        'remaining_to_target': int(remaining_to_target),
        'provinces': provinces,
        'weekly_data': json.dumps(last_8_weeks),
    }
    return render(request, 'core/national_progress.html', context)


# ============ OFFLINE SMS ============

@login_required
def offline_sms_instructions(request):
    return render(request, 'core/offline_sms.html')

def receive_sms(request):
    if request.method == 'POST':
        sender = request.POST.get('from')
        message = request.POST.get('text')
        
        parts = message.strip().split()
        
        if parts[0].upper() == 'VAC' and len(parts) >= 4:
            try:
                tag_number = parts[1]
                batch_number = parts[2]
                dose = int(parts[3])
                vax_date = parts[4] if len(parts) > 4 else date.today().isoformat()
                
                cattle = Cattle.objects.get(tag_number=tag_number)
                batch = VaccineBatch.objects.get(batch_number=batch_number)
                
                VaccinationRecord.objects.create(
                    cattle=cattle,
                    vaccine_batch=batch,
                    dose_number=dose,
                    vaccination_date=vax_date,
                    gps_latitude=0,
                    gps_longitude=0
                )
                
                return HttpResponse("Vaccination recorded", status=200)
            except Exception as e:
                return HttpResponse(f"Error: {str(e)}", status=400)
        
        return HttpResponse("Invalid format. Use: VAC [Tag] [Batch] [Dose] [Date]", status=400)
    
    return JsonResponse({'status': 'SMS gateway ready'})