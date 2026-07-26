"""
URL configuration for configuracion_mentalidad project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from mentalidad_app.views import (
    home, registro_usuario, login_usuario, logout_usuario,
    recuperar_password, restablecer_password,
    dashboard_paciente, registrar_emocion_diario, agendar_cita, mis_actividades
)
from mentalidad_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ── ENTRADA DIRECTA ──
    # Si quieres que abra el login directamente al entrar a http://127.0.0.1:8000/:
    path('', home, name='home'),
    
    # O si prefieres que abra el dashboard del paciente directamente:
    # path('', dashboard_paciente, name='home'),

    # ── Autenticación ──
    path('registro/', registro_usuario, name='registro'),
    path('login/', login_usuario, name='login'),
    path('logout/', logout_usuario, name='logout'),
    path('recuperar-password/', recuperar_password, name='recuperar_password'),
    path('restablecer-password/', restablecer_password, name='restablecer_password'),
    
    # ── Rutas del Paciente ──
    path('dashboard/', dashboard_paciente, name='dashboard_paciente'),
    path('diario/', views.diario_personal, name='diario_personal'),
    path('diario/verificar/', views.verificar_pin_diario, name='verificar_pin_diario'),
    path('emociones/', registrar_emocion_diario, name='registrar_emocion_diario'),
    path('mi-historial/', views.historial_emociones, name='historial_emociones'),
    path('citas/', agendar_cita, name='agendar_cita'),
    path('actividades/', mis_actividades, name='mis_actividades'),
    path('agendar-cita/', views.agendar_cita, name='agendar_cita'),
    path('citas/confirmar/<int:horario_id>/', views.confirmar_cita, name='confirmar_cita'),
    path('terapeuta/<int:terapeuta_id>/favorito/', views.toggle_favorito_terapeuta, name='toggle_favorito'),
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('citas/cancelar/<int:cita_id>/', views.cancelar_cita, name='cancelar_cita'),
    path('mi-terapeuta/', views.ver_terapeuta_asignado, name='terapeuta_asignado'),
    path('terapeuta/paciente/<int:paciente_id>/', views.ver_perfil_paciente, name='ver_perfil_paciente'),

    # ── Rutas del Terapeuta ──
    path('terapeuta/dashboard/', views.dashboard_terapeuta, name='dashboard_terapeuta'),
    path('terapeuta/horarios/', views.gestionar_horarios_terapeuta, name='gestionar_horarios_terapeuta'),
    path('terapeuta/pacientes-disponibles/', views.ver_pacientes_disponibles, name='ver_pacientes_disponibles'),
    path('terapeuta/asignar-paciente/<int:paciente_id>/', views.asignar_paciente, name='asignar_paciente'),
    path('terapeuta/detalle-paciente/<int:paciente_id>/', views.detalle_paciente_terapeuta, name='detalle_paciente_terapeuta'),
    path('terapeuta/paciente/<int:paciente_id>/registro-emocional/', views.ver_registro_emocional_paciente, name='ver_registro_emocional_paciente'),
    path('terapeuta/crear-actividad/', views.crear_actividad_terapeuta, name='crear_actividad_terapeuta'),
    path('terapeuta/horarios/categoria/<str:categoria>/', views.detalle_horarios_categoria, name='detalle_horarios_categoria'),
    path('terapeuta/horarios/eliminar/<int:horario_id>/', views.eliminar_horario_terapeuta, name='eliminar_horario_terapeuta'),
    path('terapeuta/horarios/eliminar/<int:horario_id>/', views.eliminar_horario_terapeuta, name='eliminar_horario_terapeuta'),
    path('citas/aceptar/<int:cita_id>/', views.terapeuta_aceptar_cita, name='terapeuta_aceptar_cita'),
    path('citas/rechazar/<int:cita_id>/', views.terapeuta_rechazar_cita, name='terapeuta_rechazar_cita'),
    path('terapeuta/paciente/<int:paciente_id>/crear-reporte/', views.crear_reporte_comportamiento, name='crear_reporte_comportamiento'),
    path('enviar-mensaje-terapeuta/', views.enviar_mensaje_terapeuta, name='enviar_mensaje_terapeuta'),
    path('terapeuta/enviar-mensaje/', views.enviar_mensaje_terapeuta, name='enviar_mensaje_chat'),

    # ── Rutas Exclusivas del Administrador de la Clínica ──
    path('acceso-seguro-gerencia-mc/dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('acceso-seguro-gerencia-mc/crear-terapeuta/', views.crear_terapeuta_admin, name='crear_terapeuta_admin'),
    path('acceso-seguro-gerencia-mc/suspender/<int:user_id>/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('acceso-seguro-gerencia-mc/mantenimiento/', views.toggle_mantenimiento, name='toggle_mantenimiento'),
    path('acceso-seguro-gerencia-mc/pacientes/', views.listar_pacientes_admin, name='admin_listar_pacientes'),

    
]