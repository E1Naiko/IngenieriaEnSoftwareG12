import { useEffect, useState } from "react";
import "../styles/Comercios.css";

// Representa los datos de un comercio.
interface Comercio {
  id: number;
  nombre: string;
  telefono: string;
  direccion: string;
}

// Permite actualizar el listado desde el componente padre.
interface ComerciosProps {
  refreshKey?: number;
}

export default function Comercios({
  refreshKey = 0,
}: ComerciosProps) {
  // Almacena los comercios recibidos desde Django.
  const [items, setItems] = useState<Comercio[]>([]);

  // Controla el estado de carga y los posibles errores.
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Consulta la API para obtener los comercios registrados.
  async function load() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/comercios/");

      if (!res.ok) {
        throw new Error("No se pudieron cargar los comercios.");
      }

      const data = await res.json();

      // Admite respuestas como lista directa o paginada.
      setItems(Array.isArray(data) ? data : data.results ?? []);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Error al cargar comercios."
      );
    } finally {
      setLoading(false);
    }
  }

  // Carga los comercios al iniciar y cuando cambia refreshKey.
  useEffect(() => {
    load();
  }, [refreshKey]);

  return (
    <div className="comercios-container">
      {/* Encabezado de la sección */}
      <header className="comercios-header">
        <div>
          <h1 className="comercios-titulo">Comercios</h1>

          <p className="comercios-subtitulo">
            Consulta los comercios registrados en el sistema.
          </p>
        </div>
      <button
        className="comercios-boton"
        onClick={load}
        disabled={loading}
      >
        <span aria-hidden="true">↻</span>
        {loading ? "Actualizando..." : "Actualizar comercios"}
      </button>
      </header>

      {/* Tarjeta principal del listado */}
      <section className="comercios-card">
        <div className="comercios-toolbar">
          <h2 className="comercios-toolbar-titulo">
            Listado de comercios
          </h2>

          <span className="comercios-contador">
            Total: {items.length}
          </span>
        </div>

        {/* Estado de carga */}
        {loading && (
          <p className="comercios-mensaje comercios-cargando">
            Cargando comercios...
          </p>
        )}

        {/* Mensaje de error */}
        {!loading && error && (
          <p
            className="comercios-mensaje comercios-error"
            role="alert"
          >
            {error}
          </p>
        )}

        {/* Mensaje cuando no hay registros */}
        {!loading && !error && items.length === 0 && (
          <p className="comercios-mensaje comercios-vacio">
            No hay comercios registrados.
          </p>
        )}

        {/* Tabla de comercios */}
        {!loading && !error && items.length > 0 && (
          <div className="comercios-tabla-wrapper">
            <table className="comercios-tabla">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Teléfono</th>
                  <th>Dirección</th>
                </tr>
              </thead>

              <tbody>
                {items.map((comercio) => (
                  <tr key={comercio.id}>
                    <td className="comercios-id">
                      {comercio.id}
                    </td>

                    <td className="comercios-nombre">
                      {comercio.nombre}
                    </td>

                    <td className="comercios-telefono">
                      {comercio.telefono}
                    </td>

                    <td className="comercios-direccion">
                      {comercio.direccion}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}