import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import "../styles/DashboardRepartidor.css";

const API_URL = "http://127.0.0.1:8000/api";

interface PaqueteAsignado {
  id: number;
  cod_seguimiento: string;
  estado: string;
  tamanio: string;
  destinatario: string;
  direccion: string;
  comercio: string;
  fecha_destino: string; // AAAA-MM-DD
}

const ETIQUETAS_ESTADO: Record<string, string> = {
  pendiente: "Pendiente",
  retirado: "Retirado",
  en_camino: "En camino",
};

// "2026-10-30" -> "30/10/2026" (sin pasar por Date para evitar desfases de zona horaria)
function formatearFecha(iso: string) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

function DashboardRepartidor() {
  const navigate = useNavigate();
  const guardado = localStorage.getItem("repartidor");
  const repartidor = guardado ? JSON.parse(guardado) : null;

  const [paquetes, setPaquetes] = useState<PaqueteAsignado[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function cerrarSesion() {
    localStorage.removeItem("repartidor");
    navigate("/loginrepartidor");
  }

  async function cargar() {
    if (!repartidor) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/paquetes-repartidor/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: repartidor.token }),
      });

      // Token inexistente o repartidor dado de baja: se cierra la sesión
      if (res.status === 404 || res.status === 403) {
        const data = await res.json().catch(() => null);
        if (data?.message) {
          cerrarSesion();
          return;
        }
        throw new Error("No se encontró el servicio de pedidos (revisá la URL en Django)");
      }

      if (!res.ok) throw new Error("No se pudieron cargar tus pedidos");

      const data = await res.json();
      setPaquetes(data.paquetes ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo conectar con el servidor");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Si no hay sesión iniciada, vuelve al login
  if (!repartidor) return <Navigate to="/loginrepartidor" replace />;

  return (
    <main className="repartidor-container">
      <header className="repartidor-header">
        <div>
          <h1 className="repartidor-titulo">Panel de paquetes</h1>
          <p className="repartidor-saludo">Bienvenido, {repartidor.nombre}.</p>
        </div>
        <button type="button" className="repartidor-secundario" onClick={cerrarSesion}>
          Cerrar sesión
        </button>
      </header>

      <section className="repartidor-card">
        <div className="repartidor-toolbar">
          <h2 className="repartidor-subtitulo">Mis pedidos pendientes</h2>
          <button
            type="button"
            className="repartidor-primario"
            onClick={cargar}
            disabled={loading}
          >
            {loading ? "Actualizando..." : "Actualizar"}
          </button>
        </div>

        {loading && (
          <p className="repartidor-mensaje" role="status">
            Cargando pedidos...
          </p>
        )}

        {error && (
          <p className="repartidor-error" role="alert">
            {error}
          </p>
        )}

        {/* Escenario 2: lista vacía */}
        {!loading && !error && paquetes.length === 0 && (
          <p className="repartidor-mensaje repartidor-vacio">
            No tenés pedidos en espera.
          </p>
        )}

        {/* Escenario 1: lista de pedidos asignados */}
        {!loading && !error && paquetes.length > 0 && (
          <ul className="repartidor-lista">
            {paquetes.map((p) => (
              <li key={p.id} className="repartidor-item">
                <div className="repartidor-item-head">
                  <strong>{p.cod_seguimiento}</strong>
                  <span className={`repartidor-estado repartidor-estado-${p.estado}`}>
                    {ETIQUETAS_ESTADO[p.estado] ?? p.estado}
                  </span>
                </div>
                <dl className="repartidor-datos">
                  <dt>Destinatario</dt>
                  <dd>{p.destinatario}</dd>
                  <dt>Dirección</dt>
                  <dd>{p.direccion}</dd>
                  <dt>Comercio</dt>
                  <dd>{p.comercio}</dd>
                  <dt>Tamaño</dt>
                  <dd>{p.tamanio}</dd>
                  <dt>Entrega</dt>
                  <dd>{formatearFecha(p.fecha_destino)}</dd>
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

export default DashboardRepartidor;