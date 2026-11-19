import { useState, type FormEvent } from "react";

interface GestionarComerciosProps {
  onChange: () => void;
}

const emptyForm = {
  nombre: "",
  telefono: "",
  direccion: "",
};

export default function GestionarComercios({
  onChange,
}: GestionarComerciosProps) {
  // Datos ingresados en el formulario.
  const [form, setForm] = useState(emptyForm);

  // Controla el estado de guardado y los errores.
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [mensaje, setMensaje] = useState("");

  // Actualiza los campos del formulario.
  function handleChange(
    campo: keyof typeof emptyForm,
    valor: string
  ) {
    setForm((actual) => ({
      ...actual,
      [campo]: valor,
    }));
  }

  // Registra un comercio nuevo.
  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    setError("");
    setMensaje("");

    // Validación del teléfono: solo números, máximo 14 dígitos y mayor a 0.
    const telefono = form.telefono.trim();

    if (!/^[0-9]+$/.test(telefono)) {
      setError("El teléfono debe contener solamente números.");
      return;
    }
    if (telefono.length > 14) {
      setError("El teléfono no puede tener más de 14 dígitos.");
      return;
    }
    if (Number(telefono) <= 0) {
      setError("El teléfono debe ser mayor a 0.");
      return;
    }

    setGuardando(true);

    try {
      const res = await fetch("/api/comercios/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data =
        res.status === 204 ? {} : await res.json();

      if (!res.ok) {
        setError(
          typeof data === "object"
            ? JSON.stringify(data)
            : "No se pudo registrar el comercio."
        );
        return;
      }

      // Limpia el formulario después de registrar correctamente.
      setForm(emptyForm);
      setMensaje("El comercio se registró correctamente.");

      // Solicita al componente padre actualizar el listado.
      onChange();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Error al registrar el comercio."
      );
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="gestionar-comercios">
      <p className="gestionar-comercios-descripcion">
        Completá los siguientes datos para registrar un nuevo comercio.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="gestionar-comercios-formulario">
          <label htmlFor="nombre-comercio">
            Nombre del comercio
          </label>

          <input
            id="nombre-comercio"
            type="text"
            placeholder="Ej.: Almacén Central"
            value={form.nombre}
            onChange={(e) =>
              handleChange("nombre", e.target.value)
            }
            required
          />

          <label htmlFor="telefono-comercio">
            Teléfono
          </label>

          <input
            id="telefono-comercio"
            type="tel"
            inputMode="numeric"
            maxLength={14}
            placeholder="Ej.: 2211234567"
            value={form.telefono}
            onChange={(e) =>
              handleChange("telefono", e.target.value.replace(/\D/g, ""))
            }
            required
          />

          <label htmlFor="direccion-comercio">
            Dirección
          </label>

          <input
            id="direccion-comercio"
            type="text"
            placeholder="Ej.: Calle 12, número 345"
            value={form.direccion}
            onChange={(e) =>
              handleChange("direccion", e.target.value)
            }
            required
          />
        </div>

        {error && (
          <p className="gestionar-comercios-error" role="alert">
            {error}
          </p>
        )}

        {mensaje && (
          <p
            className="gestionar-comercios-mensaje"
            role="status"
          >
            {mensaje}
          </p>
        )}

        <button
          type="submit"
          className="gestionar-comercios-guardar"
          disabled={guardando}
        >
          {guardando ? "Registrando..." : "Registrar comercio"}
        </button>
      </form>
    </section>
  );
}
