from datetime import date
from django.db import models
from django.contrib.auth.models import User


class Paciente(models.Model):
    TIPO_CHOICES = [
        ("estudiante", "Estudiante"),
        ("docente", "Docente"),
    ]

    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="paciente"
    )
    dni = models.CharField(max_length=8, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    codigo_uncp = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    alergias = models.TextField(blank=True)

    class Meta:
        ordering = ["apellidos", "nombres"]

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} - DNI {self.dni}"

    @property
    def edad(self):
        hoy = date.today()
        return hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )


class Medico(models.Model):
    ESPECIALIDADES = [
        ("Medicina General", "Medicina General"),
        ("Pediatría", "Pediatría"),
        ("Cardiología", "Cardiología"),
        ("Dermatología", "Dermatología"),
        ("Psicología", "Psicología"),
        ("Odontología", "Odontología"),
        ("Ginecología", "Ginecología"),
        ("Traumatología", "Traumatología"),
    ]

    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="medico"
    )
    cmp = models.CharField(max_length=10, unique=True)
    especialidad = models.CharField(max_length=50, choices=ESPECIALIDADES)
    horario_atencion = models.CharField(max_length=120, default="L-V 08:00-18:00")
    consultorio = models.CharField(max_length=50)

    class Meta:
        ordering = ["especialidad", "cmp"]

    def __str__(self):
        nombre = self.usuario.get_full_name() if self.usuario else f"CMP {self.cmp}"
        return f"Dr(a). {nombre} - {self.especialidad}"


class Cita(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
        ("ausente", "Ausente"),
    ]

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="citas")
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name="citas")
    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_creadas"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-hora"]
        permissions = [
            ("agendar_cita", "Puede agendar citas"),
            ("cancelar_cita", "Puede cancelar citas"),
        ]

    def __str__(self):
        return f"{self.paciente} con {self.medico} - {self.fecha} {self.hora}"


class Consulta(models.Model):
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name="consulta")
    diagnostico = models.TextField()
    tratamiento = models.TextField()
    medicamentos = models.TextField(blank=True)
    proxima_cita = models.DateField(null=True, blank=True)
    adjuntos_descripcion = models.TextField(
        blank=True, help_text="Descripción simulada de recetas o exámenes adjuntos"
    )
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="consultas_creadas"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        permissions = [
            ("ver_historial_clinico", "Puede ver historial clínico"),
            ("generar_reportes", "Puede generar reportes"),
        ]

    def __str__(self):
        return f"Consulta de {self.cita.paciente} - {self.cita.fecha}"


class AuditoriaAcceso(models.Model):
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    ruta = models.CharField(max_length=255)
    metodo = models.CharField(max_length=10)
    ip = models.GenericIPAddressField(null=True, blank=True)
    detalle = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.usuario} - {self.ruta} - {self.fecha}"