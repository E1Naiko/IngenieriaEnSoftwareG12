
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/HistorialEnvios.css";

// Endpoint del historial
const HISTORIAL_URL = "/api/historial/";

// Estructura de los datos de cada repartidor
interface Repartidor {
  id: number;
  nombre: string;
  apellido: string;
  dado_de_baja: boolean;
  cantidad_envios: number;
}

// Estructura de cada paquete del historial
interface Envio {
  id: number;
  cod_seguimiento: string;
  estado: string;
  fecha_origen: string | null;
  fecha_destino: string | null;
  comercio: string;
  cliente: string;
  direccion: string;
}

// Respuesta del backend al consultar los repartidores
interface RespuestaRepartidores {
  results: Repartidor[];
  count: number;
}

// Respuesta del backend al consultar el historial individual
interface RespuestaHistorial {
  repartidor: {
    id: number;
    nombre: string;
    apellido: string;
    dado_de_baja: boolean;
  };
  results: Envio[];
  count: number;
}

function HistorialEnvios() {

  // Permite navegar entre las páginas
  const navigate = useNavigate();

  // Lista de repartidores obtenida desde Django
  const [repartidores, setRepartidores] = useState<Repartidor[]>([]);

  // ID del repartidor seleccionado
  const [repartidorSeleccionado, setRepartidorSeleccionado] =
    useState<number | "">("");

  // Información del repartidor seleccionado
  const [nombreRepartidor, setNombreRepartidor] = useState("");

  // Lista de paquetes del repartidor seleccionado
  const [envios, setEnvios] = useState<Envio[]>([]);

  // Cantidad de envíos encontrados
  const [cantidadEnvios, setCantidadEnvios] = useState(0);

  // Control de carga de los datos
  const [loadingRepartidores, setLoadingRepartidores] = useState(false);
  const [loadingHistorial, setLoadingHistorial] = useState(false);

  // Mensaje de error
  const [error, setError] = useState("");

  // ------------------------------------------------
  // 1. OBTENER LA LISTA DE REPARTIDORES
  // ------------------------------------------------

  useEffect(() => {

    // Función que consulta los repartidores al backend
    const obtenerRepartidores = async () => {

      setLoadingRepartidores(true);
      setError("");

      try {

        // Petición GET para obtener todos los repartidores
        const respuesta = await fetch(HISTORIAL_URL, {
          method: "GET",
          credentials: "same-origin",
        });

        // Verificar si Django respondió correctamente
        if (!respuesta.ok) {
          throw new Error("No se pudieron obtener los repartidores");
        }

        // Convertir la respuesta JSON a un objeto TypeScript
        const datos: RespuestaRepartidores = await respuesta.json();

        // Guardar la lista de repartidores
        setRepartidores(datos.results);

      } catch (error) {

        console.error(error);
        setError("Error al cargar la lista de repartidores");

      } finally {

        // Finalizar el estado de carga
        setLoadingRepartidores(false);
      }
    };

    // Ejecutar la consulta al entrar en la pantalla
    obtenerRepartidores();

  }, []);

  // ------------------------------------------------
  // 2. OBTENER EL HISTORIAL DE UN REPARTIDOR
  // ------------------------------------------------

  const obtenerHistorial = async (id: number) => {

    setLoadingHistorial(true);
    setError("");

    // Limpiar los envíos anteriores
    setEnvios([]);
    setCantidadEnvios(0);

    try {

      // Consultar el historial del repartidor seleccionado
      const respuesta = await fetch(`${HISTORIAL_URL}${id}/`, {
        method: "GET",
        credentials: "same-origin",
      });

      // Comprobar si ocurrió algún error
      if (!respuesta.ok) {
        throw new Error("No se pudo obtener el historial");
      }

      // Convertir el JSON recibido
      const datos: RespuestaHistorial = await respuesta.json();

      // Guardar los datos del repartidor
      setNombreRepartidor(
        `${datos.repartidor.nombre} ${datos.repartidor.apellido}`
      );

      // Guardar los paquetes recibidos
      setEnvios(datos.results);

      // Guardar la cantidad de envíos
      setCantidadEnvios(datos.count);

    } catch (error) {

      console.error(error);
      setError("Error al cargar el historial del repartidor");

    } finally {

      // Finalizar la carga
      setLoadingHistorial(false);
    }
  };

  // ------------------------------------------------
  // 3. SELECCIONAR UN REPARTIDOR
  // ------------------------------------------------

  const manejarSeleccion = (
    evento: React.ChangeEvent<HTMLSelectElement>
  ) => {

    // Obtener el ID seleccionado
    const id = evento.target.value;

    // Si no seleccionó ningún repartidor
    if (id === "") {

      setRepartidorSeleccionado("");
      setNombreRepartidor("");
      setEnvios([]);
      setCantidadEnvios(0);
      setError("");

      return;
    }

    // Convertir el ID de texto a número
    const idNumerico = Number(id);

    // Guardar el repartidor seleccionado
    setRepartidorSeleccionado(idNumerico);

    // Consultar su historial
    obtenerHistorial(idNumerico);
  };

  // ------------------------------------------------
  // 4. MOSTRAR LOS DATOS EN PANTALLA
  // ------------------------------------------------

  return (

    <div className="historial-container">

      {/* Encabezado de la pantalla */}
      <header className="historial-header">

        <button
          type="button"
          onClick={() => navigate("/dashboard")}
        >
          Volver
        </button>

        <h1>Historial de envíos</h1>

        <p>
          Consultá el historial de envíos de cada repartidor.
        </p>

      </header>

      {/* Selección del repartidor */}
      <section className="historial-filtros">

        <label htmlFor="repartidor">
          Seleccionar repartidor:
        </label>

        <select
          id="repartidor"
          value={repartidorSeleccionado}
          onChange={manejarSeleccion}
          disabled={loadingRepartidores}
        >

          <option value="">
            {loadingRepartidores
              ? "Cargando repartidores..."
              : "Seleccioná un repartidor"}
          </option>

          {repartidores.map((repartidor) => (

            <option
              key={repartidor.id}
              value={repartidor.id}
            >
              {repartidor.nombre} {repartidor.apellido}
              {" - "}
              {repartidor.cantidad_envios} envíos
              {repartidor.dado_de_baja ? " (Dado de baja)" : ""}
            </option>

          ))}

        </select>

      </section>

      {/* Mensaje cuando no existen repartidores */}
      {!loadingRepartidores && repartidores.length === 0 && !error && (
        <p>No hay repartidores registrados.</p>
      )}

      {/* Mensajes de error */}
      {error && (
        <p className="historial-error">
          {error}
        </p>
      )}

      {/* Indicador de carga del historial */}
      {loadingHistorial && (
        <p>Cargando historial...</p>
      )}

      {/* Mostrar historial cuando se seleccionó un repartidor */}
      {repartidorSeleccionado !== "" &&
        !loadingHistorial &&
        !error && (

        <section className="historial-resultados">

          <h2>
            Historial de {nombreRepartidor}
          </h2>

          <p>
            Total de envíos: {cantidadEnvios}
          </p>

          {/* Comprobar si tiene envíos registrados */}
          {envios.length === 0 ? (

            <p>
              Este repartidor no tiene envíos en su historial.
            </p>

          ) : (

            <div className="historial-tabla">

              <table>

                <thead>
                  <tr>
                    <th>Código de seguimiento</th>
                    <th>Estado</th>
                    <th>Comercio</th>
                    <th>Cliente</th>
                    <th>Dirección</th>
                    <th>Fecha de origen</th>
                    <th>Fecha de destino</th>
                  </tr>
                </thead>

                <tbody>

                  {envios.map((envio) => (

                    <tr key={envio.id}>

                      <td>{envio.cod_seguimiento}</td>

                      <td>{envio.estado}</td>

                      <td>{envio.comercio}</td>

                      <td>{envio.cliente}</td>

                      <td>{envio.direccion}</td>

                      <td>
                        {envio.fecha_origen ?? "Sin fecha"}
                      </td>

                      <td>
                        {envio.fecha_destino ?? "Sin fecha"}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </section>

      )}

    </div>
  );
}

export default HistorialEnvios;
