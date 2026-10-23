import { useEffect, useState } from "react";

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
  const [items, setItems] = useState<Repartidor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/flota/");
      if (!res.ok) {
        throw new Error("No se pudo cargar la flota");
      }
      const data = await res.json();
      setItems(data.repartidores ?? []);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Error al cargar la flota"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <h1>Flota disponible</h1>
      {loading && <p>Cargando repartidores...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {!loading && !error && (
        <table
          border={1}
          cellPadding={6}
          style={{ width: "100%", borderCollapse: "collapse" }}
        >
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
            {items.map((repartidor) => (
              <tr key={repartidor.id}>
                <td>{repartidor.id}</td>
                <td>{repartidor.nombre}</td>
                <td>{repartidor.apellido}</td>
                <td>{repartidor.tipo_vehiculo}</td>
                <td>{repartidor.telefono}</td>
                <td>{repartidor.estado}</td>
              </tr>
            ))}

            {items.length === 0 && (
              <tr>
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

export default Flota;