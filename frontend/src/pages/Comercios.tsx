import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

interface Comercio {
  id: number;
  nombre: string;
  telefono: string;
  direccion: string;
  datos_cliente: number | null;
}

const emptyForm = { nombre: "", telefono: "", direccion: "", datos_cliente: "" };

export default function Comercios() {
  const [items, setItems] = useState<Comercio[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/comercios/");
      if (!res.ok) throw new Error("No se pudieron cargar los comercios");
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

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const body: Record<string, unknown> = {
      nombre: form.nombre,
      telefono: form.telefono,
      direccion: form.direccion,
    };
    if (form.datos_cliente !== "") {
      body.datos_cliente = Number(form.datos_cliente);
    } else {
      body.datos_cliente = null;
    }
    const url = editingId ? `/api/comercios/${editingId}/` : "/api/comercios/";
    const method = editingId ? "PUT" : "POST";
    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(JSON.stringify(data));
        return;
      }
      setForm(emptyForm);
      setEditingId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  }

  function startEdit(c: Comercio) {
    setEditingId(c.id);
    setForm({
      nombre: c.nombre,
      telefono: c.telefono,
      direccion: c.direccion,
      datos_cliente: c.datos_cliente ? String(c.datos_cliente) : "",
    });
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar este comercio?")) return;
    await fetch(`/api/comercios/${id}/`, { method: "DELETE" });
    await load();
  }

  return (
    <main style={{ padding: "1rem", maxWidth: 900, margin: "0 auto" }}>
      <h1>Gestión de Comercios</h1>
      <p>
        <Link to="/dashboard">Volver al dashboard</Link>
      </p>

      <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
        <h2>{editingId ? "Editar comercio" : "Nuevo comercio"}</h2>
        <div style={{ display: "grid", gap: "0.5rem", maxWidth: 400 }}>
          <input
            placeholder="Nombre"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            required
          />
          <input
            placeholder="Teléfono"
            value={form.telefono}
            onChange={(e) => setForm({ ...form, telefono: e.target.value })}
            required
          />
          <input
            placeholder="Dirección"
            value={form.direccion}
            onChange={(e) => setForm({ ...form, direccion: e.target.value })}
            required
          />
          <input
            placeholder="ID cliente de contacto (opcional)"
            value={form.datos_cliente}
            onChange={(e) => setForm({ ...form, datos_cliente: e.target.value })}
          />
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button type="submit">{editingId ? "Guardar" : "Crear"}</button>
            {editingId && (
              <button
                type="button"
                onClick={() => {
                  setEditingId(null);
                  setForm(emptyForm);
                }}
              >
                Cancelar
              </button>
            )}
          </div>
        </div>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <table border={1} cellPadding={6} style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Teléfono</th>
              <th>Dirección</th>
              <th>Cliente</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.nombre}</td>
                <td>{c.telefono}</td>
                <td>{c.direccion}</td>
                <td>{c.datos_cliente ?? "-"}</td>
                <td>
                  <button onClick={() => startEdit(c)}>Editar</button>{" "}
                  <button onClick={() => handleDelete(c.id)}>Eliminar</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center" }}>
                  Sin comercios
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </main>
  );
}
