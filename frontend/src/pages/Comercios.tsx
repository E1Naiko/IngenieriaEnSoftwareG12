import { useEffect, useState } from "react";

interface Comercio {
  id: number;
  nombre: string;
  telefono: string;
  direccion: string;
}

interface ComerciosProps {
  refreshKey?: number;
}

export default function Comercios({
  refreshKey = 0,
}: ComerciosProps) {
  const [items, setItems] = useState<Comercio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/comercios/");

      if (!res.ok) {
        throw new Error("No se pudieron cargar los comercios.");
      }

      const data = await res.json();
      setItems(data.results ?? data);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Error al cargar comercios."
      );
    } finally {
      setLoading(false);
    }
  }

  // Carga los comercios al iniciar y cuando se modifica la lista.
  useEffect(() => {
    load();
  }, [refreshKey]);

  if (loading) {
    return <p>Cargando comercios...</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  return (
    <div className="comercios-listado">
      <h2>Listado de comercios</h2>

      {items.length === 0 ? (
        <p>No hay comercios registrados.</p>
      ) : (
        <div className="comercios-tabla-contenedor">
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
                  <td>{comercio.id}</td>
                  <td>{comercio.nombre}</td>
                  <td>{comercio.telefono}</td>
                  <td>{comercio.direccion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
