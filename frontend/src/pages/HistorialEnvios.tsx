import { useCallback, useEffect, useState } from "react";
import "../styles/HistorialEnvios.css";

// Dirección base del backend Django.
const API_URL = "http://127.0.0.1:8000/api";

// Datos que esperamos recibir de un repartidor.
interface Repartidor {
  id: number;
  dni: string;
  nombre: string;
  apellido: string;
  telefono: string;
  mail: string;
  tipo_vehiculo: "moto" | "auto" | "camioneta" | "camion";
}

// Datos que esperamos recibir de un envío.
interface Envio {
  id: number;
  fecha: string;
  direccion_entrega: string;
  cliente: string;
  estado: string;
}

// El backend puede devolver una lista o una respuesta paginada.
type Respuesta<T> = T[] | { results: T[] };

// Obtiene la lista independientemente del formato de respuesta.
const extraerLista = <T,>(data: Respuesta<T>): T[] =>
  Array.isArray(data) ? data : data.results;

// Función reutilizable para consultar el backend.
async function pedir<T>(ruta: string): Promise<T> {
  const token = localStorage.getItem("token");

  const res = await fetch(`${API_URL}${ruta}`, {
    headers: {
      "Content-Type": "application/json",

      // Se envía el token si existe.
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error("No tenés permiso para consultar esta información.");
  }

  if (!res.ok) {
    throw new Error("No se pudo cargar la información. Intentá de nuevo.");
  }

  return res.json();
}

export default function HistorialEnvios() {
  // Lista de repartidores disponibles para seleccionar.
  const [repartidores, setRepartidores] = useState<Repartidor[]>([]);

  // ID del repartidor seleccionado.
  const [repartidorId, setRepartidorId] = useState<number | null>(null);

  // Historial del repartidor seleccionado.
  const [envios, setEnvios] = useState<Envio[]>([]);

  // Estados de carga.
  const [cargandoRepartidores, setCargandoRepartidores] = useState(true);
  const [cargandoEnvios, setCargandoEnvios] = useState(false);

  // Mensaje de error, si ocurre algún problema.
  const [error, setError] = useState<string | null>(null);

  // Al abrir la pantalla, se solicita la lista de repartidores.
  useEffect(() => {
    pedir<Respuesta<Repartidor>>("/historial")
      .then((data) => {
        setRepartidores(extraerLista(data));
      })
      .catch((e: Error) => {
        setError(e.message);
      })
      .finally(() => {
        setCargandoRepartidores(false);
      });
  }, []);

  // Solicita el historial de un repartidor específico.
  const cargarHistorial = useCallback(async (id: number) => {
    setCargandoEnvios(true);
    setError(null);
    setEnvios([]);

    try {
      const data = await pedir<Respuesta<Envio>>(
      `/historial/${id}`
     );

      setEnvios(extraerLista(data));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCargandoEnvios(false);
    }
  }, []);

  // Se ejecuta cuando el usuario selecciona un repartidor.
  const alElegirRepartidor = (valor: string) => {
    if (!valor) {
      setRepartidorId(null);
      setEnvios([]);
      setError(null);
      return;
    }

    const id = Number(valor);

    setRepartidorId(id);
    cargarHistorial(id);
  };

  // Busca los datos del repartidor elegido.
  const repartidorElegido = repartidores.find(
    (r) => r.id === repartidorId
  );

  return (
    <section className="historial">
      <h1 className="historial-titulo">Historial de envíos</h1>

      <label className="historial-campo">
        <span>Repartidor</span>

        <select
          value={repartidorId ?? ""}
          onChange={(e) => alElegirRepartidor(e.target.value)}
          disabled={cargandoRepartidores}
        >
          <option value="">
            {cargandoRepartidores
              ? "Cargando repartidores…"
              : "Elegí un repartidor"}
          </option>

          {repartidores.map((r) => (
            <option key={r.id} value={r.id}>
              {r.apellido}, {r.nombre} — DNI {r.dni}
            </option>
          ))}
        </select>
      </label>

      {error && (
        <p className="historial-error" role="alert">
          {error}
        </p>
      )}

      {!cargandoRepartidores &&
        !error &&
        repartidores.length === 0 && (
          <p className="historial-vacio">
            No hay repartidores registrados.
          </p>
        )}

      {repartidorId === null && !error && (
        <p className="historial-vacio">
          Elegí un repartidor para ver todos sus envíos.
        </p>
      )}

      {repartidorId !== null && cargandoEnvios && (
        <p className="historial-vacio">
          Cargando historial…
        </p>
      )}

      {repartidorId !== null &&
        !cargandoEnvios &&
        !error &&
        envios.length === 0 && (
          <p className="historial-vacio">
            {repartidorElegido?.nombre ?? "El repartidor"} todavía no
            tiene envíos registrados.
          </p>
        )}

      {envios.length > 0 && (
        <div className="historial-tabla-wrap">
          <table className="historial-tabla">
            <caption>
              {envios.length} envíos de {repartidorElegido?.nombre}{" "}
              {repartidorElegido?.apellido}
            </caption>

            <thead>
              <tr>
                <th>Fecha</th>
                <th>Cliente</th>
                <th>Dirección de entrega</th>
                <th>Estado</th>
              </tr>
            </thead>

            <tbody>
              {envios.map((envio) => (
                <tr key={envio.id}>
                  <td>
                    {new Date(envio.fecha).toLocaleString("es-AR", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </td>

                  <td>{envio.cliente}</td>

                  <td>{envio.direccion_entrega}</td>

                  <td>
                    <span
                      className={`estado estado-${envio.estado}`}
                    >
                      {envio.estado}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}