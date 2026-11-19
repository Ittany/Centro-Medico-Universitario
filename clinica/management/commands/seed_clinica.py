import random
from datetime import timedelta, time

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone

from clinica.models import Paciente, Medico, Cita, Consulta


class Command(BaseCommand):
    help = "Crea grupos, permisos, usuarios y datos de prueba para el Caso 2"

    def handle(self, *args, **options):
        random.seed(7)

        # Grupos
        grupos = {}
        for nombre in ["Admins", "Médicos", "Recepcionistas", "Pacientes"]:
            grupo, _ = Group.objects.get_or_create(name=nombre)
            grupos[nombre] = grupo

        # Permisos personalizados
        def perm(codename):
            return Permission.objects.get(codename=codename)

        permisos = {
            "agendar_cita": perm("agendar_cita"),
            "cancelar_cita": perm("cancelar_cita"),
            "ver_historial_clinico": perm("ver_historial_clinico"),
            "generar_reportes": perm("generar_reportes"),
        }

        grupos["Admins"].permissions.set(Permission.objects.all())
        grupos["Médicos"].permissions.set([
            permisos["ver_historial_clinico"],
            permisos["cancelar_cita"],
        ])
        grupos["Recepcionistas"].permissions.set([
            permisos["agendar_cita"],
            permisos["cancelar_cita"],
        ])
        grupos["Pacientes"].permissions.set([
            permisos["agendar_cita"],
            permisos["cancelar_cita"],
            permisos["ver_historial_clinico"],
        ])

        # Admin
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@uncp.edu.pe", "first_name": "Admin", "last_name": "UNCP"},
        )
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        admin.groups.add(grupos["Admins"])

        # Recepcionista
        recep, _ = User.objects.get_or_create(
            username="recepcionista",
            defaults={"email": "recepcion@uncp.edu.pe", "first_name": "Rosa", "last_name": "Recepción"},
        )
        recep.set_password("recepcion123")
        recep.save()
        recep.groups.add(grupos["Recepcionistas"])

        # Médicos
        especialidades = [e[0] for e in Medico.ESPECIALIDADES]
        medicos = []
        for i in range(1, 9):
            username = f"medico{i}"
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@uncp.edu.pe",
                    "first_name": f"Medico{i}",
                    "last_name": "Prueba",
                },
            )
            user.set_password("medico123")
            user.save()
            user.groups.add(grupos["Médicos"])

            medico, _ = Medico.objects.get_or_create(
                cmp=f"{10000 + i}",
                defaults={
                    "usuario": user,
                    "especialidad": especialidades[(i - 1) % len(especialidades)],
                    "horario_atencion": "L-V 08:00-18:00",
                    "consultorio": f"C-{i:02d}",
                },
            )
            medico.usuario = user
            medico.save()
            medicos.append(medico)

        # Pacientes
        pacientes = []
        for i in range(1, 16):
            username = f"paciente{i}"
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@uncp.edu.pe",
                    "first_name": f"Paciente{i}",
                    "last_name": "Prueba",
                },
            )
            user.set_password("paciente123")
            user.save()
            user.groups.add(grupos["Pacientes"])

            paciente, _ = Paciente.objects.get_or_create(
                dni=f"{70000000 + i}",
                defaults={
                    "usuario": user,
                    "nombres": f"Paciente{i}",
                    "apellidos": "Prueba",
                    "fecha_nacimiento": timezone.localdate() - timedelta(days=20 * 365 + i),
                    "tipo": "estudiante",
                    "codigo_uncp": f"2026{i:04d}",
                    "email": f"{username}@uncp.edu.pe",
                    "alergias": "Ninguna" if i % 3 else "Penicilina",
                },
            )
            paciente.usuario = user
            paciente.save()
            pacientes.append(paciente)

        # Citas
        horas = [time(8, 0), time(9, 0), time(10, 0), time(11, 0), time(15, 0), time(16, 0), time(17, 0)]
        estados = ["pendiente", "pendiente", "pendiente", "completada", "cancelada"]
        creadas = 0
        intentos = 0

        while creadas < 30 and intentos < 300:
            intentos += 1
            paciente = random.choice(pacientes)
            medico = random.choice(medicos)
            fecha = timezone.localdate() + timedelta(days=random.randint(-5, 10))
            hora = random.choice(horas)
            estado = random.choice(estados)

            cita, created = Cita.objects.get_or_create(
                paciente=paciente,
                medico=medico,
                fecha=fecha,
                hora=hora,
                defaults={
                    "motivo": "Consulta médica general por dolor y malestar.",
                    "estado": estado,
                    "creado_por": recep,
                },
            )

            if created:
                creadas += 1
                if estado == "completada":
                    Consulta.objects.get_or_create(
                        cita=cita,
                        defaults={
                            "diagnostico": "Cuadro leve, paciente estable.",
                            "tratamiento": "Reposo y hidratación.",
                            "medicamentos": "Paracetamol 500 mg cada 8 horas.",
                            "proxima_cita": fecha + timedelta(days=7),
                            "adjuntos_descripcion": "Receta simulada.",
                            "creado_por": medico.usuario,
                        },
                    )

        self.stdout.write(self.style.SUCCESS("Datos de prueba creados correctamente."))
        self.stdout.write("Usuarios: admin/admin123, recepcionista/recepcion123, medico1/medico123, paciente1/paciente123")