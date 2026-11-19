import re
from datetime import date, time as dt_time

from django import forms
from django.utils import timezone

from .models import Paciente, Medico, Cita, Consulta


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            "dni", "nombres", "apellidos", "fecha_nacimiento",
            "tipo", "codigo_uncp", "email", "alergias",
        ]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "alergias": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_dni(self):
        dni = self.cleaned_data["dni"].strip()
        if not re.fullmatch(r"\d{8}", dni):
            raise forms.ValidationError("El DNI debe tener exactamente 8 dígitos numéricos.")
        return dni

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        if fecha > date.today():
            raise forms.ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        tipo = self.data.get("tipo")
        if tipo in ["estudiante", "docente"] and not email.endswith("@uncp.edu.pe"):
            raise forms.ValidationError("El email institucional debe terminar en @uncp.edu.pe.")
        return email


class MedicoForm(forms.ModelForm):
    class Meta:
        model = Medico
        fields = ["cmp", "especialidad", "horario_atencion", "consultorio"]

    def clean_cmp(self):
        cmp = self.cleaned_data["cmp"].strip()
        if not re.fullmatch(r"\d{5}", cmp):
            raise forms.ValidationError("El CMP debe tener 5 dígitos numéricos. Ejemplo: 12345.")
        return cmp


class CitaForm(forms.ModelForm):
    especialidad = forms.ChoiceField(
        choices=[("", "Todas las especialidades")] + Medico.ESPECIALIDADES,
        required=False,
        label="Filtrar médico por especialidad",
    )

    field_order = ["especialidad", "paciente", "medico", "fecha", "hora", "motivo"]

    class Meta:
        model = Cita
        fields = ["paciente", "medico", "fecha", "hora", "motivo"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "hora": forms.TimeInput(attrs={"type": "time"}),
            "motivo": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["paciente"].queryset = Paciente.objects.all().order_by("apellidos", "nombres")
        self.fields["medico"].queryset = Medico.objects.select_related("usuario").all().order_by(
            "especialidad", "cmp"
        )

        especialidad = self.data.get("especialidad") if self.is_bound else None
        if especialidad:
            self.fields["medico"].queryset = self.fields["medico"].queryset.filter(
                especialidad=especialidad
            )

        if self.user and self.user.groups.filter(name="Pacientes").exists():
            try:
                paciente = self.user.paciente
                self.fields["paciente"].queryset = Paciente.objects.filter(pk=paciente.pk)
                self.fields["paciente"].initial = paciente
            except Paciente.DoesNotExist:
                self.fields["paciente"].queryset = Paciente.objects.none()

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()
        if len(motivo) < 20:
            raise forms.ValidationError("El motivo de consulta debe tener mínimo 20 caracteres.")
        return motivo

    def clean(self):
        cleaned = super().clean()
        paciente = cleaned.get("paciente")
        medico = cleaned.get("medico")
        fecha = cleaned.get("fecha")
        hora = cleaned.get("hora")
        especialidad = cleaned.get("especialidad")

        if especialidad and medico and medico.especialidad != especialidad:
            self.add_error("medico", "El médico seleccionado no pertenece a la especialidad filtrada.")

        if self.user and self.user.groups.filter(name="Pacientes").exists():
            try:
                if paciente and paciente.pk != self.user.paciente.pk:
                    self.add_error("paciente", "Como paciente solo puede agendar citas para usted mismo.")
            except Paciente.DoesNotExist:
                self.add_error("paciente", "Su usuario no tiene un perfil de paciente asociado.")

        if fecha and hora:
            if fecha < timezone.localdate():
                self.add_error("fecha", "No se pueden agendar citas en fechas pasadas.")

            if fecha == timezone.localdate() and hora < timezone.localtime().time():
                self.add_error("hora", "La hora seleccionada ya pasó para el día de hoy.")

            dia = fecha.weekday()  # 0=Lunes, 5=Sábado, 6=Domingo
            if dia <= 4:
                if not (dt_time(8, 0) <= hora <= dt_time(18, 0)):
                    self.add_error("hora", "Horario de atención L-V: 08:00 a 18:00.")
            elif dia == 5:
                if not (dt_time(8, 0) <= hora <= dt_time(13, 0)):
                    self.add_error("hora", "Horario de atención sábados: 08:00 a 13:00.")
            else:
                self.add_error("fecha", "No hay atención los domingos.")

        qs = Cita.objects.filter(estado="pendiente")
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if paciente and fecha and qs.filter(paciente=paciente, fecha=fecha).exists():
            self.add_error("paciente", "El paciente ya tiene otra cita pendiente para ese día.")

        if medico and fecha and hora and qs.filter(medico=medico, fecha=fecha, hora=hora).exists():
            self.add_error("hora", "El médico ya tiene una cita en ese horario.")

        return cleaned


class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = [
            "diagnostico", "tratamiento", "medicamentos",
            "proxima_cita", "adjuntos_descripcion",
        ]
        widgets = {
            "diagnostico": forms.Textarea(attrs={"rows": 3}),
            "tratamiento": forms.Textarea(attrs={"rows": 3}),
            "medicamentos": forms.Textarea(attrs={"rows": 3}),
            "proxima_cita": forms.DateInput(attrs={"type": "date"}),
            "adjuntos_descripcion": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_diagnostico(self):
        diagnostico = self.cleaned_data["diagnostico"].strip()
        if len(diagnostico) < 10:
            raise forms.ValidationError("El diagnóstico debe tener mínimo 10 caracteres.")
        return diagnostico

    def clean_tratamiento(self):
        tratamiento = self.cleaned_data["tratamiento"].strip()
        if len(tratamiento) < 10:
            raise forms.ValidationError("El tratamiento debe tener mínimo 10 caracteres.")
        return tratamiento