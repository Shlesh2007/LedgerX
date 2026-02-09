# LedgerX
Here is a professional README.md for your deployment repository, tailored to reflect the configuration found in your project files and including your live site link.

LedgerX - Smart Digital Credit Ledger (Deployment)
LedgerX is a smart digital credit ledger designed for local shops to manage customers, track sales, and monitor credit transactions efficiently. This repository contains the deployment-ready version of the application, optimized for hosting on Render.com.

Live Demo: https://ledgerx-deploy.onrender.com

🚀 Key Features
Customer Management: Add and manage customer credit profiles with real-time balance tracking.

Inventory & Products: Manage a digital catalog of products with image support powered by Cloudinary.

Transaction Tracking: Detailed logging of sales and payments for every customer.

Digital Reports: Visual dashboards and generated reports for sales, products, and customer trends.

QR Code Payments: Integrated payment bridge and customer-specific QR codes for easy access to ledger details.

Automated Communication: Transactional email notifications via Brevo API.

🛠️ Tech Stack
Backend: Django 6.0.

Database: PostgreSQL (configured via dj-database-url).

Media Hosting: Cloudinary.

Static Asset Management: WhiteNoise.

Email Engine: Brevo (Sendinblue).

Deployment Platform: Render.com.

📋 Prerequisites
Python 3.10+.

A Cloudinary account for media storage.

A Brevo API Key for transactional emails.

A PostgreSQL instance (Render provides managed databases).

⚙️ Setup and Installation
Clone the Repository:

Bash
git clone https://github.com/shlesh2007/ledgerx-deploy.git
cd LedgerX-Deploy
Environment Configuration: Create a .env file in the project root and provide the following variables:

Code snippet
SECRET_KEY=your_production_secret_key
DEBUG=False
DATABASE_URL=your_postgresql_url
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
BREVO_API_KEY=your_brevo_api_key
DEFAULT_FROM_EMAIL=your_verified_email@example.com
Install Dependencies:

Bash
pip install -r requirements.txt
Database Migration:

Bash
python manage.py migrate
Run Locally:

Bash
python manage.py runserver
📂 Project Structure
accounts/: Shop profile management and authentication.

customers/: Customer data and credit history logic.

products/: Inventory management with Cloudinary integration.

sales/: Transaction processing for sales and payments.

reports/: Data visualization and analytics dashboards.

qr/: QR code generation and payment bridging tools.

Developed to empower local businesses with smart digital tools.
