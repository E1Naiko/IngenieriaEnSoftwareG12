import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

/**
 * Página de gestión de comercios (CRUD completo contra /api/comercios/).
 *
 * Cómo funciona:
 * 1. Al montar, `load()` pide la lista y guarda `results` en `items`.
 * 2. El form tiene dos modos, definidos por `editingId`:
 *    - `editingId === null`  → creación con POST.
 *    - `editingId` con valor → reemplazo total con PUT a /api/comercios/<id>/.
 * 3. Después de guardar o borrar se vuelve a llamar `load()`: la tabla siempre
 *    se lee desde el backend, nunca se parchea el estado local.
 *
 * Las rutas son relativas (`/api/...`): en desarrollo Vite las proxifica a
 * Django (`server.proxy` en vite.config.ts), así que no hay que configurar
 * hosts ni depender de CORS.
 *
 * `Comercio` espeja la tabla `comercio` de la base: id, nombre, teléfono y
 * dirección. El `id` lo asigna la base, por eso el form no lo envía.
 */

interface Comercio {
  id: number;
  nombre: string;
  telefono: string;
  direccion: string;
}

const emptyForm = { nombre: "", telefono: "", direccion: "" };

export default function Comercios() {
  const [items, setItems] = useState<Comercio[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /** Lee todos los comercios. `{results, count}` o una lista plana. */
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

  /** Crea (POST) o reemplaza (PUT) según haya una fila en edición. */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const body: Record<string, unknown> = {
      nombre: form.nombre,
      telefono: form.telefono,
      direccion: form.direccion,
    };
    const url = editingId ? `/api/comercios/${editingId}/` : "/api/comercios/";
    const method = editingId ? "PUT" : "POST";
    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      // El 204 del DELETE no trae body: se parsea solo cuando hay contenido.
      const data = res.status === 204 ? {} : await res.json();
      if (!res.ok) {
        // 400 viene como {"nombre": "..."} por campo; el resto como {"detail": "..."}.
        setError(JSON.stringify(data));
        return;
      }
      setForm(emptyForm);
      setEditingId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    }
  }

  /** Carga la fila elegida en el form y lo pasa a modo edición. */
  function startEdit(c: Comercio) {
    setEditingId(c.id);
    setForm({ nombre: c.nombre, telefono: c.telefono, direccion: c.direccion });
  }

  /** Borra y recarga. Sin `catch`, un 500/502 pasaría desapercibido. */
  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar este comercio?")) return;
    try {
      const res = await fetch(`/api/comercios/${id}/`, { method: "DELETE" });
      if (!res.ok) throw new Error(`No se pudo eliminar (${res.status})`);
      if (editingId === id) {
        setEditingId(null);
        setForm(emptyForm);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al eliminar");
    }
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
                <td>
                  <button onClick={() => startEdit(c)}>Editar</button>{" "}
                  <button onClick={() => handleDelete(c.id)}>Eliminar</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center" }}>
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
