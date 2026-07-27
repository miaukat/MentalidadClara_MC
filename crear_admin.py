import os
import django

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracion_mentalidad.settings')
django.setup()

from django.contrib.auth.models import User
from mentalidad_app.models import PerfilUsuario  # 👈 Usamos tu modelo real

USERNAME = os.environ.get("ADMIN_USER", "admin")
EMAIL = os.environ.get("ADMIN_EMAIL", "correo@example.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD")

if PASSWORD:
    # 1. Creamos o actualizamos el superusuario de Django
    usuario, creado = User.objects.get_or_create(username=USERNAME, defaults={'email': EMAIL})
    usuario.set_password(PASSWORD)
    usuario.is_superuser = True
    usuario.is_staff = True
    usuario.save()

    # 2. Creamos o actualizamos su PerfilUsuario asegurando el rol 'ADMIN'
    perfil, perfil_creado = PerfilUsuario.objects.get_or_create(usuario=usuario)
    perfil.rol = 'ADMIN'  # 👈 Asignamos el rol correcto de administrador
    perfil.save()

    if creado or perfil_creado:
        print(f"✅ ¡Superusuario y Perfil ADMIN creados con éxito para '{USERNAME}'!")
    else:
        print(f"🔄 ¡Superusuario y Perfil ADMIN actualizados correctamente para '{USERNAME}'!")