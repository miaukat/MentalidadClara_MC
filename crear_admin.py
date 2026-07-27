import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracion_mentalidad.settings')
django.setup()

from django.contrib.auth.models import User

# Lee los datos de forma segura desde las variables del servidor
USERNAME = os.environ.get("ADMIN_USER", "admin")
EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD")

if PASSWORD and not User.objects.filter(username=USERNAME).exists():
    User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
    print(f"✅ ¡Superusuario '{USERNAME}' creado con éxito!")