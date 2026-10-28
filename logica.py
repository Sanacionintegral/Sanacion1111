"""Reglas del negocio: horas libres, reservas sin choques, recordatorios y reporte del mes.

No sabe nada de la interfaz: todo se puede probar con pytest.
"""

import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from urllib.parse import quote

import config

FMT = "%Y-%m-%d %H:%M"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


class ReservaInvalida(ValueError):
    pass


@dataclass(frozen=True)
class Reserva:
    id: int
    cliente: str
    telefono: str
    estilista: str
    servicio: str
    inicio: datetime
    fin: datetime
    precio: int
    estado: str
    recordatorio_enviado: bool


def _hora(texto: str) -> time:
    return datetime.strptime(texto, "%H:%M").time()


def _fila_a_reserva(f: sqlite3.Row) -> Reserva:
    return Reserva(f["id"], f["nombre"], f["telefono"], f["estilista"], f["servicio"],
                   datetime.strptime(f["inicio"], FMT), datetime.strptime(f["fin"], FMT),
                   f["precio"], f["estado"], bool(f["recordatorio_enviado"]))


# ---------- clientes ----------

def normalizar_telefono(texto: str) -> str:
    """Normaliza números móviles argentinos para WhatsApp (549 + 10 dígitos)."""
    digitos = "".join(c for c in texto if c.isdigit())
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if digitos.startswith("549") and len(digitos) == 13:
        return digitos
    if digitos.startswith("54"):
        digitos = digitos[2:]
    if digitos.startswith("0"):
        digitos = digitos[1:]
    if digitos.startswith("9") and len(digitos) == 11:
        digitos = digitos[1:]
    if "15" in digitos and len(digitos) == 12:
        # Formato local con 15 entre código de área y número.
        for area_len in (2, 3, 4):
            if digitos[area_len:area_len+2] == "15":
                digitos = digitos[:area_len] + digitos[area_len+2:]
                break
    if len(digitos) != 10:
        raise ReservaInvalida(f"Teléfono argentino no válido: {texto!r}. Ingresá código de área y número celular.")
    return "549" + digitos


def cliente_por_telefono(con: sqlite3.Connection, nombre: str, telefono: str) -> int:
    """Devuelve el id del cliente con ese teléfono; si no existe, lo crea."""
    tel = normalizar_telefono(telefono)
    fila = con.execute("SELECT id FROM clientes WHERE telefono = ?", (tel,)).fetchone()
    if fila:
        return fila["id"]
    if not nombre.strip():
        raise ReservaInvalida("Falta el nombre del cliente")
    return con.execute("INSERT INTO clientes (nombre, telefono) VALUES (?, ?)", (nombre.strip(), tel)).lastrowid


# ---------- agenda ----------

def reservas_del_dia(con: sqlite3.Connection, dia: date) -> list[Reserva]:
    filas = con.execute(
        """SELECT r.*, c.nombre, c.telefono FROM reservas r JOIN clientes c ON c.id = r.cliente_id
           WHERE substr(r.inicio, 1, 10) = ? AND r.estado != 'cancelada' ORDER BY r.inicio""",
        (dia.isoformat(),)).fetchall()
    return [_fila_a_reserva(f) for f in filas]


def horas_libres(con: sqlite3.Connection, estilista: str, dia: date, servicio: str,
                 desde: datetime | None = None) -> list[str]:
    """Horas de inicio posibles para ese servicio, sin chocar con otras reservas del estilista.
    Con `desde` (normalmente la hora actual) no se ofrecen horas que ya pasaron."""
    if dia.weekday() not in config.DIAS_ABIERTO:
        return []
    duracion = timedelta(minutes=config.SERVICIOS[servicio][0])
    abre = datetime.combine(dia, _hora(config.ABRE))
    cierra = datetime.combine(dia, _hora(config.CIERRA))
    ocupadas = [(r.inicio, r.fin) for r in reservas_del_dia(con, dia) if r.estilista == estilista]
    libres = []
    t = abre
    while t + duracion <= cierra:
        libre = all(t + duracion <= ini or t >= fin for ini, fin in ocupadas)
        if libre and (desde is None or t >= desde):
            libres.append(t.strftime("%H:%M"))
        t += timedelta(minutes=config.BLOQUE_MINUTOS)
    return libres


def crear_reserva(con: sqlite3.Connection, cliente_id: int, estilista: str, servicio: str,
                  inicio: datetime, desde: datetime | None = None) -> int:
    if estilista not in config.ESTILISTAS:
        raise ReservaInvalida(f"Terapeuta desconocido: {estilista}")
    if servicio not in config.SERVICIOS:
        raise ReservaInvalida(f"Servicio desconocido: {servicio}")
    if inicio.strftime("%H:%M") not in horas_libres(con, estilista, inicio.date(), servicio, desde):
        raise ReservaInvalida(f"{estilista} no tiene libre el {inicio:%d/%m} a las {inicio:%H:%M} para {servicio}")
    minutos, precio = config.SERVICIOS[servicio]
    fin = inicio + timedelta(minutes=minutos)
    return con.execute(
        "INSERT INTO reservas (cliente_id, estilista, servicio, inicio, fin, precio) VALUES (?, ?, ?, ?, ?, ?)",
        (cliente_id, estilista, servicio, inicio.strftime(FMT), fin.strftime(FMT), precio)).lastrowid


def cambiar_estado(con: sqlite3.Connection, reserva_id: int, estado: str) -> None:
    con.execute("UPDATE reservas SET estado = ? WHERE id = ?", (estado, reserva_id))


# ---------- recordatorios ----------

@dataclass(frozen=True)
class Recordatorio:
    reserva: Reserva
    mensaje: str
    enlace: str


def recordatorios(con: sqlite3.Connection, dia: date) -> list[Recordatorio]:
    """Un mensaje de WhatsApp listo para cada reserva agendada de ese día."""
    salida = []
    for r in reservas_del_dia(con, dia):
        if r.estado != "agendada":
            continue
        mensaje = config.RECORDATORIO.format(
            nombre=r.cliente.split()[0], negocio=config.NEGOCIO, dia=f"{DIAS[dia.weekday()]} {dia:%d/%m}",
            hora=f"{r.inicio:%H:%M}", servicio=r.servicio.lower(), estilista=r.estilista)
        salida.append(Recordatorio(r, mensaje, f"https://wa.me/{r.telefono}?text={quote(mensaje)}"))
    return salida


def marcar_recordado(con: sqlite3.Connection, reserva_id: int) -> None:
    con.execute("UPDATE reservas SET recordatorio_enviado = 1 WHERE id = ?", (reserva_id,))


# ---------- clientes y reporte ----------

@dataclass(frozen=True)
class FichaCliente:
    id: int
    nombre: str
    telefono: str
    visitas: int
    gastado: int
    ultima_visita: date | None


def clientes(con: sqlite3.Connection, buscar: str = "") -> list[FichaCliente]:
    filas = con.execute(
        """SELECT c.id, c.nombre, c.telefono,
                  COUNT(r.id) AS visitas, COALESCE(SUM(r.precio), 0) AS gastado,
                  MAX(substr(r.inicio, 1, 10)) AS ultima
           FROM clientes c LEFT JOIN reservas r ON r.cliente_id = c.id AND r.estado = 'atendida'
           WHERE c.nombre LIKE ? OR c.telefono LIKE ?
           GROUP BY c.id ORDER BY c.nombre""",
        (f"%{buscar}%", f"%{buscar}%")).fetchall()
    return [FichaCliente(f["id"], f["nombre"], f["telefono"], f["visitas"], f["gastado"],
                         date.fromisoformat(f["ultima"]) if f["ultima"] else None) for f in filas]


def clientes_por_recuperar(con: sqlite3.Connection, hoy: date) -> list[FichaCliente]:
    """Clientes que vinieron al menos dos veces, pero no vienen hace más de DIAS_CLIENTE_PERDIDO días
    y no tienen una hora agendada."""
    limite = hoy - timedelta(days=config.DIAS_CLIENTE_PERDIDO)
    con_hora = {f["cliente_id"] for f in con.execute(
        "SELECT cliente_id FROM reservas WHERE estado = 'agendada' AND inicio >= ?", (hoy.isoformat(),))}
    return [c for c in clientes(con)
            if c.visitas >= 2 and c.ultima_visita and c.ultima_visita < limite and c.id not in con_hora]


@dataclass(frozen=True)
class ReporteMes:
    anio: int
    mes: int
    atendidas: int
    no_vino: int
    ingresos: int
    perdido_por_inasistencias: int
    por_servicio: list[tuple[str, int]]
    por_estilista: list[tuple[str, int]]

    @property
    def tasa_inasistencia(self) -> float:
        total = self.atendidas + self.no_vino
        return self.no_vino / total if total else 0.0


def reporte_mes(con: sqlite3.Connection, anio: int, mes: int) -> ReporteMes:
    prefijo = f"{anio:04d}-{mes:02d}"
    filas = con.execute("SELECT * FROM reservas WHERE substr(inicio, 1, 7) = ? AND estado IN ('atendida', 'no_vino')",
                        (prefijo,)).fetchall()
    atendidas = [f for f in filas if f["estado"] == "atendida"]
    faltas = [f for f in filas if f["estado"] == "no_vino"]
    por_servicio = Counter()
    por_estilista = Counter()
    for f in atendidas:
        por_servicio[f["servicio"]] += f["precio"]
        por_estilista[f["estilista"]] += f["precio"]
    return ReporteMes(anio, mes, len(atendidas), len(faltas), sum(f["precio"] for f in atendidas),
                      sum(f["precio"] for f in faltas), por_servicio.most_common(), por_estilista.most_common())


def pesos(n: int) -> str:
    return f"${n:,}".replace(",", ".")
