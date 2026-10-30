
import { useState } from "react";
import "../styles/ConsultarEnvio.css";

const API_URL = "http://127.0.0.1:8000/api/cambiar-estado-pedido/";

interface Paquete {
  id: number;
  cod_seguimiento: string;
  estado: "pendiente" | "en_camino" | "entregado" | "cancelado";
  tamanio: string;
  fecha_origen: string | null;
  fecha_destino: string | null;
  id_repartidor_asignado: number | null;
  id_comercio: number;
  id_cliente: number;
}

interface RespuestaAPI {
  message: string;
  paquetes: Paquete[];
}

const estados = [
  { valor: "pendiente", texto: "Pendiente" },
  { valor: "en_camino", texto: "En camino" },
  { valor: "entregado", texto: "Entregado" },
];

function formatearFecha(fecha: string | null): string {
  if (!fecha) return "Aún no registrada";

  const fechaLocal = new Date(fecha);

  if (Number.isNaN(fechaLocal.getTime())) return fecha;

  return fechaLocal.toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function ConsultarPaquete() {
  const [codigo, setCodigo] = useState("");
  const [paquete, setPaquete] = useState<Paquete | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  async function consultarPaquete(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const codigoLimpio = codigo.trim();

    if (!codigoLimpio) {
      setError("Ingresá tu código de seguimiento.");
      setPaquete(null);
      return;
    }

    setCargando(true);
    setError("");
    setPaquete(null);

    try {
      const respuesta = await fetch(
        `${API_URL}?cod_seguimiento=${encodeURIComponent(codigoLimpio)}`
      );

      if (!respuesta.ok) {
        throw new Error("No se pudo consultar el paquete.");
      }

      const data: RespuestaAPI = await respuesta.json();

      if (!data.paquetes || data.paquetes.length === 0) {
        setError("No encontramos ningún paquete con ese código.");
        return;
      }

      setPaquete(data.paquetes[0]);
    } catch {
      setError(
        "No se pudo conectar con el servidor. Intentá nuevamente más tarde."
      );
    } finally {
      setCargando(false);
    }
  }
    const estadoNormalizado = paquete?.estado
    ?.trim()
    .toLowerCase()
    .replace(/\s+/g, "_");

    const progresoPorEstado: Record<string, number> = {
    pendiente: 0,
    en_camino: 1,
    entregado: 2,
    };

    const estadoActual =
    estadoNormalizado !== undefined
        ? progresoPorEstado[estadoNormalizado] ?? -1
        : -1;

  const estadoTexto: Record<string, string> = {
    pendiente: "Pendiente",
    en_camino: "En camino",
    entregado: "Entregado",
    cancelado: "Cancelado",
  };

  return (
    <main className="consulta-pagina">
      <section className="consulta-contenedor">
        <header className="consulta-header">
          <span className="consulta-icono" aria-hidden="true">
            📦
          </span>

          <h1>Seguimiento de paquetes</h1>

          <p>
            Consultá el estado de tu envío ingresando el código de
            seguimiento que recibiste.
          </p>
        </header>

        <form className="consulta-formulario" onSubmit={consultarPaquete}>
          <label htmlFor="codigo-seguimiento">
            Código de seguimiento
          </label>

          <input
            id="codigo-seguimiento"
            type="text"
            placeholder="Ej.: SRFR-XXXX"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            autoComplete="off"
            required
          />

          <button type="submit" disabled={cargando}>
            {cargando ? "Consultando..." : "Consultar envío"}
          </button>
        </form>

        {error && (
          <div className="consulta-error" role="alert">
            {error}
          </div>
        )}

        {paquete && (
          <section className="resultado-paquete" aria-live="polite">
            <div className="resultado-cabecera">
              <div>
                <span className="resultado-etiqueta">
                  Código de seguimiento
                </span>
                <h2>{paquete.cod_seguimiento}</h2>
              </div>

              <span
                className={`estado-badge estado-${paquete.estado}`}
              >
                {estadoTexto[paquete.estado] ?? paquete.estado}
              </span>
            </div>

            {paquete.estado === "cancelado" ? (
              <div className="estado-cancelado">
                <span aria-hidden="true">✕</span>
                <div>
                  <strong>Envío cancelado</strong>
                  <p>
                    Este paquete fue cancelado. Contactá con el comercio
                    para obtener más información.
                  </p>
                </div>
              </div>
            ) : (
              <div className="progreso-envio">
                {estados.map((estado, indice) => {
                const completado = estadoActual >= indice && estadoActual !== -1;
                const actual = estadoActual === indice;

                return (
                    <div
                    key={estado.valor}
                    className={`progreso-paso ${
                        completado ? "completado" : ""
                    } ${actual ? "paso-actual" : ""}`}
                    >
                    <div className="progreso-marca">
                        {completado ? "✓" : indice + 1}
                    </div>

                    <span>{estado.texto}</span>

                    {indice < estados.length - 1 && (
                        <div className="progreso-linea" />
                    )}
                    </div>
                );
                })}
              </div>
            )}

            <div className="resultado-detalles">
              <h3>Información del envío</h3>

              <div className="detalle-item">
                <span>Tamaño del paquete</span>
                <strong>{paquete.tamanio || "No especificado"}</strong>
              </div>

              <div className="detalle-item">
                <span>Fecha de origen</span>
                <strong>{formatearFecha(paquete.fecha_origen)}</strong>
              </div>

              <div className="detalle-item">
                <span>Fecha de entrega prevista</span>
                <strong>
                  { formatearFecha(paquete.fecha_destino) }
                </strong>
              </div>

              <div className="detalle-item">
                <span>Repartidor asignado</span>
                <strong>
                  {paquete.id_repartidor_asignado !== null
                    ? "Asignado"
                    : "Aún sin asignar"}
                </strong>
              </div>
            </div>

            <p className="resultado-ayuda">
              Los datos se corresponden con la última información
              registrada en el sistema.
            </p>
          </section>
        )}
      </section>
    </main>
  );
}

export default ConsultarPaquete;
