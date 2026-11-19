import logging
from datetime import time as dt_time

from django.http import HttpResponseForbidden
from django.utils import timezone
from django.contrib import messages

from .models import AuditoriaAcceso, Cita

logger = logging.getLogger("clinica.auditoria")


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class ValidacionHorarioMiddleware:
    """
    Valida que las citas enviadas por POST solo se agenden dentro del horario
    de atención: L-V 08:00-18:00 y Sáb 08:00-13:00.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/citas/nueva/") and request.method == "POST":
            fecha_str = request.POST.get("fecha")
            hora_str = request.POST.get("hora")
            if fecha_str and hora_str:
                try:
                    from datetime import datetime
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    hora = datetime.strptime(hora_str, "%H:%M").time()
                    dia = fecha.weekday()
                    valido = False
                    if dia <= 4:
                        valido = dt_time(8, 0) <= hora <= dt_time(18, 0)
                    elif dia == 5:
                        valido = dt_time(8, 0) <= hora <= dt_time(13, 0)
                    if not valido:
                        return HttpResponseForbidden(
                            "Horario no permitido. L-V 08:00-18:00, Sáb 08:00-13:00."
                        )
                except ValueError:
                    pass

        return self.get_response(request)


class AuditoriaMedicaMiddleware:
    """
    Registra accesos a historiales clínicos y consultas médicas.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        rutas_sensibles = ["/historial/", "/consultas/"]
        if request.user.is_authenticated and any(r in request.path for r in rutas_sensibles):
            ip = get_client_ip(request)
            AuditoriaAcceso.objects.create(
                usuario=request.user,
                ruta=request.path,
                metodo=request.method,
                ip=ip,
                detalle="Acceso a información clínica sensible",
            )
            logger.info(
                "AUDITORIA MEDICA | usuario=%s | ruta=%s | metodo=%s | ip=%s",
                request.user.username,
                request.path,
                request.method,
                ip,
            )

        return response


class AlertasCitasMiddleware:
    """
    Al iniciar sesión, si el usuario es médico, muestra cuántas citas pendientes tiene.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.session.get("alerta_citas_mostrada"):
            if request.user.groups.filter(name="Médicos").exists():
                try:
                    medico = request.user.medico
                    pendientes = Cita.objects.filter(
                        medico=medico,
                        estado="pendiente",
                        fecha__gte=timezone.localdate(),
                    ).count()
                    if pendientes:
                        messages.warning(
                            request,
                            f"Tiene {pendientes} cita(s) pendiente(s) por atender.",
                        )
                except Exception:
                    pass
            request.session["alerta_citas_mostrada"] = True

        return self.get_response(request)