import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracion_mentalidad.settings')
django.setup()

from django.contrib.auth.models import User

USERNAME = os.environ.get("ADMIN_USER", "admin")
EMAIL = os.environ.get("ADMIN_EMAIL", "correo_por_defecto@example.com") 
PASSWORD = os.environ.get("ADMIN_PASSWORD")

if PASSWORD and not User.objects.filter(username=USERNAME).exists():
    User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
    print(f"✅ ¡Superusuario '{USERNAME}' creado con éxito!")