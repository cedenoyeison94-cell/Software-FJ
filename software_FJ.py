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
# PARTE 2. CLIENTES
# ============================================================

class Cliente(EntidadBase):
    PATRON_CORREO = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    PATRON_TELEFONO = re.compile(r"^\+?[0-9]{7,15}$")
    TIPOS_PERMITIDOS = ("REGULAR", "VIP", "CORPORATIVO")

    def __init__(self, documento_id, nombre_completo, correo, telefono,
                 saldo_inicial=0.0, tipo_cliente="REGULAR", id_entidad=None):
        super().__init__(id_entidad)
        self.__documento_id = ""
        self.__nombre_completo = ""
        self.__correo = ""
        self.__telefono = ""
        self.__saldo_cuenta = 0.0
        self.__tipo_cliente = "REGULAR"

        self.documento_id = documento_id
        self.nombre_completo = nombre_completo
        self.correo = correo
        self.telefono = telefono
        self.saldo_cuenta = saldo_inicial
        self.tipo_cliente = tipo_cliente

    @property
    def documento_id(self):
        return self.__documento_id

    @documento_id.setter
    def documento_id(self, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 5:
            raise ErrorClienteInvalido("Documento inválido: mínimo 5 caracteres.", "documento_id")
        self.__documento_id = valor.strip().upper()

    @property
    def nombre_completo(self):
        return self.__nombre_completo

    @nombre_completo.setter
    def nombre_completo(self, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ErrorClienteInvalido("El nombre requiere al menos 3 caracteres.", "nombre")
        self.__nombre_completo = valor.strip().title()

    @property
    def correo(self):
        return self.__correo

    @correo.setter
    def correo(self, valor):
        if not isinstance(valor, str) or not self.PATRON_CORREO.match(valor.strip()):
            raise ErrorClienteInvalido("Correo electrónico inválido.", "correo")
        self.__correo = valor.strip().lower()

    @property
    def telefono(self):
        return self.__telefono

    @telefono.setter
    def telefono(self, valor):
        limpio = re.sub(r"[\s-]", "", valor) if isinstance(valor, str) else ""
        if not self.PATRON_TELEFONO.match(limpio):
            raise ErrorClienteInvalido("Teléfono inválido: use entre 7 y 15 dígitos.", "telefono")
        self.__telefono = limpio

    @property
    def saldo_cuenta(self):
        return self.__saldo_cuenta

    @saldo_cuenta.setter
    def saldo_cuenta(self, valor):
        if not isinstance(valor, (int, float)) or isinstance(valor, bool) or valor < 0:
            raise ErrorClienteInvalido("El saldo debe ser numérico y no negativo.", "saldo")
        self.__saldo_cuenta = round(float(valor), 2)

    @property
    def tipo_cliente(self):
        return self.__tipo_cliente

    @tipo_cliente.setter
    def tipo_cliente(self, valor):
        tipo = str(valor).upper()
        if tipo not in self.TIPOS_PERMITIDOS:
            raise ErrorClienteInvalido("Tipo de cliente no permitido.", "tipo_cliente")
        self.__tipo_cliente = tipo

    def acreditar_saldo(self, monto):
        if not isinstance(monto, (int, float)) or monto <= 0:
            raise ErrorClienteInvalido("La recarga debe ser mayor que cero.", "recarga")
        self.__saldo_cuenta = round(self.__saldo_cuenta + float(monto), 2)
        return self.__saldo_cuenta

    def debitar_saldo(self, monto):
        if not isinstance(monto, (int, float)) or monto <= 0:
            raise ErrorClienteInvalido("El débito debe ser mayor que cero.", "debito")
        if monto > self.__saldo_cuenta:
            raise ErrorFondosInsuficientes(
                f"Saldo insuficiente para {self.nombre_completo}.",
                self.__saldo_cuenta, monto
            )
        self.__saldo_cuenta = round(self.__saldo_cuenta - float(monto), 2)
        return self.__saldo_cuenta

    def validar_consistencia(self):
        return bool(self.__documento_id and self.__correo and self.__saldo_cuenta >= 0)


# ============================================================
# PARTE 3. SERVICIOS Y POLIMORFISMO
# ============================================================

class Servicio(EntidadBase):
    def __init__(self, nombre, descripcion, tarifa_base, id_entidad=None):
        super().__init__(id_entidad)
        if not nombre or len(str(nombre).strip()) < 3:
            raise ErrorSoftwareFJ("Nombre de servicio demasiado corto.", "ERR-SRV-001")
        if not isinstance(tarifa_base, (int, float)) or tarifa_base < 0:
            raise ErrorSoftwareFJ("La tarifa debe ser numérica y no negativa.", "ERR-SRV-002")
        self._nombre = str(nombre).strip()
        self._descripcion = str(descripcion).strip()
        self._tarifa_base = float(tarifa_base)
        self._disponible = True

    @property
    def nombre(self):
        return self._nombre

    @property
    def disponible(self):
        return self._disponible

    @disponible.setter
    def disponible(self, valor):
        if not isinstance(valor, bool):
            raise ErrorSoftwareFJ("La disponibilidad debe ser booleana.")
        self._disponible = valor

    @abstractmethod
    def calcular_costo_base(self, unidades):
        pass

    @abstractmethod
    def describir_servicio(self):
        pass

    @abstractmethod
    def validar_parametros(self, **kwargs):
        pass

    def calcular_costo_total(self, unidades, aplicar_iva=True,
                             porcentaje_descuento=0.0, recargo_urgencia=0.0):
        if not isinstance(unidades, int) or unidades <= 0:
            raise ErrorSoftwareFJ("Las unidades deben ser un entero mayor que cero.")
        if not self._disponible:
            raise ErrorServicioNoDisponible(f"Servicio '{self._nombre}' no disponible.", self.id)
        subtotal = self.calcular_costo_base(unidades)
        descuento = subtotal * (porcentaje_descuento / 100)
        base = subtotal - descuento + max(0.0, recargo_urgencia)
        iva = base * (0.19 if aplicar_iva else 0)
        return {
            "subtotal_base": round(subtotal, 2),
            "descuento": round(descuento, 2),
            "recargo_urgencia": round(max(0.0, recargo_urgencia), 2),
            "iva": round(iva, 2),
            "total_a_pagar": round(base + iva, 2)
        }

    def validar_consistencia(self):
        return self._tarifa_base >= 0 and bool(self._nombre)


class ReservaSala(Servicio):
    def __init__(self, nombre, descripcion, tarifa_hora, capacidad_maxima,
                 incluye_audiovisual=True, tasa_limpieza=25000.0):
        super().__init__(nombre, descripcion, tarifa_hora)
        if capacidad_maxima <= 0:
            raise ErrorSoftwareFJ("La capacidad debe ser mayor que cero.")
        self.__capacidad_maxima = capacidad_maxima
        self.__incluye_audiovisual = incluye_audiovisual
        self.__tasa_limpieza = float(tasa_limpieza)

    def calcular_costo_base(self, unidades):
        costo = self._tarifa_base * unidades
        suplemento = costo * 0.10 if self.__incluye_audiovisual else 0
        return costo + suplemento + self.__tasa_limpieza

    def validar_parametros(self, **kwargs):
        asistentes = kwargs.get("asistentes", 1)
        if asistentes > self.__capacidad_maxima:
            raise ErrorCapacidadExcedida(
                f"Capacidad máxima {self.__capacidad_maxima}; solicitados {asistentes}.",
                self.__capacidad_maxima, asistentes
            )
        return True

    def describir_servicio(self):
        return f"SALA: {self._nombre} | Aforo: {self.__capacidad_maxima} | Tarifa/hora: ${self._tarifa_base:,.0f}"


class AlquilerEquipo(Servicio):
    def __init__(self, nombre, descripcion, tarifa_diaria, numero_serie,
                 deposito_garantia=100000.0, seguro_todo_riesgo=15000.0):
        super().__init__(nombre, descripcion, tarifa_diaria)
        self.__numero_serie = str(numero_serie).strip().upper()
        self.__deposito_garantia = float(deposito_garantia)
        self.__seguro_todo_riesgo = float(seguro_todo_riesgo)

    def calcular_costo_base(self, unidades):
        return (self._tarifa_base + self.__seguro_todo_riesgo) * unidades + self.__deposito_garantia

    def validar_parametros(self, **kwargs):
        dias = kwargs.get("dias", 1)
        if not isinstance(dias, int) or not 1 <= dias <= 30:
            raise ErrorSoftwareFJ("El alquiler debe ser de 1 a 30 días.")
        return True

    def describir_servicio(self):
        return f"EQUIPO: {self._nombre} | Serie: {self.__numero_serie} | Tarifa/día: ${self._tarifa_base:,.0f}"


class AsesoriaEspecializada(Servicio):
    FACTORES = {"JUNIOR": 1.0, "SENIOR": 1.45, "MASTER": 2.10}

    def __init__(self, nombre, descripcion, tarifa_hora_base,
                 nivel_consultor="SENIOR", modalidad="VIRTUAL", area_tematica="Software"):
        super().__init__(nombre, descripcion, tarifa_hora_base)
        self.__nivel = nivel_consultor.upper()
        self.__modalidad = modalidad.upper()
        self.__area = area_tematica
        if self.__nivel not in self.FACTORES:
            raise ErrorSoftwareFJ("Nivel de consultor inválido.")

    def calcular_costo_base(self, unidades):
        total = self._tarifa_base * self.FACTORES[self.__nivel] * unidades
        if self.__modalidad == "PRESENCIAL":
            total += 35000
        return total

    def validar_parametros(self, **kwargs):
        horas = kwargs.get("horas", 1)
        if not isinstance(horas, int) or horas < 1:
            raise ErrorSoftwareFJ("La asesoría requiere mínimo una hora.")
        return True

    def describir_servicio(self):
        return f"ASESORÍA: {self._nombre} | Área: {self.__area} | Nivel: {self.__nivel} | Modalidad: {self.__modalidad}"


# ============================================================
# PARTE 4. RESERVAS Y MÁQUINA DE ESTADOS
# ============================================================

class Reserva(EntidadBase):
    def __init__(self, cliente, servicio, fecha_inicio, duracion_unidades,
                 parametros_especiales=None, gestor_logs=None):
        super().__init__()
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise ErrorReservaInvalida("Cliente y servicio deben ser objetos válidos.")
        if not isinstance(duracion_unidades, int) or duracion_unidades <= 0:
            raise ErrorReservaInvalida("La duración debe ser un entero positivo.")
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion_unidades = duracion_unidades
        self.__gestor_logs = gestor_logs
        self.__fecha_inicio = self._validar_y_parsear_fecha(fecha_inicio)
        self.__servicio.validar_parametros(**(parametros_especiales or {}))
        self.__estado = "PENDIENTE"
        descuento = 15 if cliente.tipo_cliente == "VIP" else 10 if cliente.tipo_cliente == "CORPORATIVO" else 0
        self.__desglose = servicio.calcular_costo_total(duracion_unidades, True, descuento)

    @property
    def cliente(self):
        return self.__cliente

    @property
    def servicio(self):
        return self.__servicio

    @property
    def estado(self):
        return self.__estado

    @property
    def total_a_pagar(self):
        return self.__desglose["total_a_pagar"]

    def _validar_y_parsear_fecha(self, fecha_str):
        try:
            formato = "%Y-%m-%d %H:%M" if " " in fecha_str else "%Y-%m-%d"
            fecha = datetime.strptime(fecha_str.strip(), formato)
        except (ValueError, AttributeError) as exc:
            raise ErrorFechaInvalida(f"Fecha inválida: {fecha_str}", str(fecha_str)) from exc
        if fecha.date() < datetime.now().date():
            raise ErrorFechaInvalida("La fecha no puede estar en el pasado.", fecha_str)
        return fecha

    def confirmar_reserva(self):
        if self.__estado != "PENDIENTE":
            raise ErrorReservaInvalida(f"No se puede confirmar desde {self.__estado}.", self.__estado)
        if not self.__servicio.disponible:
            raise ErrorServicioNoDisponible("El servicio no está disponible.", self.__servicio.id)
        monto = self.total_a_pagar
        try:
            self.__cliente.debitar_saldo(monto)
        except ErrorFondosInsuficientes as exc:
            if self.__gestor_logs:
                self.__gestor_logs.error("Reserva.confirmar", "Fondos insuficientes", exc)
            raise ErrorReservaInvalida("Reserva rechazada por saldo insuficiente.", self.__estado) from exc
        else:
            self.__estado = "CONFIRMADA"
            if self.__gestor_logs:
                self.__gestor_logs.info("Reserva.confirmar", f"Reserva {self.id} confirmada.")
        finally:
            if self.__gestor_logs:
                self.__gestor_logs.info("Reserva.confirmar", f"Estado final: {self.__estado}")
        return True

    def cancelar_reserva(self, motivo="Solicitado por usuario"):
        if self.__estado in ("FINALIZADA", "CANCELADA"):
            raise ErrorReservaInvalida(f"No se puede cancelar desde {self.__estado}.", self.__estado)
        try:
            if self.__estado == "CONFIRMADA":
                self.__cliente.acreditar_saldo(self.total_a_pagar)
            self.__estado = "CANCELADA"
            if self.__gestor_logs:
                self.__gestor_logs.warning("Reserva.cancelar", motivo)
            return True
        finally:
            if self.__gestor_logs:
                self.__gestor_logs.info("Reserva.cancelar", f"Estado final: {self.__estado}")

    def procesar_finalizacion(self):
        if self.__estado != "CONFIRMADA":
            raise ErrorReservaInvalida("Solo se pueden finalizar reservas confirmadas.")
        self.__estado = "FINALIZADA"
        return True

    def validar_consistencia(self):
        return self.__cliente is not None and self.__servicio is not None and self.__duracion_unidades > 0


# ============================================================
# PARTE 5. SISTEMA INTEGRAL Y SIMULACIÓN DE 10 OPERACIONES
# ============================================================

def main():
    logs = GestorLogs()
    print("=" * 68)
    print("       SOFTWARE FJ - SISTEMA DE GESTIÓN INTEGRAL")
    print("=" * 68)

    # Operación 1: creación de clientes
    cliente1 = Cliente("12345678", "Ana Gómez", "ana@gmail.com", "3001234567",
                       3000000, "VIP")
    cliente2 = Cliente("87654321", "Carlos Pérez", "carlos@gmail.com", "3107654321",
                       2500000, "REGULAR")
    logs.info("Sistema", "Se crearon dos clientes.")
    print("\n1. Clientes registrados:")
    print(f"   {cliente1.nombre_completo} | Tipo: {cliente1.tipo_cliente} | Saldo: ${cliente1.saldo_cuenta:,.0f}")
    print(f"   {cliente2.nombre_completo} | Tipo: {cliente2.tipo_cliente} | Saldo: ${cliente2.saldo_cuenta:,.0f}")

    # Operación 2: creación de servicios
    sala = ReservaSala("Sala de reuniones", "Sala con proyector", 80000, 20)
    equipo = AlquilerEquipo("Portátil", "Equipo portátil", 90000, "PC-2026-01")
    asesoria = AsesoriaEspecializada("Asesoría tecnológica", "Consultoría de software", 100000)
    servicios = [sala, equipo, asesoria]
    logs.info("Sistema", "Se registraron tres servicios.")
    print("\n2. Servicios disponibles:")
    for servicio in servicios:
        print("  ", servicio.describir_servicio())

    # Operación 3: recarga de saldo
    cliente2.acreditar_saldo(200000)
    print(f"\n3. Recarga realizada a {cliente2.nombre_completo}. Nuevo saldo: ${cliente2.saldo_cuenta:,.0f}")

    # Operación 4: cálculo polimórfico de costos
    print("\n4. Cálculo de costos (polimorfismo):")
    for servicio in servicios:
        unidades = 2
        print(f"   {servicio.nombre}: ${servicio.calcular_costo_total(unidades)['total_a_pagar']:,.0f}")

    # Operación 5: reserva de sala
    fecha = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
    reserva1 = Reserva(cliente1, sala, fecha, 2, {"asistentes": 12}, logs)
    print(f"\n5. Reserva de sala creada: {reserva1.id} | Total: ${reserva1.total_a_pagar:,.0f}")

    # Operación 6: confirmación y débito
    reserva1.confirmar_reserva()
    print(f"\n6. Reserva {reserva1.id}: {reserva1.estado}. Saldo de Ana: ${cliente1.saldo_cuenta:,.0f}")

    # Operación 7: reserva y confirmación de equipo
    reserva2 = Reserva(cliente2, equipo, fecha, 2, {"dias": 2}, logs)
    reserva2.confirmar_reserva()
    print(f"\n7. Alquiler confirmado: {reserva2.id} | Total: ${reserva2.total_a_pagar:,.0f}")

    # Operación 8: cancelación con reembolso
    reserva2.cancelar_reserva("Cancelación de demostración")
    print(f"\n8. Reserva de equipo: {reserva2.estado}. Saldo de Carlos: ${cliente2.saldo_cuenta:,.0f}")

    # Operación 9: demostración de excepción controlada
    print("\n9. Prueba de manejo de errores:")
    try:
        sala.validar_parametros(asistentes=30)
    except ErrorCapacidadExcedida as exc:
        logs.error("Prueba.capacidad", "Se detectó exceso de aforo", exc)
        print(f"   Error controlado: {exc}")

    # Operación 10: validación y resumen de logs
    print("\n10. Validación final y registro de eventos:")
    print(f"   Cliente 1 consistente: {cliente1.validar_consistencia()}")
    print(f"   Cliente 2 consistente: {cliente2.validar_consistencia()}")
    print(f"   Reserva 1 consistente: {reserva1.validar_consistencia()}")
    print(f"   Eventos registrados: {len(logs.obtener_historial_logs())}")
    print(f"   Archivo de auditoría: {logs.nombre_archivo}")

    print("\n" + "=" * 68)
    print("SIMULACIÓN FINALIZADA CORRECTAMENTE")
    print("=" * 68)


if __name__ == "__main__":
    try:
        main()
    except ErrorSoftwareFJ as error:
        print(f"\nERROR DEL SISTEMA: {error}")
    except Exception as error:
        print(f"\nERROR INESPERADO: {error}")
        traceback.print_exc()
