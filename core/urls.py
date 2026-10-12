from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('alerts/', views.alerts, name='alerts'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('vet/register/', views.vet_register, name='vet_register'),  # NEW: Vet registration
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Farm management
    path('farms/', views.my_farms, name='my_farms'),
    path('farms/add/', views.add_farm, name='add_farm'),
    path('my-farms/', views.my_farms, name='my_farms_alt'),
    
    # Cattle management
    path('cattle/', views.my_cattle, name='my_cattle'),
    path('my-cattle/', views.my_cattle, name='my_cattle_alt'),
    path('cattle/add/', views.add_cattle, name='add_cattle'),
    path('add-cattle/', views.add_cattle, name='add_cattle_alt'),
    path('cattle/<int:cattle_id>/', views.vet_cattle_detail, name='cattle_detail'),
    
    # Vaccine management
    path('batches/', views.vaccine_batches, name='vaccine_batches'),
    path('batches/add/', views.add_vaccine_batch, name='add_batch'),
    path('cold-chain/', views.cold_chain_monitoring, name='cold_chain'),
    
    # Vaccination
    path('vaccination/record/', views.record_vaccination, name='record_vaccination'),
    path('vaccination/history/', views.vaccination_history, name='vaccination_history'),
    path('reminders/', views.reminders, name='reminders'),
    
    # QR Verification
    path('qr-verification/', views.qr_verification, name='qr_verification'),
    path('api/verify/<str:qr_data>/', views.verify_qr_api, name='verify_qr'),
    
    # Export certificates
    path('export/', views.export_certificate_generator, name='export_certificate'),
    path('certificate/download/<int:cert_id>/', views.download_certificate, name='download_certificate'),
    
    # Vet dashboard
    path('vet/dashboard/', views.vet_dashboard, name='vet_dashboard'),
    path('vet/appointments/', views.vet_appointments, name='vet_appointments'),
    path('vet/vaccinate/', views.vet_perform_vaccination, name='vet_vaccinate'),
    path('vet/vaccinate/<int:cattle_id>/', views.vet_perform_vaccination, name='vet_vaccinate_cattle'),
    path('vet/cattle/', views.vet_cattle_records, name='vet_cattle_records'),
    path('vet/cattle/<int:cattle_id>/', views.vet_cattle_detail, name='vet_cattle_detail'),
    path('vet/reports/', views.vet_reports, name='vet_reports'),
    path('vet/batches/', views.vet_batch_tracking, name='vet_batch_tracking'),
    
    # Appointments
    path('vet-directory/', views.vet_directory, name='vet_directory'),
    path('appointment/book/<int:vet_id>/', views.book_appointment, name='book_appointment'),
    path('appointments/', views.my_appointments, name='appointments'),
    path('appointment/update/<int:appointment_id>/', views.update_appointment, name='update_appointment'),
    
    # National progress
    path('national-progress/', views.national_progress, name='national_progress'),
    
    # Offline SMS
    path('offline-sms/', views.offline_sms_instructions, name='offline_sms'),
    path('api/sms-webhook/', views.receive_sms, name='sms_webhook'),

    # Add these to your urlpatterns list:

    # Exporter URLs
    path('exporter/dashboard/', views.exporter_dashboard, name='exporter_dashboard'),
    path('exporter/export/', views.exporter_export_cattle, name='exporter_export'),
    path('exporter/certificates/', views.exporter_certificates, name='exporter_certificates'),
    
    # Government Official URLs
    path('official/dashboard/', views.official_dashboard, name='official_dashboard'),
    path('official/reports/', views.official_reports, name='official_reports'),
    path('official/manage-alerts/', views.official_manage_alerts, name='official_manage_alerts'),
    path('official/under-vaccinated/', views.official_under_vaccinated, name='official_under_vaccinated'),
    
    # Distributor URLs
    path('distributor/dashboard/', views.distributor_dashboard, name='distributor_dashboard'),
    path('distributor/batches/', views.distributor_batch_management, name='distributor_batch_management'),
    path('distributor/cold-chain/', views.distributor_cold_chain, name='distributor_cold_chain'),
    path('distributor/stock-alerts/', views.distributor_stock_alerts, name='distributor_stock_alerts'),
    
    # Inspector URLs
    path('inspector/dashboard/', views.inspector_dashboard, name='inspector_dashboard'),
    path('inspector/verify-cattle/', views.inspector_verify_cattle, name='inspector_verify_cattle'),
    path('inspector/verify-batch/', views.inspector_verify_batch, name='inspector_verify_batch'),

    path('disease-map/', views.disease_map_view, name='disease_map'),
]