from django.contrib import admin
from django.utils import timezone

from .models import Paciente, Medico, Cita, Consulta, AuditoriaAcceso


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("dni", "nombres", "apellidos", "tipo", "edad", "email")
    search_fields = ("dni", "nombres", "apellidos")
    list_filter = ("tipo",)

    @admin.display(description="Edad")
    def edad(self, obj):
        return obj.edad


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ("cmp", "nombre_medico", "especialidad", "consultorio")
    search_fields = ("cmp", "usuario__first_name", "usuario__last_name")
    list_filter = ("especialidad",)

    @admin.display(description="Médico")
    def nombre_medico(self, obj):
        return obj.usuario.get_full_name() if obj.usuario else f"CMP {obj.cmp}"


@admin.action(description="Marcar citas seleccionadas como completadas")
def marcar_completadas(modeladmin, request, queryset):
    actualizadas = queryset.update(estado="completada")
    modeladmin.message_user(request, f"{actualizadas} cita(s) marcadas como completadas.")


@admin.action(description="Enviar recordatorio de devolución/atención")
def enviar_recordatorio(modeladmin, request, queryset):
    modeladmin.message_user(
        request,
        f"Se simula el envío de recordatorio a {queryset.count()} cita(s).",
    )


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = (
        "paciente", "medico", "fecha", "hora", "estado", "dias_retraso"
    )
    list_filter = ("fecha", "estado", "medico")
    search_fields = (
        "paciente__dni", "paciente__nombres", "paciente__apellidos",
        "medico__cmp", "medico__usuario__first_name", "medico__usuario__last_name",
    )
    date_hierarchy = "fecha"
    actions = [marcar_completadas, enviar_recordatorio]
    autocomplete_fields = ["paciente", "medico"]

    @admin.display(description="Días de retraso")
    def dias_retraso(self, obj):
        if obj.estado == "pendiente" and obj.fecha < timezone.localdate():
            return (timezone.localdate() - obj.fecha).days
        return 0


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ("cita", "creado_por", "creado_en", "proxima_cita")
    search_fields = (
        "cita__paciente__dni",
        "cita__paciente__nombres",
        "diagnostico",
    )
    list_filter = ("creado_en", "proxima_cita")
    readonly_fields = ("creado_en",)


@admin.register(AuditoriaAcceso)
class AuditoriaAccesoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "ruta", "metodo", "ip", "fecha")
    list_filter = ("fecha", "metodo")
    search_fields = ("usuario__username", "ruta", "ip")
    readonly_fields = ("usuario", "ruta", "metodo", "ip", "detalle", "fecha")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False