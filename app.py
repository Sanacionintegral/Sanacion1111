"""Sistema de reservas Sanación 11.11 — interfaz de escritorio (CustomTkinter)."""

import os
import sys
import tkinter as tk
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import customtkinter as ctk

import config
import db
import logica

# Carpeta de datos: junto al .exe cuando está empaquetado, junto al script en desarrollo
BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
RUTA_DB = BASE / "reservas.db"
RESPALDOS = BASE / "respaldos"
# RESERVAS_AHORA="2026-10-15 12:40" fija la fecha y hora (útil para demos y capturas)
AHORA = datetime.fromisoformat(os.environ["RESERVAS_AHORA"]) if "RESERVAS_AHORA" in os.environ else datetime.now()
HOY = AHORA.date()

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
COLOR = {"principal": "#b98539", "principal_hover": "#9c6b2d", "fondo": "#f7f0e5", "tarjeta": "#fffaf2", "texto": "#4c301d", "suave": "#806b55", "agendada": "#bb8c52", "atendida": "#608768", "no_vino": "#b45f55", "linea": "#e8dac6", "lateral": "#f4e5ce", "seleccion": "#e7cfaa"}
FUENTE = "DejaVu Sans" if sys.platform.startswith("linux") else "Segoe UI"


def f(tam=14, peso="normal"):
    return ctk.CTkFont(family=FUENTE, size=tam, weight=peso)


def fecha_larga(d: date) -> str:
    return f"{logica.DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]}"


def dibujar_loto(canvas, cx, cy, tam):
    """Ornamento botánico vectorial en dorado, sin archivos externos."""
    import math
    dorado = COLOR["principal"]
    for ang in (-72, -48, -24, 0, 24, 48, 72):
        rad = math.radians(ang)
        punta_x = cx + math.sin(rad) * tam * 0.88
        punta_y = cy - math.cos(rad) * tam * 0.82
        base_y = cy + tam * 0.35
        dx = math.cos(rad) * tam * 0.27
        canvas.create_line(cx, base_y, cx-dx, cy-tam*.12, punta_x, punta_y,
                           cx+dx, cy-tam*.12, cx, base_y, smooth=True,
                           fill=dorado, width=1.5)
    canvas.create_arc(cx-tam*.75, cy-tam*.12, cx+tam*.75, cy+tam*.58,
                      start=190, extent=160, style="arc", outline=dorado, width=1.5)
    for x,y in ((.84,-.40),(-.89,-.23),(.94,.14),(-.72,.38)):
        r=2
        canvas.create_oval(cx+x*tam-r,cy+y*tam-r,cx+x*tam+r,cy+y*tam+r,fill=dorado,outline="")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(f"{config.NEGOCIO} — Reservas")
        self.geometry("1400x860+260+110")
        self.configure(fg_color=COLOR["fondo"])
        self.con = db.conectar(RUTA_DB)
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

        lateral = ctk.CTkFrame(self, width=275, corner_radius=0, fg_color=COLOR["lateral"])
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        ctk.CTkLabel(lateral, text="☾ ✧", font=f(37), text_color=COLOR["principal"]).pack(pady=(23, 0))
        ctk.CTkLabel(lateral, text=config.NEGOCIO, font=f(23, "bold"), text_color=COLOR["texto"],
                     wraplength=255).pack(pady=(0, 0))
        ctk.CTkLabel(lateral, text="TERAPIAS HOLÍSTICAS", font=f(11), text_color=COLOR["principal"]).pack(pady=(0, 5))
        dibujo_superior = tk.Canvas(lateral, width=245, height=100, bg=COLOR["lateral"], highlightthickness=0)
        dibujo_superior.pack(pady=(0, 12))
        dibujar_loto(dibujo_superior, 122, 59, 65)
        self.botones = {}
        iconos = {"Agenda": "▦", "Clientes": "♙", "Recordatorios": "♧", "Reporte": "▥"}
        for nombre in ("Agenda", "Clientes", "Recordatorios", "Reporte"):
            b = ctk.CTkButton(lateral, text=f"{iconos[nombre]}    {nombre}", anchor="w", height=50,
                              font=f(16), corner_radius=10, text_color=COLOR["texto"],
                              fg_color="transparent", hover_color=COLOR["seleccion"],
                              command=lambda n=nombre: self.mostrar(n))
            b.pack(fill="x", padx=14, pady=5)
            self.botones[nombre] = b
        dibujo_inferior = tk.Canvas(lateral, width=255, height=225, bg=COLOR["lateral"], highlightthickness=0)
        dibujo_inferior.pack(side="bottom", pady=(0, 15))
        dibujar_loto(dibujo_inferior, 125, 135, 105)
        ctk.CTkLabel(lateral, text=f"Hoy: {HOY:%d/%m/%Y}  ·  Respaldo al cerrar", font=f(11),
                     text_color=COLOR["suave"]).pack(side="bottom", pady=10)

        self.contenido = ctk.CTkFrame(self, fg_color="transparent")
        self.contenido.pack(side="left", fill="both", expand=True, padx=24, pady=20)
        self.aviso = ctk.CTkLabel(self, text="", font=f(14, "bold"), fg_color=COLOR["texto"], text_color="white",
                                  corner_radius=8, height=40)
        self.vistas = {"Agenda": VistaAgenda, "Clientes": VistaClientes, "Recordatorios": VistaRecordatorios,
                       "Reporte": VistaReporte}
        self.mostrar("Agenda")

    def mostrar(self, nombre):
        for n, b in self.botones.items():
            b.configure(fg_color=COLOR["seleccion"] if n == nombre else "transparent")
        for w in self.contenido.winfo_children():
            w.destroy()
        self.vista = self.vistas[nombre](self.contenido, self)
        self.vista.pack(fill="both", expand=True)

    def avisar(self, texto):
        self.aviso.configure(text=f"   {texto}   ")
        self.aviso.place(relx=0.58, rely=0.95, anchor="center")
        self.after(2600, self.aviso.place_forget)

    def abrir_whatsapp(self, enlace):
        webbrowser.open(enlace)

    def cerrar(self):
        self.con.commit()
        db.respaldar(RUTA_DB, RESPALDOS)
        self.con.close()
        self.destroy()


class VistaAgenda(ctk.CTkFrame):
    HORA_PX = 58
    TOP = 44

    def __init__(self, padre, app: App):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.dia = HOY
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(barra, text="◀", width=40, font=f(15), fg_color=COLOR["tarjeta"], text_color=COLOR["texto"],
                      hover_color=COLOR["linea"], command=lambda: self.mover(-1)).pack(side="left")
        self.titulo = ctk.CTkLabel(barra, text="", font=f(22, "bold"), text_color=COLOR["texto"], width=360)
        self.titulo.pack(side="left", padx=10)
        ctk.CTkButton(barra, text="▶", width=40, font=f(15), fg_color=COLOR["tarjeta"], text_color=COLOR["texto"],
                      hover_color=COLOR["linea"], command=lambda: self.mover(1)).pack(side="left")
        ctk.CTkButton(barra, text="Hoy", width=70, font=f(14), fg_color=COLOR["tarjeta"], text_color=COLOR["texto"],
                      hover_color=COLOR["linea"], command=self.ir_hoy).pack(side="left", padx=10)
        ctk.CTkButton(barra, text="+  Nueva reserva", height=40, font=f(15, "bold"), fg_color=COLOR["principal"],
                      hover_color=COLOR["principal_hover"], command=self.nueva).pack(side="right")
        self.resumen = ctk.CTkLabel(barra, text="", font=f(14), text_color=COLOR["suave"])
        self.resumen.pack(side="right", padx=16)

        marco = ctk.CTkFrame(self, fg_color=COLOR["tarjeta"], corner_radius=12)
        marco.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(marco, bg=COLOR["tarjeta"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda e: self.dibujar())
        self.bloques = {}

    def mover(self, dias):
        self.dia += timedelta(days=dias)
        self.dibujar()

    def ir_hoy(self):
        self.dia = HOY
        self.dibujar()

    def dibujar(self):
        c = self.canvas
        c.delete("all")
        self.bloques.clear()
        self.titulo.configure(text=fecha_larga(self.dia) + ("  ·  hoy" if self.dia == HOY else ""))
        ancho = c.winfo_width()
        x0, columna = 70, (ancho - 70) / len(config.ESTILISTAS)
        abre, cierra = int(config.ABRE[:2]), int(config.CIERRA[:2])
        for i, est in enumerate(config.ESTILISTAS):
            c.create_text(x0 + columna * (i + 0.5), 18, text=est, font=(FUENTE, 15, "bold"), fill=COLOR["texto"])
        for h in range(abre, cierra + 1):
            y = self.TOP + (h - abre) * self.HORA_PX
            c.create_line(x0, y, ancho, y, fill=COLOR["linea"])
            c.create_text(x0 - 12, y, text=f"{h:02d}:00", anchor="e", font=(FUENTE, 11), fill=COLOR["suave"])
        for i in range(1, len(config.ESTILISTAS)):
            c.create_line(x0 + columna * i, self.TOP, x0 + columna * i, self.TOP + (cierra - abre) * self.HORA_PX,
                          fill=COLOR["linea"])
        if self.dia.weekday() not in config.DIAS_ABIERTO:
            c.create_text(ancho / 2, 300, text="Cerrado", font=(FUENTE, 20), fill=COLOR["suave"])
        reservas = logica.reservas_del_dia(self.app.con, self.dia)
        for r in reservas:
            i = config.ESTILISTAS.index(r.estilista)
            y1 = self.TOP + (r.inicio.hour - abre + r.inicio.minute / 60) * self.HORA_PX
            y2 = self.TOP + (r.fin.hour - abre + r.fin.minute / 60) * self.HORA_PX
            xa, xb = x0 + columna * i + 6, x0 + columna * (i + 1) - 6
            etiqueta = f"r{r.id}"
            c.create_rectangle(xa, y1 + 2, xb, y2 - 2, fill=COLOR[r.estado], outline="", tags=etiqueta)
            marca = {"atendida": "  ✓", "no_vino": "  ✗ no vino"}.get(r.estado, "")
            max_car = int((xb - xa - 20) / 7.3)
            if y2 - y1 > 50:
                texto = f"{r.inicio:%H:%M}  {r.servicio}{marca}"[:max_car] + "\n" + r.cliente[:max_car]
            else:
                texto = f"{r.inicio:%H:%M}  {r.servicio} · {r.cliente}"[:max_car - len(marca)] + marca
            c.create_text(xa + 10, y1 + 6, text=texto, anchor="nw", font=(FUENTE, 11), fill="white", tags=etiqueta)
            c.tag_bind(etiqueta, "<Button-1>", lambda e, res=r: self.menu_reserva(res))
            self.bloques[r.id] = (xa, y1, xb, y2)
        if self.dia == HOY and abre <= AHORA.hour < cierra:
            y = self.TOP + (AHORA.hour - abre + AHORA.minute / 60) * self.HORA_PX
            c.create_line(x0, y, ancho, y, fill=COLOR["no_vino"], width=2)
            c.create_text(x0 - 12, y, text=f"{AHORA:%H:%M}", anchor="e", font=(FUENTE, 11, "bold"), fill=COLOR["no_vino"])
        ingresos = sum(r.precio for r in reservas)
        self.resumen.configure(text=f"{len(reservas)} reservas · {logica.pesos(ingresos)}")

    def menu_reserva(self, r: logica.Reserva):
        v = ctk.CTkToplevel(self)
        v.title("Reserva")
        v.geometry("380x300+780+380")
        v.configure(fg_color=COLOR["tarjeta"])
        v.transient(self.app)
        ctk.CTkLabel(v, text=r.cliente, font=f(18, "bold"), text_color=COLOR["texto"]).pack(pady=(20, 2))
        ctk.CTkLabel(v, text=f"{r.servicio} con {r.estilista}\n{r.inicio:%d/%m %H:%M}–{r.fin:%H:%M} · "
                             f"{logica.pesos(r.precio)}", font=f(14), text_color=COLOR["suave"]).pack(pady=(0, 16))

        def poner(estado, texto):
            logica.cambiar_estado(self.app.con, r.id, estado)
            self.app.con.commit()
            v.destroy()
            self.dibujar()
            self.app.avisar(texto)

        for estado, texto, color in (("atendida", "Atendida", COLOR["atendida"]),
                                     ("no_vino", "No vino", COLOR["no_vino"]),
                                     ("cancelada", "Cancelar reserva", "#8a8088")):
            ctk.CTkButton(v, text=texto, height=38, font=f(14), fg_color=color,
                          command=lambda e=estado, t=texto: poner(e, f"{r.cliente}: {t.lower()}")).pack(
                fill="x", padx=40, pady=4)
        v.after(50, v.grab_set)

    def nueva(self):
        DialogoReserva(self.app, self.dia, self.dibujar)


class DialogoReserva(ctk.CTkToplevel):
    def __init__(self, app: App, dia: date, al_guardar):
        super().__init__(app)
        self.app, self.dia, self.al_guardar = app, dia, al_guardar
        self.title("Nueva reserva")
        self.geometry("520x620+700+200")
        self.configure(fg_color=COLOR["tarjeta"])
        self.transient(app)
        ctk.CTkLabel(self, text=f"Nueva reserva · {fecha_larga(dia)}", font=f(18, "bold"),
                     text_color=COLOR["texto"]).pack(anchor="w", padx=30, pady=(24, 14))

        def campo(texto):
            ctk.CTkLabel(self, text=texto, font=f(13), text_color=COLOR["suave"]).pack(anchor="w", padx=30)

        campo("Teléfono (WhatsApp)")
        self.tel = ctk.CTkEntry(self, height=38, font=f(15), placeholder_text="9 1234 5678")
        self.tel.pack(fill="x", padx=30, pady=(2, 10))
        self.tel.bind("<KeyRelease>", self.buscar_cliente)
        campo("Nombre")
        self.nombre = ctk.CTkEntry(self, height=38, font=f(15))
        self.nombre.pack(fill="x", padx=30, pady=(2, 4))
        self.ficha = ctk.CTkLabel(self, text="", font=f(12), text_color=COLOR["atendida"])
        self.ficha.pack(anchor="w", padx=30, pady=(0, 8))
        campo("Servicio")
        self.servicio = ctk.CTkOptionMenu(self, values=list(config.SERVICIOS), height=38, font=f(15),
                                          fg_color=COLOR["seleccion"], button_color=COLOR["principal"],
                                           text_color=COLOR["texto"],
                                          command=lambda _: self.actualizar_horas())
        self.servicio.pack(fill="x", padx=30, pady=(2, 10))
        campo("Terapeuta")
        self.estilista = ctk.CTkOptionMenu(self, values=config.ESTILISTAS, height=38, font=f(15),
                                           fg_color=COLOR["seleccion"], button_color=COLOR["principal"],
                                           text_color=COLOR["texto"],
                                           command=lambda _: self.actualizar_horas())
        self.estilista.pack(fill="x", padx=30, pady=(2, 10))
        campo("Hora (solo se muestran las libres)")
        self.hora = ctk.CTkOptionMenu(self, values=["--"], height=38, font=f(15),
                                      fg_color=COLOR["principal"], button_color=COLOR["principal_hover"])
        self.hora.pack(fill="x", padx=30, pady=(2, 4))
        self.libres = ctk.CTkLabel(self, text="", font=f(12), text_color=COLOR["suave"])
        self.libres.pack(anchor="w", padx=30)
        self.error = ctk.CTkLabel(self, text="", font=f(13), text_color=COLOR["no_vino"], wraplength=440)
        self.error.pack(anchor="w", padx=30, pady=4)
        ctk.CTkButton(self, text="Guardar reserva", height=44, font=f(16, "bold"), fg_color=COLOR["principal"],
                      hover_color=COLOR["principal_hover"], command=self.guardar).pack(fill="x", padx=30, pady=10)
        self.actualizar_horas()
        self.after(50, self.grab_set)

    def buscar_cliente(self, _=None):
        try:
            tel = logica.normalizar_telefono(self.tel.get())
        except logica.ReservaInvalida:
            self.ficha.configure(text="")
            return
        fila = self.app.con.execute("SELECT id, nombre FROM clientes WHERE telefono = ?", (tel,)).fetchone()
        if fila:
            ficha = next(c for c in logica.clientes(self.app.con) if c.id == fila["id"])
            self.nombre.delete(0, "end")
            self.nombre.insert(0, fila["nombre"])
            ultima = f", última vez el {ficha.ultima_visita:%d/%m}" if ficha.ultima_visita else ""
            self.ficha.configure(text=f"Cliente conocido: {ficha.visitas} visitas{ultima}")
        else:
            self.ficha.configure(text="Cliente nuevo")

    def actualizar_horas(self):
        libres = logica.horas_libres(self.app.con, self.estilista.get(), self.dia, self.servicio.get(), AHORA)
        self.hora.configure(values=libres or ["Sin horas"])
        self.hora.set(libres[0] if libres else "Sin horas")
        minutos, precio = config.SERVICIOS[self.servicio.get()]
        self.libres.configure(text=f"{len(libres)} horas libres · dura {minutos} min · {logica.pesos(precio)}")

    def guardar(self):
        try:
            cid = logica.cliente_por_telefono(self.app.con, self.nombre.get(), self.tel.get())
            inicio = datetime.strptime(f"{self.dia} {self.hora.get()}", "%Y-%m-%d %H:%M")
            logica.crear_reserva(self.app.con, cid, self.estilista.get(), self.servicio.get(), inicio, AHORA)
        except (logica.ReservaInvalida, ValueError) as e:
            self.error.configure(text=str(e))
            return
        self.app.con.commit()
        nombre_cliente = self.nombre.get()
        hora_reserva = self.hora.get()
        self.destroy()
        self.al_guardar()
        self.app.avisar(f"Reserva guardada: {nombre_cliente} a las {hora_reserva}")


class VistaClientes(ctk.CTkFrame):
    def __init__(self, padre, app: App):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.solo_perdidos = False
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(barra, text="Clientes", font=f(22, "bold"), text_color=COLOR["texto"]).pack(side="left")
        self.buscar = ctk.CTkEntry(barra, width=320, height=38, font=f(14), placeholder_text="Buscar por nombre o teléfono")
        self.buscar.pack(side="left", padx=20)
        self.buscar.bind("<KeyRelease>", lambda e: self.llenar())
        perdidos = logica.clientes_por_recuperar(app.con, HOY)
        self.btn_perdidos = ctk.CTkButton(barra, text=f"Por recuperar ({len(perdidos)})", height=38, font=f(14, "bold"),
                                          fg_color=COLOR["no_vino"], hover_color="#9c3f3c", command=self.alternar)
        self.btn_perdidos.pack(side="right")
        self.explicacion = ctk.CTkLabel(self, text="", font=f(13), text_color=COLOR["suave"])
        self.explicacion.pack(anchor="w")
        self.lista = ctk.CTkScrollableFrame(self, fg_color=COLOR["tarjeta"], corner_radius=12)
        self.lista.pack(fill="both", expand=True, pady=(6, 0))
        self.llenar()

    def alternar(self):
        self.solo_perdidos = not self.solo_perdidos
        self.btn_perdidos.configure(fg_color=COLOR["texto"] if self.solo_perdidos else COLOR["no_vino"])
        self.llenar()

    def llenar(self):
        for w in self.lista.winfo_children():
            w.destroy()
        if self.solo_perdidos:
            datos = logica.clientes_por_recuperar(self.app.con, HOY)
            self.explicacion.configure(text=f"Vinieron 2 o más veces, no vienen hace más de "
                                            f"{config.DIAS_CLIENTE_PERDIDO} días y no tienen hora agendada.")
        else:
            datos = logica.clientes(self.app.con, self.buscar.get().strip())
            self.explicacion.configure(text=f"{len(datos)} clientes")
        encabezado = ("Nombre", "Teléfono", "Visitas", "Total gastado", "Última visita", "")
        anchos = (260, 170, 90, 150, 150, 160)
        fila = ctk.CTkFrame(self.lista, fg_color="transparent")
        fila.pack(fill="x", pady=(4, 6))
        for t, a in zip(encabezado, anchos):
            ctk.CTkLabel(fila, text=t, width=a, anchor="w", font=f(13, "bold"), text_color=COLOR["suave"]).pack(side="left")
        for c in datos[:200]:
            fila = ctk.CTkFrame(self.lista, fg_color="transparent")
            fila.pack(fill="x", pady=1)
            tel = f"+{c.telefono[:2]} {c.telefono[2]} {c.telefono[3:7]} {c.telefono[7:]}"
            valores = (c.nombre, tel, str(c.visitas), logica.pesos(c.gastado),
                       f"{c.ultima_visita:%d/%m/%Y}" if c.ultima_visita else "—")
            for t, a in zip(valores, anchos):
                ctk.CTkLabel(fila, text=t, width=a, anchor="w", font=f(14), text_color=COLOR["texto"]).pack(side="left")
            if self.solo_perdidos:
                ctk.CTkButton(fila, text="Escribirle", width=120, height=30, font=f(13), fg_color=COLOR["atendida"],
                              command=lambda cl=c: self.escribir(cl)).pack(side="left")

    def escribir(self, c: logica.FichaCliente):
        texto = (f"¡Hola, {c.nombre.split()[0]}! Hace tiempo que no te vemos en {config.NEGOCIO}. "
                 f"¿Te reservamos una hora esta semana?")
        self.app.abrir_whatsapp(f"https://wa.me/{c.telefono}?text={quote(texto)}")
        self.app.avisar(f"Abriendo WhatsApp para {c.nombre}")


class VistaRecordatorios(ctk.CTkFrame):
    def __init__(self, padre, app: App):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.dia = HOY + timedelta(days=1)
        while self.dia.weekday() not in config.DIAS_ABIERTO:
            self.dia += timedelta(days=1)
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(barra, text=f"Recordatorios para mañana · {fecha_larga(self.dia)}", font=f(22, "bold"),
                     text_color=COLOR["texto"]).pack(side="left")
        self.contador = ctk.CTkLabel(barra, text="", font=f(14), text_color=COLOR["suave"])
        self.contador.pack(side="right")
        self.lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.lista.pack(fill="both", expand=True)
        self.llenar()

    def llenar(self):
        for w in self.lista.winfo_children():
            w.destroy()
        items = logica.recordatorios(self.app.con, self.dia)
        enviados = sum(i.reserva.recordatorio_enviado for i in items)
        self.contador.configure(text=f"{len(items)} reservas · {enviados} avisadas")
        for item in items:
            r = item.reserva
            tarjeta = ctk.CTkFrame(self.lista, fg_color=COLOR["tarjeta"], corner_radius=10)
            tarjeta.pack(fill="x", pady=5, padx=2)
            izq = ctk.CTkFrame(tarjeta, fg_color="transparent")
            izq.pack(side="left", fill="x", expand=True, padx=16, pady=10)
            ctk.CTkLabel(izq, text=f"{r.inicio:%H:%M}   {r.cliente}  ·  {r.servicio} con {r.estilista}",
                         font=f(15, "bold"), text_color=COLOR["texto"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(izq, text=item.mensaje, font=f(13), text_color=COLOR["suave"], anchor="w", justify="left",
                         wraplength=760).pack(anchor="w", pady=(4, 0))
            der = ctk.CTkFrame(tarjeta, fg_color="transparent")
            der.pack(side="right", padx=16)
            if r.recordatorio_enviado:
                ctk.CTkLabel(der, text="✓ Avisada", font=f(14, "bold"), text_color=COLOR["atendida"]).pack()
            else:
                ctk.CTkButton(der, text="Abrir WhatsApp", width=150, height=34, font=f(13, "bold"),
                              fg_color=COLOR["atendida"], command=lambda i=item: self.enviar(i)).pack(pady=2)
                ctk.CTkButton(der, text="Copiar texto", width=150, height=30, font=f(12), fg_color="#8a8088",
                              command=lambda i=item: self.copiar(i)).pack(pady=2)

    def enviar(self, item: logica.Recordatorio):
        self.app.abrir_whatsapp(item.enlace)
        logica.marcar_recordado(self.app.con, item.reserva.id)
        self.app.con.commit()
        self.llenar()
        self.app.avisar(f"WhatsApp abierto para {item.reserva.cliente}")

    def copiar(self, item: logica.Recordatorio):
        self.app.clipboard_clear()
        self.app.clipboard_append(item.mensaje)
        self.app.avisar("Texto copiado")


class VistaReporte(ctk.CTkFrame):
    def __init__(self, padre, app: App):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        primero = HOY.replace(day=1) - timedelta(days=1)  # por defecto, el último mes cerrado
        self.anio, self.mes = primero.year, primero.month
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(barra, text="◀", width=40, fg_color=COLOR["tarjeta"], text_color=COLOR["texto"],
                      hover_color=COLOR["linea"], command=lambda: self.mover(-1)).pack(side="left")
        self.titulo = ctk.CTkLabel(barra, text="", font=f(22, "bold"), text_color=COLOR["texto"], width=320)
        self.titulo.pack(side="left", padx=10)
        ctk.CTkButton(barra, text="▶", width=40, fg_color=COLOR["tarjeta"], text_color=COLOR["texto"],
                      hover_color=COLOR["linea"], command=lambda: self.mover(1)).pack(side="left")
        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True)
        self.llenar()

    def mover(self, n):
        m = self.mes + n
        self.anio, self.mes = self.anio + (m - 1) // 12, (m - 1) % 12 + 1
        self.llenar()

    def llenar(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()
        r = logica.reporte_mes(self.app.con, self.anio, self.mes)
        self.titulo.configure(text=f"Reporte de {MESES[self.mes - 1]} {self.anio}")
        tarjetas = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        tarjetas.pack(fill="x")
        datos = [("Ingresos", logica.pesos(r.ingresos), COLOR["texto"]),
                 ("Clientes atendidos", str(r.atendidas), COLOR["texto"]),
                 ("No vinieron", f"{r.no_vino}  ({r.tasa_inasistencia:.0%})", COLOR["no_vino"]),
                 ("Perdido por inasistencias", logica.pesos(r.perdido_por_inasistencias), COLOR["no_vino"])]
        for i, (titulo, valor, color) in enumerate(datos):
            t = ctk.CTkFrame(tarjetas, fg_color=COLOR["tarjeta"], corner_radius=12)
            t.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            tarjetas.columnconfigure(i, weight=1)
            ctk.CTkLabel(t, text=titulo, font=f(14), text_color=COLOR["suave"]).pack(anchor="w", padx=18, pady=(16, 2))
            ctk.CTkLabel(t, text=valor, font=f(28, "bold"), text_color=color).pack(anchor="w", padx=18, pady=(0, 16))
        abajo = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        abajo.pack(fill="both", expand=True, pady=(16, 0))
        for i, (titulo, serie) in enumerate((("Ingresos por servicio", r.por_servicio),
                                             ("Ingresos por terapeuta", r.por_estilista))):
            caja = ctk.CTkFrame(abajo, fg_color=COLOR["tarjeta"], corner_radius=12)
            caja.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            abajo.columnconfigure(i, weight=1)
            abajo.rowconfigure(0, weight=1)
            ctk.CTkLabel(caja, text=titulo, font=f(16, "bold"), text_color=COLOR["texto"]).pack(anchor="w", padx=18, pady=(16, 8))
            tope = max((v for _, v in serie), default=1)
            for nombre, valor in serie:
                fila = ctk.CTkFrame(caja, fg_color="transparent")
                fila.pack(fill="x", padx=18, pady=4)
                ctk.CTkLabel(fila, text=nombre, width=150, anchor="w", font=f(13), text_color=COLOR["texto"]).pack(side="left")
                barra = ctk.CTkProgressBar(fila, height=16, progress_color=COLOR["agendada"], fg_color=COLOR["linea"])
                barra.set(valor / tope)
                barra.pack(side="left", fill="x", expand=True, padx=8)
                ctk.CTkLabel(fila, text=logica.pesos(valor), width=110, anchor="e", font=f(13),
                             text_color=COLOR["texto"]).pack(side="left")


if __name__ == "__main__":
    App().mainloop()
