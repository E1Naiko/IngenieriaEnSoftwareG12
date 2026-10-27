import { useEffect, useState } from "react";
//import "../styles/PaquetesEnCurso.css";

// Define la estructura que debe tener cada paquete recibido desde el backend.
interface Paquete {
  id: number;
  destinatario: string;
  direccion: string;
  repartidor: string;
  estado: string;
}

function PaquetesEnCurso() {
  // Guarda la lista de paquetes recibidos desde el backend.
  const [items, setItems] = useState<Paquete[]>([]);

  // Indica si se están cargando los paquetes.
  const [loading, setLoading] = useState(false);

  // Guarda un mensaje en caso de error.
  const [error, setError] = useState("");

  // Solicita al backend la lista de paquetes en curso.
  async function load() {
    setLoading(true);
    setError("");

    try {
      // Endpoint de ejemplo: debe coincidir con la URL configurada en Django.
      const res = await fetch("/api/dashboard/paquetes-en-curso/");

      // Comprueba si la petición fue exitosa.
      if (!res.ok) {
        throw new Error("No se pudieron cargar los paquetes");
      }

      // Convierte la respuesta JSON en un objeto JavaScript.
      const data = await res.json();

      // Guarda la lista recibida. Si no existe, utiliza una lista vacía.
      setItems(data.paquetes ?? []);
    } catch (e) {
      // Muestra el error ocurrido durante la petición.
      setError(
        e instanceof Error
          ? e.message
          : "Error al cargar los paquetes"
      );
    } finally {
      // Finaliza el estado de carga.
      setLoading(false);
    }
  }

  // Carga los paquetes cuando se muestra el componente.
  useEffect(() => {
    load();
  }, []);

  return (
    <main className="paquetes-container">
      {/* Encabezado de la página */}
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

      {/* Tarjeta principal */}
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

        {/* Estado de carga */}
        {loading && (
          <p
            className="paquetes-mensaje paquetes-cargando"
            role="status"
          >
            Cargando paquetes...
          </p>
        )}

        {/* Mensaje de error */}
        {error && (
          <p className="paquetes-error" role="alert">
            {error}
          </p>
        )}

        {/* Tabla de paquetes */}
        {!loading && !error && (
          <div className="paquetes-tabla-wrapper">
            <table className="paquetes-tabla">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Destinatario</th>
                  <th>Dirección</th>
                  <th>Repartidor asignado</th>
                  <th>Estado</th>
                </tr>
              </thead>

              <tbody>
                {items.map((paquete) => {
                  // Normaliza el estado para poder compararlo.
                  const estado = paquete.estado
                    .trim()
                    .toLowerCase();

                  // Asigna una clase CSS según el estado del paquete.
                  const claseEstado =
                    estado === "en curso" ||
                    estado === "en distribución" ||
                    estado === "en distribucion"
                      ? "paquetes-estado-curso"
                      : estado === "pendiente"
                        ? "paquetes-estado-pendiente"
                        : estado === "entregado"
                          ? "paquetes-estado-entregado"
                          : "paquetes-estado-otro";

                  return (
                    <tr key={paquete.id}>
                      <td className="paquetes-id">
                        #{paquete.id}
                      </td>

                      <td className="paquetes-destinatario">
                        {paquete.destinatario}
                      </td>

                      <td>{paquete.direccion}</td>

                      <td>{paquete.repartidor}</td>

                      <td>
                        <span
                          className={`paquetes-estado ${claseEstado}`}
                        >
                          {paquete.estado}
                        </span>
                      </td>
                    </tr>
                  );
                })}

                {/* Mensaje cuando no existen paquetes */}
                {items.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
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
    </main>
  );
}

// Permite importar el componente desde otros archivos de React.
export default PaquetesEnCurso;
