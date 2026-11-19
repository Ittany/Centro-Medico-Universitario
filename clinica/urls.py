from django.urls import path

from .views import (
    CitaCancelView,
    CitaCreateView,
    CitaListView,
    ConsultaCreateView,
    DashboardView,
    HistorialPacienteView,
    MedicoCreateView,
    MedicoListView,
    PacienteCreateView,
    PacienteListView,
    ReportesView,
)

app_name = "clinica"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("citas/", CitaListView.as_view(), name="cita_list"),
    path("citas/nueva/", CitaCreateView.as_view(), name="cita_create"),
    path("citas/<int:pk>/cancelar/", CitaCancelView.as_view(), name="cita_cancel"),
    path("citas/<int:pk>/consulta/", ConsultaCreateView.as_view(), name="consulta_create"),
    path("pacientes/", PacienteListView.as_view(), name="paciente_list"),
    path("pacientes/nuevo/", PacienteCreateView.as_view(), name="paciente_create"),
    path("pacientes/<int:pk>/historial/", HistorialPacienteView.as_view(), name="historial"),
    path("medicos/", MedicoListView.as_view(), name="medico_list"),
    path("medicos/nuevo/", MedicoCreateView.as_view(), name="medico_create"),
    path("reportes/", ReportesView.as_view(), name="reportes"),
]