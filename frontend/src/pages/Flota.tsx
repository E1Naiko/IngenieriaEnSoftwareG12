
import { useEffect, useState } from "react";

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
    <div>
      {/* Título principal de la sección de flota. */}
      <h1>Flota disponible</h1>

      {/* Muestra un mensaje mientras se espera la respuesta del backend. */}
      {loading && <p>Cargando repartidores...</p>}

      {/* Muestra el mensaje de error únicamente si existe uno. */}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Muestra la tabla cuando no se está cargando y no hay errores. */}
      {!loading && !error && (
        <table
          // Agrega bordes a las celdas y permite configurar su apariencia.
          border={1}
          cellPadding={6}
          style={{ width: "100%", borderCollapse: "collapse" }}
        >
          {/* Encabezado de la tabla. */}
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

          {/* Cuerpo de la tabla: contiene una fila por cada repartidor. */}
          <tbody>
            {items.map((repartidor) => (
              // Recorre la lista items y genera una fila por repartidor.
              // La propiedad key permite a React identificar cada fila.
              <tr key={repartidor.id}>
                {/* Muestra el identificador del repartidor. */}
                <td>{repartidor.id}</td>

                {/* Muestra el nombre del repartidor. */}
                <td>{repartidor.nombre}</td>

                {/* Muestra el apellido del repartidor. */}
                <td>{repartidor.apellido}</td>

                {/* Muestra el tipo de vehículo que utiliza. */}
                <td>{repartidor.tipo_vehiculo}</td>

                {/* Muestra su número de teléfono. */}
                <td>{repartidor.telefono}</td>

                {/* Muestra su estado actual. */}
                <td>{repartidor.estado}</td>
              </tr>
            ))}

            {/* Si la lista está vacía, muestra un mensaje en la tabla. */}
            {items.length === 0 && (
              <tr>
                {/* colSpan={6} hace que la celda ocupe las seis columnas. */}
                <td colSpan={6} style={{ textAlign: "center" }}>
                  No hay repartidores disponibles.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

// Permite importar este componente desde otros archivos de React.
export default Flota;
