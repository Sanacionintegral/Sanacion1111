"""Configuración del negocio. Para adaptarlo a otro rubro, normalmente basta con cambiar este archivo."""

NEGOCIO = "SANACIÓN 11.11"

# Horario de atención (24 h). Día 0 = lunes ... 6 = domingo.
ABRE = "08:00"
CIERRA = "22:00"
DIAS_ABIERTO = {0, 1, 2, 3, 4, 5}  # lunes a sábado
BLOQUE_MINUTOS = 15  # cada cuánto se puede empezar una reserva

ESTILISTAS = ["Carla"]

# nombre: (duración en minutos, precio en pesos)
SERVICIOS = {
    "Lectura evolutiva": (40, 15000),
    "Pendulo Karnak": (40, 15000),
    "Biodescodificacion": (40, 30000),
    "Hipnosis": (40, 50000),
    "Liberacion y desbloqueo": (40, 50000),
    
}

PREFIJO_PAIS = "54"  # Argentina; WhatsApp utiliza 54 + 9 + código de área + número
DIAS_CLIENTE_PERDIDO = 45  # sin venir en este tiempo = cliente por recuperar

RECORDATORIO = (
    "¡Hola, {nombre}! Te recordamos tu hora en {negocio}: {dia} a las {hora}, "
    "{servicio} con {estilista}. Si no podés asistir, avisanos por acá para reorganizar la agenda. ¡Gracias!"
)
