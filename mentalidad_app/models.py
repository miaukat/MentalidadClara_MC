import os
from django.db import models
from django.contrib.auth.models import User

class PerfilUsuario(models.Model):
    ROLES = (
        ('PACIENTE', 'Paciente'),
        ('TERAPEUTA', 'Terapeuta'),
        ('ADMIN', 'Administrador'),
    )

    # 🔹 Opciones para el campo de Especialidad
    OPCIONES_ESPECIALIDAD = (
        ('Psicología Infantil', 'Psicología Infantil'),
        ('Psicología Clínica', 'Psicología Clínica'),
        ('Terapia Cognitivo-Conductual', 'Terapia Cognitivo-Conductual'),
        ('Terapia Familiar y de Pareja', 'Terapia Familiar y de Pareja'),
        ('Neuropsicología', 'Neuropsicología'),
        ('Psicopedagogía', 'Psicopedagogía'),
        ('Psicoterapia Humanista', 'Psicoterapia Humanista'),
        ('Psicología Educativa', 'Psicología Educativa'),
    )

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROLES, default='PACIENTE')
    activo = models.BooleanField(default=True)  # Para suspender o activar cuentas (Admin)
    telefono = models.CharField(max_length=15, blank=True, null=True)


    terapeuta_asignado = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='pacientes_asignados', limit_choices_to={'perfil__rol': 'TERAPEUTA'}
    )

    terapeutas_favoritos = models.ManyToManyField(
        User, blank=True, related_name='favoritado_por', limit_choices_to={'perfil__rol': 'TERAPEUTA'}
    )

    # 🔒 PIN de 6 dígitos del diario personal
    pin_diario = models.CharField(max_length=6, blank=True, null=True)

    # 🌟 CAMPOS EXISTENTES Y NUEVOS
    especialidad = models.CharField(
        max_length=100, 
        choices=OPCIONES_ESPECIALIDAD, 
        blank=True, 
        null=True
    )
    fecha_nacimiento = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.usuario.username
    

class ReporteModeracion(models.Model):
    """Modelo para que queden registradas las notas o reportes sobre un terapeuta"""
    administrador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reportes_creados')
    usuario_reportado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reportes_recibidos')
    motivo = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reporte sobre {self.usuario_reportado.username} por {self.administrador.username if self.administrador else 'Sistema'}"

class ReporteComportamientoPaciente(models.Model):
    TIPOS_COMPORTAMIENTO = (
        ('Falta de Asistencia / Incumplimiento', 'Falta de Asistencia / Incumplimiento'),
        ('Resistencia al Tratamiento', 'Resistencia al Tratamiento'),
        ('Conducta Disruptiva o Inapropiada', 'Conducta Disruptiva o Inapropiada'),
        ('Incumplimiento de Actividades', 'Incumplimiento de Actividades'),
        ('Otro', 'Otro'),
    )

    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reportes_emitidos')
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reportes_comportamiento')
    tipo_comportamiento = models.CharField(max_length=100, choices=TIPOS_COMPORTAMIENTO)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reporte de {self.terapeuta.username} sobre {self.paciente.username} - {self.tipo_comportamiento}"


class ConfiguracionSistema(models.Model):
    """Modelo global para el interruptor de mantenimiento de la web"""
    sistema_en_mantenimiento = models.BooleanField(default=False)
    mensaje_mantenimiento = models.TextField(default="Estamos actualizando Mentalidad Clara para ti. Vuelve pronto.")

    def __str__(self):
        return "Configuración General del Sistema"




#TERAPEUTA
class HorarioDisponible(models.Model):
    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='horarios')
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr(a). {self.terapeuta.username} — {self.fecha}"


#PACIENTE - TERAPEUTA
class Cita(models.Model):
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas_paciente')
    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas_terapeuta')
    horario = models.ForeignKey(HorarioDisponible, on_delete=models.CASCADE)
    motivo = models.TextField()
    estado = models.CharField(max_length=20, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cita de {self.paciente.username} con {self.terapeuta.username}"


class RegistroEmocional(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_emocionales')
    emocion = models.CharField(max_length=50)
    intensidad = models.IntegerField(default=5)
    comentario = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    EMOJI_MAP = {
        'alegre': '😊',
        'tranquilo': '😌',
        'motivado': '✨',
        'cansado': '😴',
        'ansioso': '😰',
        'triste': '😢',
        'frustrado': '😤',
    }

    def __str__(self):
        return f"{self.usuario.username} - {self.emocion}"

    @property
    def emoji(self):
        clave = str(self.emocion).lower().strip()
        return self.EMOJI_MAP.get(clave, '😊')

class DiarioPersonal(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entradas_diario')
    titulo = models.CharField(max_length=100)
    contenido = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diario de {self.usuario.username} - {self.titulo}"


class Actividad(models.Model):
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actividades_creadas', limit_choices_to={'perfil__rol': 'TERAPEUTA'}, null=True, blank=True)
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actividades_asignadas', null=True, blank=True) # 👈 Agrégalo aquí
    fecha_creacion = models.DateTimeField(auto_now_add=True) # 👈 Asegúrate de tener también este de fecha
    completada = models.BooleanField(default=False)

    def __str__(self):
        return self.titulo

class MensajeChat(models.Model):
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados')
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_recibidos')
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    def __str__(self):
        return f"De {self.remitente.username} a {self.destinatario.username}: {self.texto[:20]}"
    
#TERAPEUTA
class DisponibilidadTerapeuta(models.Model):
    DIAS_SEMANA = [
        ('LUN', 'Lunes'),
        ('MAR', 'Martes'),
        ('MIE', 'Miércoles'),
        ('JUE', 'Jueves'),
        ('VIE', 'Viernes'),
        ('SAB', 'Sábado'),
        ('DOM', 'Domingo'),
    ]
    
    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disponibilidades')
    dia = models.CharField(max_length=3, choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    def __str__(self):
        return f"{self.terapeuta.username} - {self.get_dia_display()} ({self.hora_inicio} a {self.hora_fin})"

from django.db import models
from django.contrib.auth.models import User

class ActividadEmocional(models.Model):
    EMOCIONES_CHOICES = [
        ('FELIZ', 'Feliz / Motivado'),
        ('ANSIOSO', 'Ansioso / Preocupado'),
        ('FRUSTRADO', 'Frustrado / Incomodo'),
        ('TRISTE', 'Triste / Desanimado'),
        ('ESTRESADO', 'Estresado / Saturado'),
        ('NEUTRAL', 'Neutral / Tranquilo'),
    ]

    terapeuta = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='actividades_emocionales_creadas'
    )
    paciente = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='actividades_emocionales_asignadas', 
        limit_choices_to={'perfil__rol': 'PACIENTE'}
    )
    
    emocion_objetivo = models.CharField(
        max_length=20, 
        choices=EMOCIONES_CHOICES, 
        default='ANSIOSO',
        blank=True, 
        null=True
    )
    intensidad = models.IntegerField(default=5, help_text="Nivel de intensidad de 1 a 10")
    motivo_emocion = models.TextField(blank=True, null=True, help_text="Por qué se sentía así el paciente")
    
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    completada = models.BooleanField(default=False)

    def __str__(self):
        emocion_display = self.get_emocion_objetivo_display() if self.emocion_objetivo else "Sin emoción"
        return f"{self.titulo} - {emocion_display} (Intensidad: {self.intensidad})"


class NotaClinica(models.Model):
    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notas_creadas')
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notas_recibidas')
    contenido = models.TextField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Nota de {self.terapeuta.username} para {self.paciente.username}"


