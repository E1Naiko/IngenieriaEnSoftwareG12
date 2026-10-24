import { useState, type FormEvent } from "react";

interface Props {
  onGuardado: () => void;
  onCancelar: () => void;
}

const vacio = { nombre: "", dni: "", direccion: "" };

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
          dni: Number(form.dni),
          direccion: form.direccion,
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
        placeholder="DNI"
        inputMode="numeric"
        pattern="[0-9]*"
        value={form.dni}
        onChange={(e) => setForm({ ...form, dni: e.target.value })}
        required
      />
      <input
        placeholder="Dirección"
        value={form.direccion}
        onChange={(e) => setForm({ ...form, direccion: e.target.value })}
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
