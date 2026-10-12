\# UGCINO - Protecting Our Future



A livestock traceability and vaccination management system for South Africa.



\## Features

\- Multi-role authentication (Farmer, Vet, Official, Distributor, Exporter, Inspector)

\- Cattle registration with QR codes

\- Vaccination records with duplicate prevention

\- Vaccine batch cold chain monitoring

\- Interactive disease outbreak map

\- Export certificate generation (PDF with QR verification)

\- National vaccination progress dashboard

\- Offline SMS-based data capture



\## Technology Stack

| Layer | Technology |

|-------|-----------|

| Backend | Django 5.0.2 |

| Database (Dev) | SQLite 3 |

| Database (Prod) | PostgreSQL |

| Frontend | Tailwind CSS |

| Mapping | Folium, Leaflet.js |

| PDF | ReportLab |

| QR Codes | qrcode |



\## Installation



```bash

git clone https://github.com/thando-alt/ugcino.git

cd ugcino



python -m venv venv

venv\\Scripts\\activate        # Windows

source venv/bin/activate      # Mac/Linux



pip install -r requirements.txt



\# Configure PostgreSQL in ugcino/settings.py



python manage.py migrate

python manage.py createsuperuser

python manage.py runserver

