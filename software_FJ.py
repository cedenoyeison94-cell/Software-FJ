"""
====================================================================================================
PROYECTO: SISTEMA INTEGRAL DE GESTIÓN DE CLIENTES, SERVICIOS Y RESERVAS - SOFTWARE FJ
FASE 4: CALIDAD, ESTABILIDAD Y MANEJO DE ERRORES (SIN BASE DE DATOS)
----------------------------------------------------------------------------------------------------
PARTE 1 - ESTUDIANTE 1: MÓDULO BASE, JERARQUÍA DE EXCEPCIONES Y GESTOR DE LOGS
====================================================================================================
"""
from abc import ABC, abstractmethod
from datetime import datetime
import uuid
import traceback

class ErrorSoftwareFJ(Exception):
    """Excepción raíz para el dominio Software FJ."""
    def __init__(self, mensaje: str, codigo_error: str = "ERR-GEN-000"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo_error = codigo_error
        self.timestamp = datetime.now().isoformat()

    def __str__(self) -> str:
        return f"[{self.codigo_error}] {self.mensaje} (Ocurrido en: {self.timestamp})"

class ErrorClienteInvalido(ErrorSoftwareFJ):
    """Lanzada cuando los datos del cliente violan reglas de validación."""
    def __init__(self, mensaje: str, campo_afectado: str = "Desconocido"):
        super().__init__(mensaje, codigo_error="ERR-CLI-101")
        self.campo_afectado = campo_afectado

class ErrorServicioNoDisponible(ErrorSoftwareFJ):
    """Lanzada ante servicios inactivos o no encontrados."""
    def __init__(self, mensaje: str, servicio_id: str = "N/A"):
        super().__init__(mensaje, codigo_error="ERR-SRV-201")
        self.servicio_id = servicio_id

class ErrorCapacidadExcedida(ErrorSoftwareFJ):
    """Lanzada cuando la solicitud excede el aforo permitido."""
    def __init__(self, mensaje: str, aforo_maximo: int, aforo_solicitado: int):
        super().__init__(mensaje, codigo_error="ERR-CAP-202")
        self.aforo_maximo = aforo_maximo
        self.aforo_solicitado = aforo_solicitado

class ErrorFondosInsuficientes(ErrorSoftwareFJ):
    """Lanzada cuando el saldo del cliente no cubre el costo."""
    def __init__(self, mensaje: str, saldo_actual: float, monto_requerido: float):
        super().__init__(mensaje, codigo_error="ERR-SAL-301")
        self.saldo_actual = saldo_actual
        self.monto_requerido = monto_requerido

class ErrorFechaInvalida(ErrorSoftwareFJ):
    """Lanzada ante fechas en el pasado o con sintaxis errónea."""
    def __init__(self, mensaje: str, fecha_provista: str):
        super().__init__(mensaje, codigo_error="ERR-FEC-401")
        self.fecha_provista = fecha_provista

class ErrorReservaInvalida(ErrorSoftwareFJ):
    """Lanzada ante transiciones ilícitas o estados incompatibles."""
    def __init__(self, mensaje: str, estado_actual: str = "N/A"):
        super().__init__(mensaje, codigo_error="ERR-RES-501")
        self.estado_actual = estado_actual

class EntidadBase(ABC):
    """Clase abstracta con identificador único y auditoría."""
    def __init__(self, id_entidad: str = None):
        self.__id = id_entidad if id_entidad else str(uuid.uuid4())[:8].upper()
        self.__fecha_creacion = datetime.now()
        self.__activo = True

    @property
    def id(self) -> str:
        return self.__id

    @property
    def fecha_creacion(self) -> datetime:
        return self.__fecha_creacion

    @property
    def activo(self) -> bool:
        return self.__activo

    @activo.setter
    def activo(self, nuevo_estado: bool) -> None:
        if not isinstance(nuevo_estado, bool):
            raise ErrorSoftwareFJ("El estado activo debe ser un valor booleano.", "ERR-ENT-001")
        self.__activo = nuevo_estado

    @abstractmethod
    def validar_consistencia(self) -> bool:
        pass

class GestorLogs:
    """Manejador centralizado con bloque try/finally para archivos planos."""
    def __init__(self, nombre_archivo: str = "sistema_software_fj.log"):
        self.__nombre_archivo = nombre_archivo
        self.__buffer_logs = []

    def registrar_evento(self, nivel: str, origen: str, mensaje: str, excepcion: Exception = None) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        linea_log = f"[{timestamp}] [{nivel.upper():<7}] [{origen:<22}] {mensaje}"
        if excepcion is not None:
            linea_log += f" | EXCEPCIÓN: {type(excepcion).__name__} -> {str(excepcion)}"

        archivo_descriptor = None
        try:
            archivo_descriptor = open(self.__nombre_archivo, mode="a", encoding="utf-8")
            archivo_descriptor.write(linea_log + "\n")
            if nivel.upper() in ["ERROR", "CRITICAL"] and excepcion is not None:
                traza = traceback.format_exc()
                if "NoneType: None" not in traza:
                    archivo_descriptor.write("--- TRAZA DETALLADA ---\n" + traza + "-----------------------\n")
        except IOError as io_err:
            print(f"[ALERTA CRÍTICA GESTOR LOGS] Imposible escribir en archivo: {io_err}")
        finally:
            if archivo_descriptor is not None and not archivo_descriptor.closed:
                archivo_descriptor.close()

        self.__buffer_logs.append({
            "timestamp": timestamp,
            "nivel": nivel.upper(),
            "origen": origen,
            "mensaje": mensaje,
            "excepcion": type(excepcion).__name__ if excepcion else None,
            "linea_completa": linea_log
        })
        return linea_log

    def info(self, origen: str, mensaje: str): return self.registrar_evento("INFO", origen, mensaje)
        
    def warning(self, origen: str, mensaje: str): return self.registrar_evento("WARNING", origen, mensaje)
    def error(self, origen: str, mensaje: str, exc=None): return self.registrar_evento("ERROR", origen, mensaje, exc)
    def critical(self, origen: str, mensaje: str, exc=None): return self.registrar_evento("CRITICAL", origen, mensaje, exc)
    def obtener_historial_logs(self): return list(self.__buffer_logs)
