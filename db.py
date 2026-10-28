"""Base de datos SQLite: un solo archivo junto a la app, más respaldos automáticos."""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    telefono TEXT NOT NULL UNIQUE,
    notas TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    estilista TEXT NOT NULL,
    servicio TEXT NOT NULL,
    inicio TEXT NOT NULL,   -- 'YYYY-MM-DD HH:MM'
    fin TEXT NOT NULL,
    precio INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'agendada'
        CHECK (estado IN ('agendada', 'atendida', 'no_vino', 'cancelada')),
    recordatorio_enviado INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_reservas_inicio ON reservas(inicio);
"""


def conectar(ruta: Path) -> sqlite3.Connection:
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


def respaldar(ruta: Path, carpeta: Path, conservar: int = 30) -> Path:
    """Copia la base a respaldos/ con fecha y hora en el nombre. Conserva los últimos `conservar`."""
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / f"reservas_{datetime.now():%Y-%m-%d_%H%M%S}.db"
    with sqlite3.connect(ruta) as origen, sqlite3.connect(destino) as copia:
        origen.backup(copia)  # copia consistente aunque la app esté escribiendo
    for viejo in sorted(carpeta.glob("reservas_*.db"))[:-conservar]:
        viejo.unlink()
    return destino


def exportar_copia(ruta: Path, destino: Path) -> None:
    shutil.copy2(ruta, destino)
