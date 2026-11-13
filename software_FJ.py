"""
PROYECTO: SISTEMA INTEGRAL DE GESTIÓN DE CLIENTES, SERVICIOS Y RESERVAS
SOFTWARE FJ - FASE 4
Versión integrada en un solo archivo, sin base de datos.
Ejecutar con: python software_fj.py
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import re
import uuid
import traceback


# ============================================================
# PARTE 1. EXCEPCIONES, ENTIDAD BASE Y GESTOR DE LOGS
# ============================================================

class ErrorSoftwareFJ(Exception):
    def __init__(self, mensaje, codigo_error="ERR-GEN-000"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo_error = codigo_error
        self.timestamp = datetime.now().isoformat(timespec="seconds")

    def __str__(self):
        return f"[{self.codigo_error}] {self.mensaje} (Ocurrido: {self.timestamp})"


class ErrorClienteInvalido(ErrorSoftwareFJ):
    def __init__(self, mensaje, campo_afectado="Desconocido"):
        super().__init__(mensaje, "ERR-CLI-101")
        self.campo_afectado = campo_afectado


class ErrorServicioNoDisponible(ErrorSoftwareFJ):
    def __init__(self, mensaje, servicio_id="N/A"):
        super().__init__(mensaje, "ERR-SRV-201")
        self.servicio_id = servicio_id


class ErrorCapacidadExcedida(ErrorSoftwareFJ):
    def __init__(self, mensaje, aforo_maximo, aforo_solicitado):
        super().__init__(mensaje, "ERR-CAP-202")
        self.aforo_maximo = aforo_maximo
        self.aforo_solicitado = aforo_solicitado


class ErrorFondosInsuficientes(ErrorSoftwareFJ):
    def __init__(self, mensaje, saldo_actual, monto_requerido):
        super().__init__(mensaje, "ERR-SAL-301")
        self.saldo_actual = saldo_actual
        self.monto_requerido = monto_requerido


class ErrorFechaInvalida(ErrorSoftwareFJ):
    def __init__(self, mensaje, fecha_provista):
        super().__init__(mensaje, "ERR-FEC-401")
        self.fecha_provista = fecha_provista


class ErrorReservaInvalida(ErrorSoftwareFJ):
    def __init__(self, mensaje, estado_actual="N/A"):
        super().__init__(mensaje, "ERR-RES-501")
        self.estado_actual = estado_actual


class EntidadBase(ABC):
    def __init__(self, id_entidad=None):
        self.__id = id_entidad or str(uuid.uuid4())[:8].upper()
        self.__fecha_creacion = datetime.now()
        self.__activo = True

    @property
    def id(self):
        return self.__id

    @property
    def fecha_creacion(self):
        return self.__fecha_creacion

    @property
    def activo(self):
        return self.__activo

    @activo.setter
    def activo(self, nuevo_estado):
        if not isinstance(nuevo_estado, bool):
            raise ErrorSoftwareFJ("El estado activo debe ser booleano.", "ERR-ENT-001")
        self.__activo = nuevo_estado

    @abstractmethod
    def validar_consistencia(self):
        pass


class GestorLogs:
    def __init__(self, nombre_archivo="sistema_software_fj.log"):
        self.nombre_archivo = nombre_archivo
        self.buffer_logs = []

    def registrar_evento(self, nivel, origen, mensaje, excepcion=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{timestamp}] [{nivel.upper():<8}] [{origen}] {mensaje}"
        if excepcion:
            linea += f" | EXCEPCIÓN: {type(excepcion).__name__}: {excepcion}"

        archivo = None
        try:
            archivo = open(self.nombre_archivo, "a", encoding="utf-8")
            archivo.write(linea + "\n")
            if excepcion and nivel.upper() in ("ERROR", "CRITICAL"):
                traza = traceback.format_exc()
                if "NoneType: None" not in traza:
                    archivo.write(traza + "\n")
        except OSError as error:
            print(f"ALERTA: no se pudo escribir el log: {error}")
        finally:
            if archivo is not None:
                archivo.close()

        self.buffer_logs.append({
            "timestamp": timestamp,
            "nivel": nivel.upper(),
            "origen": origen,
            "mensaje": mensaje
        })
        return linea

    def info(self, origen, mensaje):
        return self.registrar_evento("INFO", origen, mensaje)

    def warning(self, origen, mensaje):
        return self.registrar_evento("WARNING", origen, mensaje)

    def error(self, origen, mensaje, exc=None):
        return self.registrar_evento("ERROR", origen, mensaje, exc)

    def obtener_historial_logs(self):
        return list(self.buffer_logs)

# ============================================================
# PARTE 2. CLASE CLIENTE (Encapsulación y Validaciones)
# ============================================================

class Cliente(EntidadBase):
    def __init__(self, nombre, correo, telefono, saldo=0.0, id_entidad=None):
        super().__init__(id_entidad)
        self.nombre = nombre
        self.correo = correo
        self.telefono = telefono
        self.saldo = saldo

    @property
    def nombre(self):
        return self.__nombre

    @nombre.setter
    def nombre(self, valor):
        if not valor or not valor.strip():
            raise ErrorClienteInvalido("El nombre del cliente no puede estar vacío.", "nombre")
        self.__nombre = valor.strip()

    @property
    def correo(self):
        return self.__correo

    @correo.setter
    def correo(self, valor):
        patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(patron, valor):
            raise ErrorClienteInvalido(f"Formato de correo electrónico inválido: {valor}", "correo")
        self.__correo = valor.strip().lower()

    @property
    def telefono(self):
        return self.__telefono

    @telefono.setter
    def telefono(self, valor):
        if not valor.isdigit() or len(valor) < 7:
            raise ErrorClienteInvalido(f"Número de teléfono inválido: {valor}", "telefono")
        self.__telefono = valor.strip()

    @property
    def saldo(self):
        return self.__saldo

    @saldo.setter
    def saldo(self, valor):
        if valor < 0:
            raise ErrorClienteInvalido("El saldo inicial no puede ser negativo.", "saldo")
        self.__saldo = float(valor)

    def abonar_saldo(self, monto):
        if monto <= 0:
            raise ErrorClienteInvalido("El monto a abonar debe ser mayor que cero.")
        self.__saldo += float(monto)

    def descontar_saldo(self, monto):
        if monto > self.__saldo:
            raise ErrorFondosInsuficientes("Saldo insuficiente para completar la operación.", self.__saldo, monto)
        self.__saldo -= float(monto)

    def validar_consistencia(self):
        if not self.nombre or "@" not in self.correo:
            return False
        
        return True

    def __str__(self):
        return f"Cliente [{self.id}] - Nombre: {self.nombre} | Correo: {self.correo} | Saldo: ${self.saldo:.2f}"
        
# ============================================================
# PARTE 3. CLASE BASE SERVICIO Y SERVICIOS ESPECIALIZADOS
# ============================================================

class Servicio(EntidadBase):
    def __init__(self, nombre: str, tarifa_base: float, id_entidad=None):
        super().__init__(id_entidad)
        self.nombre = nombre
        self.tarifa_base = tarifa_base

    @property
    def tarifa_base(self):
        return self.__tarifa_base

    @tarifa_base.setter
    def tarifa_base(self, valor):
        if valor < 0:
            raise ErrorServicioNoDisponible("La tarifa base no puede ser negativa.")
        self.__tarifa_base = float(valor)

    @abstractmethod
    def calcular_costo(self, *args, **kwargs) -> float:
        """Método abstracto que implementa polimorfismo en las clases hijas."""
        pass

    @abstractmethod
    def obtener_descripcion(self) -> str:
        """Método abstracto para detallar las características del servicio."""
        pass

    def validar_consistencia(self):
        return bool(self.nombre and self.tarifa_base >= 0)


# Servicio especializado 1: Reserva de Salas
class ReservaSalas(Servicio):
    def __init__(self, nombre: str, tarifa_base: float, capacidad: int, id_entidad=None):
        super().__init__(nombre, tarifa_base, id_entidad)
        self.capacidad = capacidad

    def calcular_costo(self, horas: int, incluye_multimedia: bool = False) -> float:
        if horas <= 0:
            raise ErrorServicioNoDisponible("El número de horas debe ser mayor a cero.")
        costo = self.tarifa_base * horas
        if incluye_multimedia:
            costo += 50000  # Costo adicional por equipos multimedia
        return costo

    def obtener_descripcion(self) -> str:
        return f"Reserva de Sala: {self.nombre} (Capacidad máxima: {self.capacidad} personas)"


# Servicio especializado 2: Alquiler de Equipos
class AlquilerEquipos(Servicio):
    def __init__(self, nombre: str, tarifa_base: float, serial: str, id_entidad=None):
        super().__init__(nombre, tarifa_base, id_entidad)
        self.serial = serial

    def calcular_costo(self, dias: int) -> float:
        if dias <= 0:
            raise ErrorServicioNoDisponible("El número de días de alquiler debe ser mayor a cero.")
        costo = self.tarifa_base * dias
        if dias > 5:
            costo *= 0.90  # Descuento del 10% por alquileres mayores a 5 días
        return costo

    def obtener_descripcion(self) -> str:
        return f"Alquiler de Equipo: {self.nombre} (Serial: {self.serial})"


# Servicio especializado 3: Asesorías Especializadas
class AsesoriaEspecializada(Servicio):
    def __init__(self, nombre: str, tarifa_base: float, area: str, id_entidad=None):
        super().__init__(nombre, tarifa_base, id_entidad)
        self.area = area

    def calcular_costo(self, horas: int, nivel_senior: bool = False) -> float:
        if horas <= 0:
            raise ErrorServicioNoDisponible("Las horas de asesoría deben ser mayores a cero.")
        costo = self.tarifa_base * horas
        if nivel_senior:
            costo *= 1.25  # Incremento del 25% por asesor senior
        return costo

    def obtener_descripcion(self) -> str:
        return f"Asesoría Especializada en {self.area}: {self.nombre}"

# PARTE 4. CLASE RESERVA (Relaciones y Estados)

class Reserva(EntidadBase):
    ESTADOS_VALIDOS = ["PENDIENTE", "CONFIRMADA", "CANCELADA", "COMPLETADA"]

    def __init__(self, cliente: Cliente, servicio: Servicio, detalles_servicio: dict, id_entidad=None):
        super().__init__(id_entidad)
        self.cliente = cliente
        self.servicio = servicio
        self.detalles_servicio = detalles_servicio
        self.__estado = "PENDIENTE"
        
        # Calcular el costo total aplicando polimorfismo según el servicio
        if isinstance(servicio, ReservaSala):
            self.costo_total = servicio.calcular_costo(
                detalles_servicio.get("horas", 1), 
                detalles_servicio.get("asistentes", 1)
            )
        elif isinstance(servicio, AlquilerEquipos):
            self.costo_total = servicio.calcular_costo(
                detalles_servicio.get("dias", 1), 
                detalles_servicio.get("cantidad", 1)
            )
        elif isinstance(servicio, AsesoriaEspecializada):
            self.costo_total = servicio.calcular_costo(
                detalles_servicio.get("horas", 1)
            )
        else:
            self.costo_total = servicio.precio_base

    @property
    def estado(self):
        return self.__estado

    def cambiar_estado(self, nuevo_estado: str):
        nuevo_estado = nuevo_estado.upper()
        if nuevo_estado not in self.ESTADOS_VALIDOS:
            raise ErrorReservaInvalida(f"Estado de reserva no válido: {nuevo_estado}", self.__estado)
        self.__estado = nuevo_estado

    def validar_consistencia(self):
        return bool(self.cliente and self.servicio and self.costo_total >= 0)

    def __str__(self):
        return (f"Reserva [{self.id}] | Cliente: {self.cliente.nombre} | "
                f"Servicio: {self.servicio.nombre} | Total: ${self.costo_total:.2f} | Estado: {self.__estado}")
