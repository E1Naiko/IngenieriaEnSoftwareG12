import { useState, type FormEvent } from "react";

interface Props {
  onGuardado: () => void;
  onCancelar: () => void;
}

const vacio = { nombre: "", apellido: "", telefono: "", direccion: "", dni: "" };

export default function FormularioCliente({ onGuardado, onCancelar }: Props) {
  const [form, setForm] = useState(vacio);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setGuardando(true);
    try {
      const res = await fetch("/api/clientes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: form.nombre,
          apellido: form.apellido,
          telefono: form.telefono,
          direccion: form.direccion,
          dni: Number(form.dni),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(JSON.stringify(data));
        return;
      }
      onGuardado();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.5rem" }}>
      <input
        placeholder="Nombre"
        value={form.nombre}
        onChange={(e) => setForm({ ...form, nombre: e.target.value })}
        required
      />
      <input
        placeholder="Apellido"
        value={form.apellido}
        onChange={(e) => setForm({ ...form, apellido: e.target.value })}
        required
      />
      <input
        placeholder="Teléfono"
        inputMode="tel"
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
        placeholder="DNI"
        inputMode="numeric"
        pattern="[0-9]*"
        value={form.dni}
        onChange={(e) => setForm({ ...form, dni: e.target.value })}
        required
      />
      {error && <p style={{ color: "red", margin: 0 }}>{error}</p>}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="submit" disabled={guardando}>Crear cliente</button>
        <button type="button" onClick={onCancelar}>Cancelar</button>
      </div>
    </form>
  );
}
