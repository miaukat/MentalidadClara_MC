from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from .models import PerfilUsuario, RegistroEmocional, DiarioPersonal, HorarioDisponible, Cita, MensajeChat, NotaClinica, ReporteComportamientoPaciente
from .models import Cita
from django.utils.crypto import get_random_string
from .models import PerfilUsuario, ConfiguracionSistema, ReporteModeracion
from .models import DisponibilidadTerapeuta
from.models import ActividadEmocional
from django.http import HttpResponseForbidden
from django.contrib import messages
from .models import HorarioDisponible, Cita
from django.utils import timezone
from django.conf import settings
from mentalidad_app.models import Cita
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import calendar
from django.db.models import Q
import json
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import resend
from django.template.loader import render_to_string


def home(request):
    return render(request, 'mentalidad_app/home.html')

def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil'):
            if request.user.perfil.rol == 'TERAPEUTA':
                return redirect('dashboard_terapeuta')
            elif request.user.perfil.rol == 'PACIENTE':
                return redirect('dashboard_paciente')
            elif request.user.perfil.rol == 'ADMIN':
                return redirect('dashboard_admin')
    
    return render(request, 'mentalidad_app/home.html')

#COMPARTIDOS
def registro_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        nombre = request.POST.get('first_name')
        apellido = request.POST.get('last_name')
        telefono = request.POST.get('telefono', '')

        # 1 Validar si el nombre de usuario ya existe
        if User.objects.filter(username=username).exists():
            return render(request, 'mentalidad_app/compartidos/registro.html', {
                'error': 'El nombre de usuario ya está registrado. Por favor elige otro.'
            })

        # 2 Validar si el correo electrónico ya está registrado (Correo Único)
        if User.objects.filter(email=email).exists():
            return render(request, 'mentalidad_app/compartidos/registro.html', {
                'error': 'Este correo electrónico ya está asociado a otra cuenta.'
            })

        # 3 Validar que la contraseña sea segura usando las reglas de Django
        try:
            validate_password(password)
        except ValidationError as e:
            # e.messages contiene la lista de razones por las cuales la contraseña no es segura
            return render(request, 'mentalidad_app/compartidos/registro.html', {
                'error': " ".join(e.messages)
            })

        # Si todo es correcto, creamos el usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=nombre,
            last_name=apellido
        )

        # Creamos o recuperamos el perfil
        perfil, creado = PerfilUsuario.objects.get_or_create(
            usuario=user,
            defaults={
                'rol': 'PACIENTE',
                'telefono': telefono
            }
        )
        
        if not creado:
            perfil.telefono = telefono
            perfil.rol = 'PACIENTE'
            perfil.save()

        # Envío del correo de bienvenida
        try:
            enviar_correo_bienvenida(user)
        except Exception as e:
            print(f"No se pudo enviar el correo de bienvenida: {e}")

        # Autenticamos e iniciamos sesión inmediatamente
        login(request, user)
        return redirect('dashboard_paciente')

    return render(request, 'mentalidad_app/compartidos/registro.html')


def login_usuario(request):
    if request.method == 'POST':
        identificador = request.POST.get('username') # Recibe lo que el usuario escriba (usuario o correo)
        password = request.POST.get('password')

        user = None
        # Verificamos si lo que escribió contiene un '@' para saber si es un correo electrónico
        if '@' in identificador:
            try:
                # Buscamos al usuario que tenga registrado ese correo
                user_obj = User.objects.get(email=identificador)
                # Si lo encuentra, usamos su nombre de usuario real para autenticar
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None # Si el correo no está registrado, user queda en None
        else:
            # Si no tiene '@', asumimos que ingresó directamente su nombre de usuario
            user = authenticate(request, username=identificador, password=password)

        # Si la autenticación es exitosa
        if user is not None:
            login(request, user)
            
            # Redirección inteligente según el rol del usuario
            if hasattr(user, 'perfil') and user.perfil.rol == 'TERAPEUTA':
                return redirect('dashboard_terapeuta')
            elif hasattr(user, 'perfil') and user.perfil.rol == 'PACIENTE':
                return redirect('dashboard_paciente')
            else:
                return redirect('home')
        else:
            # Si falla, mostramos el mensaje de error en el HTML
            return render(request, 'mentalidad_app/compartidos/login.html', {
                'error': 'Usuario/Correo o contraseña incorrectos.'
            })

    return render(request, 'mentalidad_app/compartidos/login.html')

def logout_usuario(request):
    logout(request)
    return redirect('home')

def recuperar_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        usuarios = User.objects.filter(email=email)

        if usuarios.exists():
            usuario = usuarios.first()
            asunto = "Recuperación de Contraseña - Mentalidad Clara"
            mensaje = f"Hola {usuario.first_name or usuario.username},\n\nHas solicitado restablecer tu contraseña."
            
            send_mail(
                asunto,
                mensaje,
                'mentalidadclara.soporte@gmail.com',
                [email],
                fail_silently=False,
            )
            return render(request, 'mentalidad_app/recuperar_password.html', {
                'mensaje': 'Te hemos enviado un correo con las instrucciones para recuperar tu cuenta.'
            })
        else:
            return render(request, 'mentalidad_app/recuperar_password.html', {
                'error': 'No encontramos ninguna cuenta registrada con este correo electrónico.'
            })

    return render(request, 'mentalidad_app/compartidos/recuperar_password.html')

def restablecer_password(request):
    user_id = request.GET.get('user')
    usuario = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            return render(request, 'mentalidad_app/restablecer_password.html', {
                'error': 'Las contraseñas no coinciden. Por favor inténtalo de nuevo.'
            })

        usuario.set_password(password1)
        usuario.save()

        return render(request, 'mentalidad_app/login.html', {
            'error': '¡Tu contraseña ha sido actualizada con éxito! Ya puedes iniciar sesión.'
        })

    return render(request, 'mentalidad_app/compartidos/restablecer_password.html')


#PACIENTE
@login_required
def dashboard_paciente(request):
    # Verificar que el usuario sea paciente
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'PACIENTE':
        return redirect('home')

    ultimas_emociones = RegistroEmocional.objects.filter(usuario=request.user).order_by('-fecha')[:3]
    proximas_citas = Cita.objects.filter(paciente=request.user, estado='CONFIRMADA').order_by('horario__fecha')
    
    # Actividades que sean solo del paciente logueado
    actividades_pendientes = ActividadEmocional.objects.filter(paciente=request.user, completada=False)

    # Obtenemos al terapeuta asignado a este paciente (si tiene uno)
    terapeuta_asignado = None
    if hasattr(request.user, 'perfil') and request.user.perfil.terapeuta_asignado:
        terapeuta_asignado = request.user.perfil.terapeuta_asignado

    # NUEVO: Obtenemos los mensajes enviados por el terapeuta a este paciente
    mensajes_chat = MensajeChat.objects.filter(destinatario=request.user).order_by('-fecha')
    
    # Opcional: Para saber si hay mensajes sin leer y mostrar el punto rojo
    mensajes_nuevos_pendientes = mensajes_chat.filter(leido=False).exists()

    return render(request, 'mentalidad_app/pacientes/dashboard_paciente.html', {
        'emociones': ultimas_emociones,
        'citas': proximas_citas,
        'actividades': actividades_pendientes,
        'terapeuta_asignado': terapeuta_asignado,
        'mensajes_chat': mensajes_chat,                 # 👈 ¡Agregado aquí!
        'mensajes_nuevos_pendientes': mensajes_nuevos_pendientes, # 👈 ¡Agregado aquí!
    })

@login_required(login_url='login')
def mi_vista_paciente(request):
    terapeuta = None
    mensajes = []
    
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'PACIENTE':
        terapeuta = request.user.perfil.terapeuta_asignado
        if terapeuta:
            # Filtramos los mensajes donde el remitente sea su terapeuta y el destinatario sea el paciente actual
            mensajes = MensajeChat.objects.filter(
                remitente=terapeuta,
                destinatario=request.user
            ).order_by('fecha') # Orden cronológico para que los lea en orden

    contexto = {
        'terapeuta_asignado': terapeuta,
        'mensajes_chat': mensajes,
    }
    return render(request, 'mentalidad_app/paciente/terapeuta_asignado.html', contexto)
@login_required
def ver_terapeuta_asignado(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'PACIENTE':
        return redirect('home')

    terapeuta_asignado = None
    reportes = []
    
    if hasattr(request.user, 'perfil') and request.user.perfil.terapeuta_asignado:
        terapeuta_asignado = request.user.perfil.terapeuta_asignado
        # Buscamos usando el modelo correcto que creaste para el comportamiento del paciente
        reportes = ReporteComportamientoPaciente.objects.filter(
            paciente=request.user, 
            terapeuta=terapeuta_asignado
        ).order_by('-fecha')

    return render(request, 'mentalidad_app/pacientes/terapeuta_asignado.html', {
        'terapeuta_asignado': terapeuta_asignado,
        'reportes': reportes,
    })


@login_required
def registrar_emocion_diario(request):
    if request.method == 'POST':
        tipo_registro = request.POST.get('tipo_registro')

        if tipo_registro == 'EMOCION':
            emocion = request.POST.get('emocion_principal')
            intensidad_raw = request.POST.get('intensidad')
            intensidad = int(intensidad_raw) if intensidad_raw else 5
            comentario = request.POST.get('descripcion', '')

            RegistroEmocional.objects.create(
                usuario=request.user,
                emocion=emocion,
                intensidad=intensidad,
                comentario=comentario
            )
        elif tipo_registro == 'DIARIO':
            titulo = request.POST.get('titulo')
            contenido = request.POST.get('contenido')

            DiarioPersonal.objects.create(
                usuario=request.user,
                titulo=titulo,
                contenido=contenido
            )

        return redirect('historial_emociones')

    emociones_historial = RegistroEmocional.objects.filter(usuario=request.user).order_by('-fecha')
    diarios_historial = DiarioPersonal.objects.filter(usuario=request.user).order_by('-fecha')

    return render(request, 'mentalidad_app/pacientes/registro_emocion.html', {
        'emociones': emociones_historial,
        'diarios': diarios_historial
    })


@login_required
def historial_emociones(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'PACIENTE':
        return redirect('home')

    ahora = datetime.now()
    
    # Consulta usando los campos reales de tu modelo
    mis_registros = RegistroEmocional.objects.filter(usuario=request.user).order_by('-fecha')
    
    # Filtro opcional por fecha si la selecciona el usuario
    fecha_filtro = request.GET.get('fecha_filtro')
    if fecha_filtro:
        mis_registros = mis_registros.filter(fecha__date=fecha_filtro)

    total_registros_mes = mis_registros.count()
    
    # Emoción más frecuente
    emocion_mas_frecuente = "Aún sin registros 😌"
    if mis_registros.exists():
        emocion_mas_frecuente = mis_registros.first().emocion

    # 📊 Agrupación para la gráfica
    conteo_emociones = mis_registros.values('emocion').annotate(total=Count('id'))
    chart_labels = [item['emocion'].capitalize() for item in conteo_emociones]
    chart_data = [item['total'] for item in conteo_emociones]

    contexto = {
        'mis_registros': mis_registros,
        'emocion_mas_frecuente': emocion_mas_frecuente,
        'total_registros_mes': total_registros_mes,
        'mes_actual': ahora.strftime('%B %Y'),
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    
    return render(request, 'mentalidad_app/pacientes/historial_emociones.html', contexto)

@login_required
def bloquear_diario(request):
    if 'diario_desbloqueado' in request.session:
        del request.session['diario_desbloqueado']
    return redirect('dashboard_paciente')

@login_required
def diario_personal(request):
    perfil = getattr(request.user, 'perfil', None)
    pin_guardado = perfil.pin_diario if perfil else None
    tiene_pin = bool(pin_guardado)

    # 1. Seguridad: Si tiene PIN y no está desbloqueado en la sesión, lo mandamos a verificar
    if tiene_pin and not request.session.get('diario_desbloqueado', False):
        return redirect('verificar_pin_diario')

    # 2. Acción para guardar o actualizar el PIN de seguridad (con validación de PIN repetido)
    if request.method == 'POST' and 'guardar_pin' in request.POST:
        nuevo_pin = request.POST.get('nuevo_pin')
        
        # Validar que el nuevo PIN no sea idéntico al anterior
        if pin_guardado and nuevo_pin == pin_guardado:
            messages.error(request, 'El nuevo PIN no puede ser igual al PIN anterior. Por favor, elige uno diferente.')
            return redirect('diario_personal')

        if perfil:
            perfil.pin_diario = nuevo_pin
            perfil.save()
            request.session['diario_desbloqueado'] = True
            messages.success(request, '¡PIN de seguridad guardado correctamente!')
        return redirect('diario_personal')

    # 3. Acción para guardar una nueva entrada en el diario
    if request.method == 'POST' and 'guardar_escrito' in request.POST:
        titulo = request.POST.get('titulo')
        contenido = request.POST.get('contenido')
        
        DiarioPersonal.objects.create(
            usuario=request.user,
            titulo=titulo,
            contenido=contenido
        )
        
        messages.success(request, '¡Entrada guardada con éxito!')
        return redirect('diario_personal')

    # 4. Consultar las entradas del usuario autenticado
    entradas = DiarioPersonal.objects.filter(usuario=request.user).order_by('-fecha')

    # 5. Ver una entrada específica al hacer clic en "Entrar y Leer"
    entrada_id = request.GET.get('ver')
    entrada_seleccionada = None
    if entrada_id:
        entrada_seleccionada = get_object_or_404(DiarioPersonal, id=entrada_id, usuario=request.user)

    contexto = {
        'tiene_pin': tiene_pin,
        'entradas': entradas,
        'entrada_seleccionada': entrada_seleccionada,
    }
    return render(request, 'mentalidad_app/pacientes/diario_personal.html', contexto)

@login_required
def verificar_pin_diario(request):
    perfil = getattr(request.user, 'perfil', None)
    pin_guardado = perfil.pin_diario if perfil else None
    
    # Si el usuario NO tiene PIN creado, no tiene sentido estar aquí, lo mandamos directo al diario
    if not pin_guardado:
        return redirect('diario_personal')
        
    # Si ya puso el PIN antes en esta sesión, lo mandamos directo al diario
    if request.session.get('diario_desbloqueado', False):
        return redirect('diario_personal')

    if request.method == 'POST':
        pin_ingresado = request.POST.get('pin_ingresado')
        if pin_ingresado == pin_guardado:
            request.session['diario_desbloqueado'] = True  # Desbloqueamos la sesión
            return redirect('diario_personal')
        else:
            messages.error(request, 'PIN incorrecto. Inténtalo de nuevo.')

    return render(request, 'mentalidad_app/pacientes/verificar_pin_diario.html')

@login_required
def agendar_cita(request):
    perfil_paciente, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)

    # Capturamos los filtros avanzados enviados por POST o GET
    dias_seleccionados = request.GET.getlist('dias')       # Ej: ['Lun', 'Mie', 'Vie']
    rangos_seleccionados = request.GET.getlist('rangos')   # Ej: ['Mañana', 'Tarde']

    # Obtenemos la fecha actual del servidor
    hoy = timezone.now().date()

    # Partimos de los horarios disponibles, filtrando desde hoy en adelante y ordenados de menor a mayor
    horarios_disponibles = HorarioDisponible.objects.filter(
        disponible=True,
        fecha__gte=hoy  # Oculta los días pasados y el día actual (usa fecha__gt si quieres excluir hoy también)
    ).order_by('fecha', 'hora_inicio')

    citas_paciente = Cita.objects.filter(paciente=request.user)
    terapeutas_favoritos = perfil_paciente.terapeutas_favoritos.all()

    context = {
        'horarios': horarios_disponibles,
        'mis_citas': citas_paciente,
        'terapeutas_favoritos': terapeutas_favoritos,
        'dias_activos': dias_seleccionados,
        'rangos_activos': rangos_seleccionados,
    }
    return render(request, 'mentalidad_app/pacientes/agendar_cita.html', context)

def confirmar_cita(request, horario_id):
    horario = get_object_or_404(HorarioDisponible, id=horario_id)
    
    if Cita.objects.filter(horario=horario, estado__in=['CONFIRMADA', 'PENDIENTE']).exists():
        messages.error(request, 'Lo sentimos, este horario ya se encuentra ocupado o tiene una solicitud en proceso.')
        return redirect('agendar_cita')
    
    if request.method == 'POST':
        # Si presionó el botón de rechazar, nos salimos de inmediato sin validar nada
        if 'rechazar' in request.POST:
            return redirect('agendar_cita')
            
        motivo = request.POST.get('motivo', '').strip()
        
        # Validamos que el motivo no esté vacío al confirmar
        if not motivo:
            messages.error(request, 'Por favor, escribe un motivo de consulta para continuar.')
            return render(request, 'mentalidad_app/pacientes/confirmar_cita.html', {'horario': horario})
        
        # Creamos la cita en estado PENDIENTE
        cita = Cita.objects.create(
            paciente=request.user,
            terapeuta=horario.terapeuta,
            horario=horario,
            motivo=motivo,
            estado='PENDIENTE'
        )
        
        messages.success(request, '¡Solicitud enviada! Tu terapeuta revisará la disponibilidad y te notificaremos cuando sea aceptada.')
        return redirect('mis_citas') 
        
    return render(request, 'mentalidad_app/pacientes/confirmar_cita.html', {'horario': horario})

@login_required
def mis_citas(request):
    """Vista para que el paciente vea sus citas agendadas."""
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'PACIENTE':
        return redirect('home')
    
    citas = Cita.objects.filter(paciente=request.user).order_by('horario__fecha', 'horario__hora_inicio')
    return render(request, 'mentalidad_app/pacientes/mis_citas.html', {'citas': citas})


@login_required
def cancelar_cita(request, cita_id):
    """Vista para cancelar o eliminar una cita y liberar el horario."""
    cita = get_object_or_404(Cita, id=cita_id, paciente=request.user)
    
    if request.method == 'POST':
        # Liberamos el horario disponible nuevamente
        horario = cita.horario
        horario.disponible = True
        horario.save()
        
        cita.delete()
        return redirect('mis_citas')
        
    return render(request, 'mentalidad_app/pacientes/confirmar_cancelacion.html', {'cita': cita})

@login_required
def mis_actividades(request):
    if request.method == 'POST':
        actividad_id = request.POST.get('actividad_id')
        actividad = get_object_or_404(ActividadEmocional, id=actividad_id, paciente=request.user)
        actividad.completada = True
        actividad.save()
        return redirect('mis_actividades')

    # Filtramos las actividades emocionales del paciente logueado
    actividades = ActividadEmocional.objects.filter(paciente=request.user).order_by('-fecha_creacion')
    
    return render(request, 'mentalidad_app/pacientes/mis_actividades.html', {
        'actividades': actividades
    })

@login_required
def toggle_favorito_terapeuta(request, terapeuta_id):
    if request.method == 'POST':
        terapeuta_user = get_object_or_404(User, id=terapeuta_id, perfil__rol='TERAPEUTA')
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)

        if terapeuta_user in perfil.terapeutas_favoritos.all():
            perfil.terapeutas_favoritos.remove(terapeuta_user)
            es_favorito = False
        else:
            perfil.terapeutas_favoritos.add(terapeuta_user)
            es_favorito = True

        return JsonResponse({'status': 'success', 'es_favorito': es_favorito})
    
    return JsonResponse({'status': 'error'}, status=400)

#ADMINISTRADOR
@login_required
def dashboard_admin(request):
    # Si es superusuario de Django o tiene rol ADMIN, lo dejamos pasar
    if not request.user.is_superuser:
        if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
            return redirect('home')

    terapeutas = User.objects.filter(perfil__rol='TERAPEUTA')
    total_terapeutas = terapeutas.count()

    # 🔍 Obtenemos los reportes de comportamiento emitidos por los terapeutas
    reportes = ReporteComportamientoPaciente.objects.all().order_by('-fecha')

    contexto = {
        'terapeutas': terapeutas,
        'total_terapeutas': total_terapeutas,
        'reportes': reportes,
    }
    return render(request, 'mentalidad_app/admin/dashboard_admin.html', contexto)

from django.contrib import messages  # Asegúrate de importar messages si lo usas
@login_required
def crear_terapeuta_admin(request):
    """Crea un terapeuta, le genera contraseña y se la envía al correo"""
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        username = request.POST.get('username')
        
        especialidad = request.POST.get('especialidad')
        fecha_nacimiento = request.POST.get('fecha_nacimiento')

        # 🔍 Validación: Verificar si el username ya existe (ESTRICTO Y ÚNICO)
        if User.objects.filter(username=username).exists():
            return render(request, 'mentalidad_app/admin/crear_terapeuta.html', {
                'error': f'El nombre de usuario "{username}" ya está en uso. Por favor, elige uno diferente.'
            })

        # Generar una contraseña aleatoria fuerte de 10 caracteres (¡NECESARIO!)
        password_temporal = get_random_string(length=10)

        # Crear el usuario base en Django
        nuevo_usuario = User.objects.create_user(
            username=username,
            email=email,
            first_name=nombre,
            last_name=apellido,
            password=password_temporal
        )

        # Asignar perfil de Terapeuta
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=nuevo_usuario)
        perfil.rol = 'TERAPEUTA'
        perfil.activo = True
        perfil.especialidad = especialidad
        perfil.fecha_nacimiento = fecha_nacimiento if fecha_nacimiento else None
        perfil.save()

        # Configurar correo electrónico con las credenciales en texto plano por si acaso
        asunto = 'Bienvenido a Mentalidad Clara - Credenciales de Acceso'
        
        contexto_email = {
            'usuario': nuevo_usuario,
            'nombre': nombre,
            'apellido': apellido,
            'username': username,
            'password': password_temporal, 
            'especialidad': especialidad,
        }

        # 🛠️ TODO ESTE BLOQUE AHORA SÍ ESTÁ DENTRO DEL POST Y DEBIDAMENTE INDENTADO
        try:
            resend.api_key = settings.RESEND_API_KEY
            mensaje_html = render_to_string('emails/bienvenida_terapeuta.html', contexto_email)
            
            params = {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": ["penarodriguezednakaterine@gmail.com"],
                "subject": asunto,
                "html": mensaje_html,  
            }
            resend.Emails.send(params)
            print("✅ Correo de terapeuta enviado con éxito mediante la API de Resend")
        except Exception as e:
            print(f"Error al enviar correo: {e}")

        # Redirección al dashboard solo cuando termine de procesar el formulario POST
        return redirect('dashboard_admin')

    return render(request, 'mentalidad_app/admin/crear_terapeuta.html')

@login_required
def cambiar_estado_usuario(request, user_id):
    """Suspende o activa a un usuario (paciente o terapeuta)"""
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    usuario_objetivo = get_object_or_404(User, id=user_id)
    perfil = usuario_objetivo.perfil
    perfil.activo = not perfil.activo  # Alterna entre True y False
    perfil.save()
    return redirect('dashboard_admin')


@login_required
def toggle_mantenimiento(request):
    """Activa o desactiva el modo mantenimiento global de la web"""
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    config, _ = ConfiguracionSistema.objects.get_or_create(id=1)
    config.sistema_en_mantenimiento = not config.sistema_en_mantenimiento
    config.save()
    return redirect('dashboard_admin')

@login_required
def listar_pacientes_admin(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    # 🛠️ Rescate automático para usuarios antiguos que no tengan perfil creado
    for user_obj in User.objects.all():
        if not hasattr(user_obj, 'perfil') and not user_obj.is_staff and not user_obj.is_superuser:
            PerfilUsuario.objects.create(usuario=user_obj, rol='PACIENTE')

    # Usamos select_related para traer el terapeuta asignado junto con el perfil y evitar consultas extra
    pacientes = PerfilUsuario.objects.filter(rol='PACIENTE').select_related('terapeuta_asignado')
    total_pacientes = pacientes.count() 

    contexto = {
        'pacientes': pacientes,
        'total_pacientes': total_pacientes,
    }
    return render(request, 'mentalidad_app/admin/listar_pacientes.html', contexto)

#TERAPEUTA

@login_required(login_url='login')
def dashboard_terapeuta(request):
    # Verificamos si tiene perfil y rol de terapeuta
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'TERAPEUTA':
        return HttpResponseForbidden("Acceso denegado: No tienes permisos de terapeuta.")
    
    mis_pacientes = PerfilUsuario.objects.filter(rol='PACIENTE', terapeuta_asignado=request.user)
    
    # Buscamos las citas pendientes del terapeuta
    citas_pendientes = Cita.objects.filter(terapeuta=request.user, estado='PENDIENTE').order_by('horario__fecha', 'horario__hora_inicio')

    # CORREGIDO: Usamos 'fecha' en lugar de 'fecha_envio'
    mensajes_enviados = MensajeChat.objects.filter(remitente=request.user).order_by('fecha')

    contexto = {
        'mis_pacientes': mis_pacientes,
        'citas_pendientes': citas_pendientes,
        'pacientes_asignados': mis_pacientes,
        'mensajes_enviados': mensajes_enviados,
    }
    
    return render(request, 'mentalidad_app/terapeuta/dashboard_terapeuta.html', contexto)

@login_required
def enviar_mensaje_terapeuta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            paciente_id = data.get('paciente_id')
            texto_mensaje = data.get('mensaje')
            
            # Opción A: Si en el HTML mandas el id del User (paciente.usuario.id)
            usuario_paciente = User.objects.get(id=paciente_id)
            
            # Guardamos asociando directamente al usuario destinatario
            MensajeChat.objects.create(
                remitente=request.user, 
                destinatario=usuario_paciente, 
                texto=texto_mensaje
            )
            
            return JsonResponse({'status': 'success'})
            
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'El usuario paciente no existe.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

@login_required
def ver_perfil_paciente(request, paciente_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'TERAPEUTA':
        return HttpResponseForbidden("Acceso denegado.")

    # Buscamos el perfil del paciente asegurándonos de que esté asignado a este terapeuta
    paciente = get_object_or_404(PerfilUsuario, id=paciente_id, rol='PACIENTE', terapeuta_asignado=request.user)

    contexto = {
        'paciente': paciente,
    }
    return render(request, 'mentalidad_app/terapeuta/ver_perfil_paciente.html', contexto)

@login_required
def gestionar_horarios_terapeuta(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    if request.method == 'POST':
        dias_seleccionados = request.POST.getlist('dias')     # Ej: ['Mon', 'Wed']
        rangos_seleccionados = request.POST.getlist('rangos') # Ej: ['Mañana', 'Tarde']

        dias_map = {
            'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 
            'Fri': 4, 'Sat': 5, 'Sun': 6
        }

        hoy = datetime.now().date()
        # Generar disponibilidad por 2 semanas (14 días)
        for i in range(14):
            fecha_actual = hoy + timedelta(days=i)
            dia_str_key = [k for k, v in dias_map.items() if v == fecha_actual.weekday()]
            
            if dia_str_key and dia_str_key[0] in dias_seleccionados:
                for rango in rangos_seleccionados:
                    if rango == 'Mañana':
                        hora_inicio, hora_fin = '08:00:00', '12:00:00'
                    elif rango == 'Tarde':
                        hora_inicio, hora_fin = '14:00:00', '18:00:00'
                    elif rango == 'Noche':
                        hora_inicio, hora_fin = '18:00:00', '21:00:00'
                    else:
                        continue

                    HorarioDisponible.objects.get_or_create(
                        terapeuta=request.user,
                        fecha=fecha_actual,
                        hora_inicio=hora_inicio,
                        defaults={
                            'hora_fin': hora_fin,
                            'disponible': True
                        }
                    )

        return redirect('gestionar_horarios_terapeuta')

    # Agrupar los horarios actuales por categoría según la hora de inicio
    horarios = HorarioDisponible.objects.filter(terapeuta=request.user).order_by('fecha', 'hora_inicio')
    
    manana = horarios.filter(hora_inicio__lt='12:00:00')
    tarde = horarios.filter(hora_inicio__gte='12:00:00', hora_inicio__lt='18:00:00')
    noche = horarios.filter(hora_inicio__gte='18:00:00')

    # --- NUEVO: Buscamos las citas pendientes para que aparezcan en esta vista ---
    citas_pendientes = Cita.objects.filter(terapeuta=request.user, estado='PENDIENTE').order_by('horario__fecha', 'horario__hora_inicio')

    return render(request, 'mentalidad_app/terapeuta/gestionar_horarios.html', {
        'manana': manana,
        'tarde': tarde,
        'noche': noche,
        'citas_pendientes': citas_pendientes,  # <-- Agregado al contexto
    })

@login_required
def detalle_horarios_categoria(request, categoria):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    horarios = HorarioDisponible.objects.filter(terapeuta=request.user)
    if categoria == 'manana':
        horarios = horarios.filter(hora_inicio__lt='12:00:00')
        titulo = "Horarios - Categoría Mañana"
    elif categoria == 'tarde':
        horarios = horarios.filter(hora_inicio__gte='12:00:00', hora_inicio__lt='18:00:00')
        titulo = "Horarios - Categoría Tarde"
    elif categoria == 'noche':
        horarios = horarios.filter(hora_inicio__gte='18:00:00')
        titulo = "Horarios - Categoría Noche"
    else:
        return redirect('gestionar_horarios_terapeuta')

    return render(request, 'mentalidad_app/terapeuta/detalle_categoria.html', {
        'horarios': horarios.order_by('fecha', 'hora_inicio'),
        'titulo': titulo
    })

@login_required
def eliminar_horario_terapeuta(request, horario_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    horario = get_object_or_404(HorarioDisponible, id=horario_id, terapeuta=request.user)
    horario.delete()
    return redirect(request.META.get('HTTP_REFERER', 'gestionar_horarios_terapeuta'))

def terapeuta_aceptar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, terapeuta=request.user)
    cita.estado = 'CONFIRMADA'
    cita.save()
    
    # Marcamos el horario como no disponible si tu modelo lo requiere
    cita.horario.disponible = False
    cita.horario.save()

    # ENVÍO DE CORREO AL PACIENTE: ¡Cita aceptada!
    try:
        asunto = "¡Cita Aceptada! - Mentalidad Clara"
        mensaje = (
            f"Hola {cita.paciente.get_full_name() or cita.paciente.username},\n\n"
            f"¡Buenas noticias! El/la Dr(a). {cita.terapeuta.get_full_name() or cita.terapeuta.username} ha aceptado tu solicitud de cita.\n\n"
            f"Detalles de la cita:\n"
            f"- Fecha: {cita.horario.fecha.strftime('%A, %d de %B de %Y')}\n"
            f"- Hora: {cita.horario.hora_inicio.strftime('%I:%M %p')} - {cita.horario.hora_fin.strftime('%I:%M %p')}\n\n"
            f"Te esperamos.\n\n"
            f"Atentamente,\nEquipo de Mentalidad Clara"
        )
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [cita.paciente.email], fail_silently=False)
    except Exception as e:
        print(f"Error al enviar correo: {e}")

    messages.success(request, 'Has aceptado la cita correctamente. Se le ha notificado al paciente.')
    return redirect('dashboard_terapeuta') # Ajusta a la ruta de tu panel de terapeuta


def terapeuta_rechazar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, terapeuta=request.user)
    
    # Guardamos los datos para el correo antes de eliminarla o cambiarla de estado
    paciente_email = cita.paciente.email
    paciente_nombre = cita.paciente.get_full_name() or cita.paciente.username
    terapeuta_nombre = cita.terapeuta.get_full_name() or cita.terapeuta.username
    fecha_cita = cita.horario.fecha
    
    # Cambiamos el estado a RECHAZADA o eliminamos la cita para liberar el horario
    cita.estado = 'RECHAZADA'
    cita.save()
    
    # Opcional: si deseas que el horario vuelva a estar disponible para que otro lo tome
    cita.horario.disponible = True
    cita.horario.save()

    # ENVÍO DE CORREO AL PACIENTE: El terapeuta no puede ese día
    try:
        asunto = "Actualización sobre tu solicitud de cita - Mentalidad Clara"
        mensaje = (
            f"Hola {paciente_nombre},\n\n"
            f"Lamentamos informarte que el/la Dr(a). {terapeuta_nombre} no tiene disponibilidad para atenderte en la fecha solicitada ({fecha_cita.strftime('%d/%m/%Y')}).\n\n"
            f"Te invitamos a ingresar nuevamente a la plataforma para agendar una cita en otro horario disponible.\n\n"
            f"Atentamente,\nEquipo de Mentalidad Clara"
        )
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [paciente_email], fail_silently=False)
    except Exception as e:
        print(f"Error al enviar correo: {e}")

    messages.warning(request, 'Has rechazado la cita. Se le ha notificado al paciente por correo.')
    return redirect('dashboard_terapeuta')

@login_required
def ver_pacientes_disponibles(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    # Pacientes que aún no tienen un terapeuta asignado
    pacientes_libres = PerfilUsuario.objects.filter(rol='PACIENTE', terapeuta_asignado__isnull=True)
    
    # Pacientes que ya están asignados a ESTE terapeuta
    mis_pacientes = PerfilUsuario.objects.filter(rol='PACIENTE', terapeuta_asignado=request.user)

    contexto = {
        'pacientes_libres': pacientes_libres,
        'mis_pacientes': mis_pacientes,
    }
    return render(request, 'mentalidad_app/terapeuta/pacientes_disponibles.html', contexto)

@login_required
def asignar_paciente(request, paciente_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    # Asignamos el paciente logueado actualmente a este terapeuta
    paciente_perfil = get_object_or_404(PerfilUsuario, id=paciente_id, rol='PACIENTE')
    if paciente_perfil.terapeuta_asignado is None:
        paciente_perfil.terapeuta_asignado = request.user
        paciente_perfil.save()
        
    return redirect('ver_pacientes_disponibles')


@login_required
def detalle_paciente_terapeuta(request, paciente_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    paciente_perfil = get_object_or_404(PerfilUsuario, id=paciente_id, rol='PACIENTE', terapeuta_asignado=request.user)
    mis_pacientes = PerfilUsuario.objects.filter(rol='PACIENTE', terapeuta_asignado=request.user)
    hoy = timezone.localtime(timezone.now()).date()

    # Procesar guardado de Notas Clínicas
    nota_obj, _ = NotaClinica.objects.get_or_create(
        terapeuta=request.user, 
        paciente=paciente_perfil.usuario
    )

    if request.method == 'POST' and 'guardar_nota' in request.POST:
        nota_obj.contenido = request.POST.get('contenido_nota', '')
        nota_obj.save()
        return redirect('detalle_paciente_terapeuta', paciente_id=paciente_id)

    # 🟢 CAMBIO AQUÍ: Usamos ActividadEmocional (que es donde tu vista 'crear_actividad_terapeuta' guarda los datos)
    # y traemos todas las de este paciente sin filtrar solo por hoy, ordenadas de la más reciente a la más antigua.
    actividades_hoy = ActividadEmocional.objects.filter(
        paciente=paciente_perfil.usuario,
        terapeuta=request.user
    ).order_by('-fecha_creacion') # Si en ActividadEmocional tu campo de fecha se llama distinto (ej. 'fecha'), cámbialo aquí.

    citas_paciente = Cita.objects.filter(
        paciente=paciente_perfil.usuario,
        terapeuta=request.user
    ).select_related('horario').order_by('horario__fecha', 'horario__hora_inicio')

    contexto = {
        'paciente': paciente_perfil,
        'mis_pacientes': mis_pacientes,
        'actividades_hoy': actividades_hoy, 
        'citas': citas_paciente,
        'nota': nota_obj,
        'hoy': hoy,
    }
    return render(request, 'mentalidad_app/terapeuta/detalle_paciente.html', contexto)

@login_required
def ver_registro_emocional_paciente(request, paciente_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    paciente_perfil = get_object_or_404(PerfilUsuario, id=paciente_id, rol='PACIENTE', terapeuta_asignado=request.user)
    
    fecha_filtro_str = request.GET.get('fecha_registro')
    hoy_date = timezone.localtime(timezone.now()).date()

    if fecha_filtro_str:
        try:
            # Limpiamos espacios y guiones raros que puedan venir de la URL
            fecha_limpia = fecha_filtro_str.strip().replace(' ', '')
            fecha_obj = datetime.strptime(fecha_limpia, '%Y-%m-%d').date()
        except ValueError:
            fecha_obj = hoy_date
    else:
        fecha_obj = hoy_date

    # Forzamos un string limpio y estandarizado para la plantilla (ej: 2026-07-23)
    fecha_seleccionada = fecha_obj.strftime('%Y-%m-%d')

    # Calendario y matrices del mes
    cal = calendar.Calendar(firstweekday=0)
    dias_matriz = cal.monthdayscalendar(fecha_obj.year, fecha_obj.month)
    
    registros_mes_dict = {}
    emojis_mes_dict = {}

    # Mapeo unificado de emojis
    emojis_map = {
        'FELIZ': '😊', 'ALEGRE': '😊',
        'ANSIOSO': '😰',
        'FRUSTRADO': '😣', 'FRUSTRADO': '😤',
        'TRISTE': '😢',
        'ESTRESADO': '🤯',
        'NEUTRAL': '😌', 'TRANQUILO': '😌',
        'MOTIVADO': '✨',
        'CANSADO': '😴',
    }

    # 1. Registros exactos del día seleccionado filtrados por fecha limpia (__date)
    registros_emocionales = RegistroEmocional.objects.filter(
        usuario=paciente_perfil.usuario,
        fecha__date=fecha_obj
    ).order_by('-fecha')

    # 2. Registros de todo el mes para el calendario y la gráfica
    registros_mes = RegistroEmocional.objects.filter(
        usuario=paciente_perfil.usuario,
        fecha__year=fecha_obj.year,
        fecha__month=fecha_obj.month
    ).order_by('fecha')

    for reg in registros_mes:
        fecha_local = timezone.localtime(reg.fecha) if timezone.is_aware(reg.fecha) else reg.fecha
        dia_num = fecha_local.day
        registros_mes_dict[dia_num] = reg
        
        emocion_key = str(reg.emocion).upper().strip()
        emojis_mes_dict[dia_num] = emojis_map.get(emocion_key, '🌱')

    # Estadísticas para gráficos del mes
    stats_emociones = (
        RegistroEmocional.objects.filter(
            usuario=paciente_perfil.usuario,
            fecha__month=fecha_obj.month,
            fecha__year=fecha_obj.year
        )
        .values('emocion')
        .annotate(total=Count('emocion'))
        .order_by('-total')
    )

    etiquetas_emociones = [item['emocion'] for item in stats_emociones]
    conteo_emociones = [item['total'] for item in stats_emociones]

    contexto = {
        'paciente': paciente_perfil,
        'registros_emocionales': registros_emocionales,
        'fecha_seleccionada': fecha_seleccionada,
        'fecha_obj': fecha_obj,
        'dias_matriz': dias_matriz,
        'registros_mes_dict': registros_mes_dict,
        'emojis_mes_dict': emojis_mes_dict,
        'etiquetas_emociones': etiquetas_emociones,
        'conteo_emociones': conteo_emociones,
    }
    return render(request, 'mentalidad_app/terapeuta/registro_emocional_paciente.html', contexto)

@login_required
def crear_actividad_terapeuta(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    pacientes = PerfilUsuario.objects.filter(rol='PACIENTE', terapeuta_asignado=request.user)
    paciente_id = request.GET.get('paciente_id')
    fecha_filtro_str = request.GET.get('fecha_registro')
    
    paciente_seleccionado = None
    registros_emocionales = []
    etiquetas_emociones = []
    conteo_emociones = []
    
    # 1. Fecha seleccionada
    hoy_date = timezone.localtime(timezone.now()).date()
    hoy_str = hoy_date.strftime('%Y-%m-%d')
    fecha_seleccionada = fecha_filtro_str if fecha_filtro_str else hoy_str

    try:
        fecha_obj = datetime.strptime(fecha_seleccionada, '%Y-%m-%d').date()
    except ValueError:
        fecha_obj = hoy_date

    # 2. Generar matriz del calendario para el mes en curso
    cal = calendar.Calendar(firstweekday=0)  # 0 = Lunes
    dias_matriz = cal.monthdayscalendar(fecha_obj.year, fecha_obj.month)
    registros_mes_dict = {}

    if paciente_id:
        paciente_seleccionado = get_object_or_404(PerfilUsuario, id=paciente_id, terapeuta_asignado=request.user)
        
        # Registros del día exacto seleccionado para la tarjeta de abajo
        inicio_dia = timezone.make_aware(datetime.combine(fecha_obj, datetime.min.time()))
        fin_dia = timezone.make_aware(datetime.combine(fecha_obj, datetime.max.time()))

        registros_emocionales = RegistroEmocional.objects.filter(
            usuario=paciente_seleccionado.usuario,
            fecha__range=(inicio_dia, fin_dia)
        ).order_by('-fecha')

        # Registros del mes ordenados ascendentemente
        registros_mes = RegistroEmocional.objects.filter(
            usuario=paciente_seleccionado.usuario,
            fecha__year=fecha_obj.year,
            fecha__month=fecha_obj.month
        ).order_by('fecha')

        # Mapeamos los registros por día: { día_num: objeto_registro }
        for reg in registros_mes:
            fecha_local = timezone.localtime(reg.fecha) if timezone.is_aware(reg.fecha) else reg.fecha
            dia_num = fecha_local.day
            registros_mes_dict[dia_num] = reg

        # Datos para la gráfica del mes actual
        mes_actual = timezone.now().month
        anho_actual = timezone.now().year
        
        stats_emociones = (
            RegistroEmocional.objects.filter(
                usuario=paciente_seleccionado.usuario,
                fecha__month=mes_actual,
                fecha__year=anho_actual
            )
            .values('emocion')
            .annotate(total=Count('emocion'))
            .order_by('-total')
        )

        etiquetas_emociones = [item['emocion'] for item in stats_emociones]
        conteo_emociones = [item['total'] for item in stats_emociones]

    if request.method == 'POST':
        paciente_post_id = request.POST.get('paciente_id')
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        
        paciente_destino = get_object_or_404(PerfilUsuario, id=paciente_post_id, terapeuta_asignado=request.user)
        
        # OBTENER LA ÚLTIMA EMOCIÓN REGISTRADA PARA ASIGNARLA COMO OBJETIVO AUTOMÁTICAMENTE
        ultima_emocion = 'ANSIOSO'
        if registros_emocionales.exists():
            ultima_emocion = registros_emocionales.first().emocion.upper()
        
        # Guardado en el modelo ActividadEmocional
        ActividadEmocional.objects.create(
            terapeuta=request.user,
            paciente=paciente_destino.usuario,
            emocion_objetivo=ultima_emocion,
            titulo=titulo,
            descripcion=descripcion
        )
        
        messages.success(request, '¡Actividad asignada con éxito al paciente!')
        return redirect('dashboard_terapeuta')

    return render(request, 'mentalidad_app/terapeuta/crear_actividad.html', {
        'pacientes': pacientes,
        'paciente_seleccionado': paciente_seleccionado,
        'registros_emocionales': registros_emocionales,
        'fecha_seleccionada': fecha_seleccionada,
        'fecha_obj': fecha_obj,
        'dias_matriz': dias_matriz,
        'registros_mes_dict': registros_mes_dict,
        'etiquetas_emociones': etiquetas_emociones,
        'conteo_emociones': conteo_emociones,

    })

@login_required
def crear_reporte_comportamiento(request, paciente_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'TERAPEUTA':
        return redirect('home')

    paciente_perfil = get_object_or_404(PerfilUsuario, id=paciente_id, rol='PACIENTE', terapeuta_asignado=request.user)

    if request.method == 'POST':
        tipo = request.POST.get('tipo_comportamiento')
        descripcion = request.POST.get('descripcion', '')

        if tipo:
            ReporteComportamientoPaciente.objects.create(
                terapeuta=request.user,
                paciente=paciente_perfil.usuario,
                tipo_comportamiento=tipo,
                descripcion=descripcion
            )
            messages.success(request, "Reporte de comportamiento guardado exitosamente.")
        else:
            messages.error(request, "Debes seleccionar un tipo de comportamiento.")

    return redirect('detalle_paciente_terapeuta', paciente_id=paciente_id)

#emails

def enviar_correo_bienvenida(usuario):
    asunto = "🌱 ¡Bienvenido/a a Mentalidad Clara!"
    html_content = render_to_string('emails/bienvenida_paciente.html', {'usuario': usuario})

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": ["penarodriguezednakaterine@gmail.com"],
            "subject": asunto,
            "html": html_content,
        })
        print("✅ Correo enviado con éxito")
    except Exception as e:
        print(f"Error al enviar correo: {e}")