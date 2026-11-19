from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from .forms import CitaForm, ConsultaForm, PacienteForm, MedicoForm
from .models import Cita, Consulta, Medico, Paciente


class StaffClinicaMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return (
            u.is_superuser
            or u.groups.filter(name__in=["Admins", "Recepcionistas"]).exists()
        )


class AdminClinicaMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_superuser or u.groups.filter(name="Admins").exists()


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "clinica/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user

        ctx["total_pacientes"] = Paciente.objects.count()
        ctx["total_medicos"] = Medico.objects.count()
        ctx["total_citas"] = Cita.objects.count()
        ctx["citas_pendientes"] = Cita.objects.filter(estado="pendiente").count()

        if u.groups.filter(name="Médicos").exists():
            try:
                ctx["mis_citas_pendientes"] = Cita.objects.filter(
                    medico=u.medico, estado="pendiente"
                ).count()
            except Exception:
                ctx["mis_citas_pendientes"] = 0

        if u.groups.filter(name="Pacientes").exists():
            try:
                ctx["mis_citas"] = Cita.objects.filter(paciente=u.paciente).count()
            except Exception:
                ctx["mis_citas"] = 0

        return ctx


class CitaListView(LoginRequiredMixin, ListView):
    model = Cita
    template_name = "clinica/cita_list.html"
    context_object_name = "citas"

    def get_queryset(self):
        qs = Cita.objects.select_related(
            "paciente", "medico__usuario"
        ).order_by("-fecha", "-hora")
        u = self.request.user

        if u.is_superuser or u.groups.filter(name__in=["Admins", "Recepcionistas"]).exists():
            return qs
        if u.groups.filter(name="Médicos").exists():
            return qs.filter(medico__usuario=u)
        if u.groups.filter(name="Pacientes").exists():
            return qs.filter(paciente__usuario=u)
        return qs.none()


class CitaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Cita
    form_class = CitaForm
    template_name = "clinica/form.html"
    permission_required = "clinica.agendar_cita"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nueva cita médica"
        ctx["subtitulo"] = "Complete los datos. El motivo debe tener mínimo 20 caracteres."
        return ctx

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, "Cita registrada correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("clinica:cita_list")


class CitaCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cita = get_object_or_404(Cita, pk=pk)
        u = request.user

        permitido = (
            u.is_superuser
            or u.groups.filter(name__in=["Admins", "Recepcionistas"]).exists()
            or (u.groups.filter(name="Médicos").exists() and cita.medico.usuario_id == u.id)
            or (u.groups.filter(name="Pacientes").exists() and cita.paciente.usuario_id == u.id)
        )

        if not permitido:
            return HttpResponseForbidden("No tiene permiso para cancelar esta cita.")

        if cita.estado != "pendiente":
            messages.error(request, "Solo se pueden cancelar citas pendientes.")
        else:
            cita.estado = "cancelada"
            cita.save()
            messages.success(request, "Cita cancelada correctamente.")

        return redirect("clinica:cita_list")


class ConsultaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Consulta
    form_class = ConsultaForm
    template_name = "clinica/form.html"
    permission_required = "clinica.ver_historial_clinico"

    def dispatch(self, request, *args, **kwargs):
        self.cita = get_object_or_404(
            Cita.objects.select_related("medico__usuario", "paciente"),
            pk=kwargs["pk"],
        )

        es_medico_asignado = (
            request.user.groups.filter(name="Médicos").exists()
            and self.cita.medico.usuario_id == request.user.id
        )
        if not (request.user.is_superuser or es_medico_asignado):
            return HttpResponseForbidden("Solo el médico asignado puede registrar la consulta.")

        if hasattr(self.cita, "consulta"):
            messages.info(request, "Esta cita ya tiene una consulta registrada.")
            return redirect("clinica:historial", pk=self.cita.paciente.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Registrar consulta médica"
        ctx["subtitulo"] = f"Paciente: {self.cita.paciente} | Médico: {self.cita.medico}"
        return ctx

    def form_valid(self, form):
        form.instance.cita = self.cita
        form.instance.creado_por = self.request.user
        self.cita.estado = "completada"
        self.cita.save()
        messages.success(self.request, "Consulta registrada correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("clinica:historial", args=[self.cita.paciente.pk])


class HistorialPacienteView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Paciente
    template_name = "clinica/historial.html"
    context_object_name = "paciente"
    permission_required = "clinica.ver_historial_clinico"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        u = self.request.user

        if u.is_superuser:
            return obj

        if u.groups.filter(name="Pacientes").exists():
            if obj.usuario_id != u.id:
                raise PermissionDenied("Solo puede ver su propio historial clínico.")
            return obj

        if u.groups.filter(name="Médicos").exists():
            return obj

        raise PermissionDenied("No tiene permiso para ver historiales clínicos.")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["consultas"] = Consulta.objects.filter(
            cita__paciente=self.object
        ).select_related("cita__medico__usuario").order_by("-creado_en")
        return ctx


class PacienteListView(StaffClinicaMixin, ListView):
    model = Paciente
    template_name = "clinica/paciente_list.html"
    context_object_name = "pacientes"

    def get_queryset(self):
        qs = Paciente.objects.all()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(dni__icontains=q) | qs.filter(nombres__icontains=q) | qs.filter(
                apellidos__icontains=q
            )
        return qs


class PacienteCreateView(StaffClinicaMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "clinica/form.html"
    success_url = reverse_lazy("clinica:paciente_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Registrar paciente"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Paciente registrado correctamente.")
        return super().form_valid(form)


class MedicoListView(AdminClinicaMixin, ListView):
    model = Medico
    template_name = "clinica/medico_list.html"
    context_object_name = "medicos"


class MedicoCreateView(AdminClinicaMixin, CreateView):
    model = Medico
    form_class = MedicoForm
    template_name = "clinica/form.html"
    success_url = reverse_lazy("clinica:medico_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Registrar médico"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Médico registrado correctamente.")
        return super().form_valid(form)


class ReportesView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "clinica/reportes.html"
    permission_required = "clinica.generar_reportes"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["citas_por_especialidad"] = (
            Cita.objects.values("medico__especialidad")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        ctx["medicos_top"] = (
            Medico.objects.annotate(total_citas=Count("citas"))
            .select_related("usuario")
            .order_by("-total_citas")[:5]
        )
        ctx["pacientes_top"] = (
            Paciente.objects.annotate(total_citas=Count("citas"))
            .order_by("-total_citas")[:5]
        )
        return ctx