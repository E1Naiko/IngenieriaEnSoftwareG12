import { useEffect, useState } from "react";
import "../styles/PaquetesEnCurso.css";

interface Paquete {
  id: number;
  destinatario: string;
  direccion: string;
  repartidor: string;
  estado: string;
  tamanio: string;
}

interface Repartidor {
  id: number;
  nombre: string;
  apellido: string;
  dni: string;
  telefono: string;
  mail: string;
  tipo_vehiculo: string;
  estado: string;
}

const ETIQUETAS_ESTADO: Record<string, string> = {
  pendiente: "Pendiente",
  retirado: "Retirado",
  en_camino: "En camino",
  entregado: "Entregado",
  cancelado: "Cancelado",
};

function PaquetesEnCurso() {
  const [items, setItems] = useState<Paquete[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Paquete seleccionado para asignarle un repartidor.
  const [paqueteSeleccionado, setPaqueteSeleccionado] =
    useState<Paquete | null>(null);

  // Repartidores devueltos por Django.
  const [repartidores, setRepartidores] = useState<Repartidor[]>([]);

  // Repartidor seleccionado en el modal.
  const [repartidorSeleccionado, setRepartidorSeleccionado] =
    useState("");

  const [loadingRepartidores, setLoadingRepartidores] = useState(false);
  const [asignando, setAsignando] = useState(false);
  const [errorModal, setErrorModal] = useState("");
  const [mensajeModal, setMensajeModal] = useState("");

  // Carga los paquetes.
  async function load() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/dashboard/paquetes-en-curso/");

      if (!res.ok) {
        throw new Error("No se pudieron cargar los paquetes.");
      }

      const data = await res.json();
      setItems(data.paquetes ?? []);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Error al cargar los paquetes."
      );
    } finally {
      setLoading(false);
    }
  }

  // Abre el modal y consulta los repartidores compatibles.
  async function abrirModal(paquete: Paquete) {
    setPaqueteSeleccionado(paquete);
    setRepartidores([]);
    setRepartidorSeleccionado("");
    setErrorModal("");
    setMensajeModal("");
    setLoadingRepartidores(true);

    try {
      const res = await fetch(
        `/api/dashboard/asignar-repartidor/?paquete=${paquete.id}`
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data.detail ||
          data.paquete ||
          "No se pudieron consultar los repartidores."
        );
      }

      setRepartidores(data.repartidores ?? []);

      if (data.mensaje) {
        setMensajeModal(data.mensaje);
      }
    } catch (e) {
      setErrorModal(
        e instanceof Error
          ? e.message
          : "Error al consultar los repartidores."
      );
    } finally {
      setLoadingRepartidores(false);
    }
  }

  // Asigna el repartidor seleccionado al paquete.
  async function asignarRepartidor() {
    if (!paqueteSeleccionado || !repartidorSeleccionado) {
      setErrorModal("Seleccioná un repartidor antes de continuar.");
      return;
    }

    setAsignando(true);
    setErrorModal("");

    try {
      const res = await fetch(
        "/api/dashboard/asignar-repartidor/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            paquete: paqueteSeleccionado.id,
            repartidor: Number(repartidorSeleccionado),
          }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data.detail ||
          data.repartidor ||
          data.paquete ||
          "No se pudo asignar el repartidor."
        );
      }

      // Cierra el modal y actualiza la información.
      cerrarModal();
      await load();

    } catch (e) {
      setErrorModal(
        e instanceof Error
          ? e.message
          : "Error al asignar el repartidor."
      );
    } finally {
      setAsignando(false);
    }
  }

  // Limpia los datos del modal.
  function cerrarModal() {
    setPaqueteSeleccionado(null);
    setRepartidores([]);
    setRepartidorSeleccionado("");
    setErrorModal("");
    setMensajeModal("");
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="paquetes-container">

      <header className="paquetes-header">
        <div>
          <h1 className="paquetes-titulo">
            Paquetes en curso
          </h1>

          <p className="paquetes-subtitulo">
            Seguimiento y consulta de los paquetes en distribución.
          </p>
        </div>

        <button
          className="paquetes-boton"
          onClick={load}
          disabled={loading}
        >
          <span aria-hidden="true">↻</span>
          {loading ? "Actualizando..." : "Actualizar paquetes"}
        </button>
      </header>

      <section className="paquetes-card">

        <div className="paquetes-toolbar">
          <h2 className="paquetes-toolbar-titulo">
            Listado de paquetes
          </h2>

          <span className="paquetes-contador">
            {items.length} paquete
            {items.length !== 1 ? "s" : ""}
          </span>
        </div>

        {loading && (
          <p className="paquetes-mensaje paquetes-cargando">
            Cargando paquetes...
          </p>
        )}

        {error && (
          <p className="paquetes-error" role="alert">
            {error}
          </p>
        )}

        {!loading && !error && (
          <div className="paquetes-tabla-wrapper">
            <table className="paquetes-tabla">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Destinatario</th>
                  <th>Dirección</th>
                  <th>Tamaño</th>
                  <th>Repartidor asignado</th>
                  <th>Estado</th>
                </tr>
              </thead>

              <tbody>
                {items.map((paquete) => {
                  const estado = (paquete.estado ?? "")
                    .trim()
                    .toLowerCase();

                  const claseEstado =
                    estado === "en curso" ||
                    estado === "en distribución" ||
                    estado === "en distribucion" ||
                    estado === "en_camino" ||
                    estado === "retirado"
                      ? "paquetes-estado-curso"
                      : estado === "pendiente"
                        ? "paquetes-estado-pendiente"
                        : estado === "entregado"
                          ? "paquetes-estado-entregado"
                          : "paquetes-estado-otro";

                  return (
                    <tr
                      key={paquete.id}
                      className="paquetes-fila-click"
                      onClick={() => abrirModal(paquete)}
                      title="Hacé clic para gestionar el repartidor"
                    >
                      <td className="paquetes-id">
                        #{paquete.id}
                      </td>

                      <td className="paquetes-destinatario">
                        {paquete.destinatario}
                      </td>

                      <td>{paquete.direccion}</td>

                      <td>{paquete.tamanio}</td>

                      <td>{paquete.repartidor || "Sin asignar"}</td>

                      <td>
                        <span
                          className={`paquetes-estado ${claseEstado}`}
                        >
                          {ETIQUETAS_ESTADO[estado] ?? paquete.estado}
                        </span>
                      </td>
                    </tr>
                  );
                })}

                {items.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="paquetes-mensaje paquetes-vacio"
                    >
                      No hay paquetes en curso.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* MODAL DE ASIGNACIÓN */}
      {paqueteSeleccionado && (
        <div
          className="asignar-modal-overlay"
          onClick={cerrarModal}
        >
          <section
            className="asignar-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="asignar-modal-header">
              <div>
                <h2>Asignar repartidor</h2>
                <p>
                  Paquete #{paqueteSeleccionado.id}
                </p>
              </div>

              <button
                className="asignar-modal-cerrar"
                onClick={cerrarModal}
                aria-label="Cerrar modal"
              >
                ×
              </button>
            </header>

            <div className="asignar-modal-contenido">

              <div className="asignar-paquete-info">
                <div>
                  <span>Destinatario</span>
                  <strong>
                    {paqueteSeleccionado.destinatario}
                  </strong>
                </div>

                <div>
                  <span>Dirección</span>
                  <strong>
                    {paqueteSeleccionado.direccion}
                  </strong>
                </div>

                <div>
                  <span>Tamaño del paquete</span>
                  <strong>
                    {paqueteSeleccionado.tamanio}
                  </strong>
                </div>

                <div>
                  <span>Repartidor actual</span>
                  <strong>
                    {paqueteSeleccionado.repartidor || "Sin asignar"}
                  </strong>
                </div>
              </div>

              <div className="asignar-separador" />

              <h3>Repartidores disponibles</h3>

              <p className="asignar-descripcion">
                Se muestran únicamente los repartidores disponibles
                cuyo vehículo puede transportar este paquete.
              </p>

              {loadingRepartidores && (
                <p className="asignar-mensaje">
                  Buscando repartidores compatibles...
                </p>
              )}

              {!loadingRepartidores && errorModal && (
                <p className="asignar-error" role="alert">
                  {errorModal}
                </p>
              )}

              {!loadingRepartidores &&
                !errorModal &&
                repartidores.length > 0 && (
                  <div className="asignar-selector-container">
                    <label htmlFor="repartidor-select">
                      Seleccionar repartidor
                    </label>

                    <select
                      id="repartidor-select"
                      value={repartidorSeleccionado}
                      onChange={(e) =>
                        setRepartidorSeleccionado(e.target.value)
                      }
                    >
                      <option value="">
                        Seleccioná un repartidor
                      </option>

                      {repartidores.map((repartidor) => (
                        <option
                          key={repartidor.id}
                          value={repartidor.id}
                        >
                          {repartidor.nombre} {repartidor.apellido}
                          {" — "}
                          {repartidor.tipo_vehiculo}
                          {" — DNI: "}
                          {repartidor.dni}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

              {!loadingRepartidores &&
                !errorModal &&
                repartidores.length === 0 && (
                  <p className="asignar-sin-resultados">
                    {mensajeModal ||
                      "No hay repartidores disponibles para este paquete."}
                  </p>
                )}

              {errorModal && (
                <p className="asignar-error" role="alert">
                  {errorModal}
                </p>
              )}

            </div>

            <footer className="asignar-modal-footer">
              <button
                className="asignar-btn-cancelar"
                onClick={cerrarModal}
                disabled={asignando}
              >
                Cancelar
              </button>

              <button
                className="asignar-btn-confirmar"
                onClick={asignarRepartidor}
                disabled={
                  !repartidorSeleccionado ||
                  asignando ||
                  loadingRepartidores ||
                  repartidores.length === 0
                }
              >
                {asignando
                  ? "Asignando..."
                  : "Confirmar asignación"}
              </button>
            </footer>
          </section>
        </div>
      )}

    </main>
  );
}

export default PaquetesEnCurso;