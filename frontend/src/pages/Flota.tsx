import { useEffect, useState } from "react";
import "../styles/Flota.css";
import AsignarPaquete from "../components/asignarPaquete/AsignarPaquete";

// Define la estructura de cada repartidor recibido desde el backend.
interface Repartidor {
  id: number;
  nombre: string;
  apellido: string;
  dni: string;
  telefono: string;
  mail: string;
  tipo_vehiculo: string;
  estado: string;
  listado_id_pedidos_asignados: number[];
}

function Flota() {
  // Guarda la lista de repartidores.
  const [items, setItems] = useState<Repartidor[]>([]);

  // Indica si se están cargando los datos.
  const [loading, setLoading] = useState(false);

  // Guarda un mensaje de error.
  const [error, setError] = useState("");

  // Guarda el vehículo seleccionado en el filtro.
  const [vehiculoSeleccionado, setVehiculoSeleccionado] =
    useState("Todos");

  // Guarda el repartidor seleccionado para abrir el modal.
  const [repartidorSeleccionado, setRepartidorSeleccionado] =
    useState<Repartidor | null>(null);

  // Solicita al backend la lista de repartidores disponibles.
  async function load() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(
        "/api/dashboard/repartidores-disponibles/"
      );

      if (!res.ok) {
        throw new Error("No se pudo cargar la flota");
      }

      const data = await res.json();

      setItems(data.repartidores ?? []);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Error al cargar la flota"
      );
    } finally {
      setLoading(false);
    }
  }

  // Carga la flota cuando se monta el componente.
  useEffect(() => {
    load();
  }, []);

  // Obtiene los vehículos existentes sin duplicados.
  const vehiculos = [
    ...new Set(
      items
        .map((repartidor) =>
          repartidor.tipo_vehiculo?.trim()
        )
        .filter(
          (vehiculo): vehiculo is string =>
            Boolean(vehiculo)
        )
    ),
  ].sort((a, b) => a.localeCompare(b, "es"));

  // Filtra y ordena los repartidores por vehículo.
  const repartidoresOrdenados = [...items]
    .filter((repartidor) => {
      return (
        vehiculoSeleccionado === "Todos" ||
        repartidor.tipo_vehiculo?.trim() ===
          vehiculoSeleccionado
      );
    })
    .sort((a, b) =>
      (a.tipo_vehiculo ?? "").localeCompare(
        b.tipo_vehiculo ?? "",
        "es"
      )
    );

  return (
    <main className="flota-container">
      {/* Encabezado de la página */}
      <header className="flota-header">
        <div>
          <h1 className="flota-titulo">
            Flota disponible
          </h1>

          <p className="flota-subtitulo">
            Administración y seguimiento de repartidores.
          </p>
        </div>

        <button
          className="flota-boton"
          onClick={load}
          disabled={loading}
        >
          <span aria-hidden="true">↻</span>
          {loading ? "Actualizando..." : "Actualizar flota"}
        </button>
      </header>

      {/* Tarjeta principal */}
      <section className="flota-card">
        <div className="flota-toolbar">
          <h2 className="flota-toolbar-titulo">
            Listado de repartidores
          </h2>

          {/* Filtro por tipo de vehículo */}
          <label className="flota-filtro">
            <span>Filtrar por vehículo:</span>

            <select
              value={vehiculoSeleccionado}
              onChange={(e) =>
                setVehiculoSeleccionado(e.target.value)
              }
            >
              <option value="Todos">
                Todos los vehículos
              </option>

              {vehiculos.map((vehiculo) => (
                <option key={vehiculo} value={vehiculo}>
                  {vehiculo}
                </option>
              ))}
            </select>
          </label>

          {/* Contador de repartidores visibles */}
          <span className="flota-contador">
            {repartidoresOrdenados.length} repartidor
            {repartidoresOrdenados.length !== 1
              ? "es"
              : ""}
          </span>
        </div>

        {/* Estado de carga */}
        {loading && (
          <p
            className="flota-mensaje flota-cargando"
            role="status"
          >
            Cargando repartidores...
          </p>
        )}

        {/* Mensaje de error */}
        {error && (
          <p className="flota-error" role="alert">
            {error}
          </p>
        )}

        {/* Tabla de repartidores */}
        {!loading && !error && (
          <div className="flota-tabla-wrapper">
            <table className="flota-tabla">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Apellido</th>
                  <th>Vehículo</th>
                  <th>Teléfono</th>
                  <th>Estado</th>
                </tr>
              </thead>

              <tbody>
                {repartidoresOrdenados.map((repartidor) => {
                  // Normaliza el estado del repartidor.
                  const estado = (
                    repartidor.estado ?? ""
                  )
                    .trim()
                    .toLowerCase();

                  const claseEstado =
                    estado === "disponible" ||
                    estado === "activo"
                      ? "flota-estado-disponible"
                      : estado === "ocupado"
                        ? "flota-estado-ocupado"
                        : "flota-estado-inactivo";

                  return (
                    <tr
                      key={repartidor.id}
                      className="flota-fila-clicable"
                      onClick={() =>
                        setRepartidorSeleccionado(repartidor)
                      }
                      title="Ver pedidos sin asignar"
                    >
                      <td className="flota-id">
                        #{repartidor.id}
                      </td>

                      <td className="flota-nombre">
                        {repartidor.nombre}
                      </td>

                      <td>{repartidor.apellido}</td>

                      <td>
                        {repartidor.tipo_vehiculo || "—"}
                      </td>

                      <td>{repartidor.telefono}</td>

                      <td>
                        <span
                          className={`flota-estado ${claseEstado}`}
                        >
                          {repartidor.estado}
                        </span>
                      </td>
                    </tr>
                  );
                })}

                {/* Mensaje cuando no hay resultados */}
                {repartidoresOrdenados.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="flota-mensaje flota-vacio"
                    >
                      {items.length === 0
                        ? "No hay repartidores disponibles."
                        : "No hay repartidores para este vehículo."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Modal de pedidos sin asignar */}
      {repartidorSeleccionado && (
        <AsignarPaquete
          repartidor={repartidorSeleccionado}
          onClose={() => setRepartidorSeleccionado(null)}
        />
      )}
    </main>
  );
}

export default Flota;