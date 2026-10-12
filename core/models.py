from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('farmer', 'Farmer'),
        ('vet', 'Veterinarian'),
        ('official', 'Government Official'),
        ('distributor', 'Distributor'),
        ('exporter', 'Exporter'),
        ('inspector', 'Inspector'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='farmer')
    phone_number = models.CharField(max_length=15)
    id_number = models.CharField(max_length=20, blank=True)
    province = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    practice_number = models.CharField(max_length=50, blank=True, help_text="For veterinarians")
    company_name = models.CharField(max_length=100, blank=True, help_text="For distributors/exporters")
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"

class Farm(models.Model):
    farmer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='farms', limit_choices_to={'role': 'farmer'})
    farm_name = models.CharField(max_length=100)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=6)
    gps_longitude = models.DecimalField(max_digits=10, decimal_places=6)
    province = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, help_text="Hectares")
    owner_contact = models.CharField(max_length=15)
    registration_number = models.CharField(max_length=50, unique=True, blank=True)
    qr_code = models.ImageField(upload_to='qrcodes/farms/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.registration_number:
            self.registration_number = f"FARM{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)
        # Generate QR code
        if not self.qr_code:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"FARM:{self.registration_number}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            self.qr_code.save(f"farm_{self.registration_number}.png", File(buffer), save=True)
    
    def __str__(self):
        return self.farm_name

class Cattle(models.Model):
    BREED_CHOICES = [
        ('brahman', 'Brahman'),
        ('angus', 'Angus Beef'),
        ('hereford', 'Hereford'),
        ('holstein', 'Holstein Friesian'),
        ('jersey', 'Jersey'),
        ('sahiwal', 'Sahiwal'),
        ('other', 'Other'),
    ]
    
    SEX_CHOICES = [('M', 'Male'), ('F', 'Female')]
    VACCINATION_STATUS = [
        ('unvaccinated', 'Unvaccinated'),
        ('partial', 'Partially Vaccinated (Dose 1)'),
        ('fully', 'Fully Vaccinated'),
    ]
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='cattle')
    tag_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50, blank=True)
    breed = models.CharField(max_length=20, choices=BREED_CHOICES)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    date_of_birth = models.DateField()
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    vaccination_status = models.CharField(max_length=20, choices=VACCINATION_STATUS, default='unvaccinated')
    qr_code = models.ImageField(upload_to='qrcodes/cattle/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def age_months(self):
        today = timezone.now().date()
        months = (today.year - self.date_of_birth.year) * 12
        months += today.month - self.date_of_birth.month
        return months
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Generate QR code
        if not self.qr_code:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"CATTLE:{self.tag_number}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            self.qr_code.save(f"cattle_{self.tag_number}.png", File(buffer), save=True)
    
    def __str__(self):
        return f"{self.tag_number} - {self.farm.farm_name}"

class VaccineBatch(models.Model):
    STATUS_CHOICES = [
        ('in_storage', 'In Storage'),
        ('distributed', 'Distributed'),
        ('cold_chain_breach', 'Cold Chain Breach'),
        ('expired', 'Expired'),
        ('depleted', 'Depleted'),
    ]
    
    batch_number = models.CharField(max_length=50, unique=True)
    manufacturer = models.CharField(max_length=100)
    country_of_origin = models.CharField(max_length=50)
    quantity = models.IntegerField()
    quantity_remaining = models.IntegerField()
    production_date = models.DateField()
    expiry_date = models.DateField()
    arrival_date = models.DateField(auto_now_add=True)
    storage_location = models.CharField(max_length=200)
    storage_temperature = models.DecimalField(max_digits=4, decimal_places=1, default=5.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_storage')
    qr_code = models.ImageField(upload_to='qrcodes/batches/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.pk:
            self.quantity_remaining = self.quantity
        super().save(*args, **kwargs)
        if not self.qr_code:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"BATCH:{self.batch_number}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            self.qr_code.save(f"batch_{self.batch_number}.png", File(buffer), save=True)
    
    def __str__(self):
        return f"{self.batch_number} - {self.quantity_remaining}/{self.quantity} doses"

class ColdChainLog(models.Model):
    batch = models.ForeignKey(VaccineBatch, on_delete=models.CASCADE, related_name='temperature_logs')
    temperature = models.DecimalField(max_digits=4, decimal_places=1)
    timestamp = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=200)
    is_breach = models.BooleanField(default=False)
    breach_duration_minutes = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        # Check temperature breach (2-8°C is acceptable range)
        if self.temperature < 2 or self.temperature > 8:
            self.is_breach = True
            self.batch.status = 'cold_chain_breach'
            self.batch.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.batch.batch_number} - {self.temperature}°C at {self.timestamp}"

class VaccinationRecord(models.Model):
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_batch = models.ForeignKey(VaccineBatch, on_delete=models.CASCADE)
    vet = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'vet'})
    dose_number = models.IntegerField(choices=[(1, 'Dose 1'), (2, 'Dose 2')])
    vaccination_date = models.DateField()
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=6)
    gps_longitude = models.DecimalField(max_digits=10, decimal_places=6)
    adverse_reaction = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Check for duplicate
        existing = VaccinationRecord.objects.filter(
            cattle=self.cattle, dose_number=self.dose_number
        ).first()
        if existing:
            raise ValueError(f"Dose {self.dose_number} already recorded for this animal")
        
        # Update batch inventory
        if self.vaccine_batch.quantity_remaining <= 0:
            raise ValueError("Insufficient vaccine doses")
        
        self.vaccine_batch.quantity_remaining -= 1
        if self.vaccine_batch.quantity_remaining == 0:
            self.vaccine_batch.status = 'depleted'
        self.vaccine_batch.save()
        
        # Update cattle status
        if self.dose_number == 1:
            self.cattle.vaccination_status = 'partial'
        else:
            self.cattle.vaccination_status = 'fully'
        self.cattle.save()
        
        super().save(*args, **kwargs)
        
        # Schedule booster for dose 1
        if self.dose_number == 1:
            ReminderSchedule.objects.create(
                vaccination=self,
                due_date=self.vaccination_date + timedelta(days=21)
            )
    
    def __str__(self):
        return f"{self.cattle.tag_number} - Dose {self.dose_number} on {self.vaccination_date}"

class ReminderSchedule(models.Model):
    vaccination = models.ForeignKey(VaccinationRecord, on_delete=models.CASCADE, related_name='reminders')
    due_date = models.DateField()
    sent_to_farmer = models.BooleanField(default=False)
    sent_to_vet = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DiseaseAlert(models.Model):
    SEVERITY_CHOICES = [
        ('critical', 'Critical - Immediate Action'),
        ('high', 'High - Urgent'),
        ('medium', 'Medium - Caution'),
        ('low', 'Low - Monitor'),
    ]
    
    DISEASE_TYPES = [
        ('fmd', 'Foot and Mouth Disease'),
        ('lumpy_skin', 'Lumpy Skin Disease'),
        ('rabies', 'Rabies'),
        ('anthrax', 'Anthrax'),
        ('brucellosis', 'Brucellosis'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    disease_type = models.CharField(max_length=50, choices=DISEASE_TYPES)
    location = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    radius_km = models.IntegerField(default=30)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    reported_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    date_reported = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.get_disease_type_display()} - {self.location}"

class ExportCertificate(models.Model):
    certificate_number = models.CharField(max_length=50, unique=True)
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='certificates')
    exporter = models.ForeignKey(UserProfile, on_delete=models.CASCADE, limit_choices_to={'role': 'exporter'})
    issue_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_compliant = models.BooleanField(default=False)
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='certificates/qrcodes/', blank=True, null=True)
    verification_code = models.CharField(max_length=100, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = f"EXP{timezone.now().strftime('%Y%m%d%H%M%S')}"
        if not self.verification_code:
            import uuid
            self.verification_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Certificate {self.certificate_number} - {self.cattle.tag_number}"

class OfflineRecord(models.Model):
    farmer = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    sms_data = models.TextField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Offline record from {self.farmer} at {self.created_at}"

class StockAlert(models.Model):
    batch = models.ForeignKey(VaccineBatch, on_delete=models.CASCADE)
    threshold = models.IntegerField(default=5000)
    alert_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Stock alert for {self.batch.batch_number}"

class VetAppointment(models.Model):
    farmer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='appointments_as_farmer')
    vet = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='appointments_as_vet', limit_choices_to={'role': 'vet'})
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, null=True, blank=True)
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Appointment: {self.farmer} with {self.vet} on {self.appointment_date}"