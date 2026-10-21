import { useEffect, useState, type FormEvent } from "react";

interface Flota {
  id: number;
  nombre: string;
  vehiculo: string;
  telefono: string;
  disponible: boolean;
}

const emptyForm = { nombre: "", vehiculo: "", telefono: ""};

function Flota() {
    const [items, setItems] = useState<Flota[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [form, setForm] = useState(emptyForm);
    const [editingId, setEditingId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/flota/");
      if (!res.ok) throw new Error("No se pudo cargar la flota");
      const data = await res.json();
      setItems(data.results ?? data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

    function startEdit(c: Flota) {
    setEditingId(c.id);
    setForm({
      nombre: c.nombre,
      vehiculo: c.vehiculo,
      telefono: c.telefono,
    });
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar este repartidor?")) return;
    await fetch(`/api/repartidores/${id}/`, { method: "DELETE" });
    await load();
  }
  
    return (
    <div>
      <h1>Flota disponible:</h1>
        <table border={1} cellPadding={6} style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Vehículo</th>
              <th>Disponibilidad</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.nombre}</td>
                <td>{c.vehiculo}</td>
                <td>
                  <button onClick={() => startEdit(c)}>Editar</button>{" "}
                  <button onClick={() => handleDelete(c.id)}>Eliminar</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center" }}>
                  Sin repartidores
                </td>
              </tr>
            )}
          </tbody>
        </table>
    </div>
  );
}

export default Flota;