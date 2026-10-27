
import { useEffect, useState } from "react";
import "../styles/Flota.css";

// Define la estructura que debe tener cada repartidor recibido desde el backend.
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
  // Guarda la lista de repartidores que se reciben desde el backend.
  // Inicialmente, la lista está vacía.
  const [items, setItems] = useState<Repartidor[]>([]);

  // Indica si se está realizando una petición para cargar los datos.
  // Inicialmente, no se está cargando nada.
  const [loading, setLoading] = useState(false);

  // Guarda un mensaje de error si ocurre algún problema al obtener los datos.
  const [error, setError] = useState("");

  // Función asíncrona que solicita al backend la lista de repartidores disponibles.
  async function load() {
    // Indica que comenzó la carga de los datos.
    setLoading(true);

    // Limpia cualquier error anterior antes de realizar una nueva petición.
    setError("");

    try {
      // Realiza una petición HTTP GET al endpoint de Django.
      const res = await fetch("/api/dashboard/repartidores-disponibles/");

      // Comprueba si la respuesta HTTP fue exitosa.
      // Si no lo fue, genera un error que será capturado por catch.
      if (!res.ok) {
        throw new Error("No se pudo cargar la flota");
      }

      // Convierte el cuerpo de la respuesta HTTP de JSON a un objeto JavaScript.
      const data = await res.json();

      // Guarda los repartidores recibidos en el estado items.
      // Si data.repartidores no existe o es null, utiliza una lista vacía.
      setItems(data.repartidores ?? []);

    } catch (e) {
      // Captura los errores que ocurran durante la petición o el procesamiento.
      // Si el error es una instancia de Error, muestra su mensaje.
      // De lo contrario, muestra un mensaje genérico.
      setError(
        e instanceof Error ? e.message : "Error al cargar la flota"
      );

    } finally {
      // Se ejecuta tanto si la petición tiene éxito como si ocurre un error.
      // Indica que el proceso de carga terminó.
      setLoading(false);
    }
  }

  // useEffect ejecuta este código cuando el componente se monta.
  // El arreglo vacío [] indica que no debe volver a ejecutarse
  // por cambios normales en el estado o las propiedades del componente.
  useEffect(() => {
    // Solicita la lista de repartidores al cargar la pantalla.
    load();
  }, []);

  // Devuelve la interfaz que se mostrará en pantalla.
  
return (
  <main className="flota-container">
    {/* Encabezado de la página */}
    <header className="flota-header">
      <div>
        <h1 className="flota-titulo">Flota disponible</h1>
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

        <span className="flota-contador">
          {items.length} repartidor
          {items.length !== 1 ? "es" : ""}
        </span>
      </div>

      {/* Estado de carga */}
      {loading && (
        <p className="flota-mensaje flota-cargando" role="status">
          Cargando repartidores...
        </p>
      )}

      {/* Mensaje de error */}
      {error && (
        <p className="flota-error" role="alert">
          {error}
        </p>
      )}

      {/* Tabla de datos */}
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
              {items.map((repartidor) => {
                const estado = repartidor.estado
                  .trim()
                  .toLowerCase();

                const claseEstado =
                  estado === "disponible" || estado === "activo"
                    ? "flota-estado-disponible"
                    : estado === "ocupado"
                      ? "flota-estado-ocupado"
                      : "flota-estado-inactivo";

                return (
                  <tr key={repartidor.id}>
                    <td className="flota-id">
                      #{repartidor.id}
                    </td>

                    <td className="flota-nombre">
                      {repartidor.nombre}
                    </td>

                    <td>{repartidor.apellido}</td>
                    <td>{repartidor.tipo_vehiculo}</td>
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

              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="flota-mensaje flota-vacio"
                  >
                    No hay repartidores disponibles.
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

// Permite importar este componente desde otros archivos de React.
export default Flota;
