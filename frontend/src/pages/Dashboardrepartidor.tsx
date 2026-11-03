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
  asignado: "Asignado",
  retirado: "Retirado",
  en_camino: "En camino",
  entregado: "Entregado",
  cancelado: "Cancelado",
};

// Flujo que maneja el repartidor: asignado -> en_camino -> entregado.
const SIGUIENTE_ESTADO: Record<string, string | null> = {
  asignado: "en_camino",
  en_camino: "entregado",
  entregado: null,
  cancelado: null,
};

// Texto del botón según el estado actual
const TEXTO_BOTON: Record<string, string> = {
  asignado: "Marcar como En camino",
  en_camino: "Marcar como Entregado",
};

// "2026-10-30" -> "30/10/2026" (sin pasar por Date para evitar desfases de zona horaria)
function formatearFecha(iso: string) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

// Convierte un archivo en texto base64 (data URL) para poder mandarlo dentro de un JSON
function archivoABase64(archivo: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const lector = new FileReader();
    lector.onload = () => resolve(lector.result as string);
    lector.onerror = () => reject(new Error("No se pudo leer la foto"));
    lector.readAsDataURL(archivo);
  });
}

interface PedidoItemProps {
  paquete: PaqueteAsignado;
  token: string;
  onActualizado: (id: number, nuevoEstado: string) => void;
}

function PedidoItem({ paquete: p, token, onActualizado }: PedidoItemProps) {
  const [foto, setFoto] = useState<File | null>(null);
  const [pidiendoFoto, setPidiendoFoto] = useState(false);
  const [cancelando, setCancelando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [exito, setExito] = useState("");

  const siguiente = SIGUIENTE_ESTADO[p.estado] ?? null;
  const finalizado = siguiente === null;

  async function enviarCambio(estado: string, extra?: { foto?: File; motivo?: string }) {
    setAviso("");
    setExito("");
    setEnviando(true);

    try {
      const cuerpo: Record<string, unknown> = {
        token,
        id: p.id,
        estado,
      };
      if (extra?.motivo) cuerpo.motivo = extra.motivo;
      if (extra?.foto) cuerpo.foto_dni = await archivoABase64(extra.foto);

      const res = await fetch(`${API_URL}/cambiar-estado-pedido/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        console.error("Error al actualizar estado:", res.status, data);
        setAviso(
          data?.message ??
            data?.error ??
            data?.detail ??
            `No se pudo actualizar el estado (código ${res.status})`
        );
        return;
      }

      onActualizado(p.id, estado);
      setExito(`Estado actualizado a "${ETIQUETAS_ESTADO[estado]}".`);
      setFoto(null);
      setMotivo("");
      setPidiendoFoto(false);
      setCancelando(false);
    } catch {
      setAviso("No se pudo conectar con el servidor");
    } finally {
      setEnviando(false);
    }
  }

  function avanzar() {
    if (!siguiente) return;

    // Antes de pasar a Entregado se pide la foto del DNI
    if (siguiente === "entregado") {
      setPidiendoFoto(true);
      setAviso("");
      setExito("");
      return;
    }

    enviarCambio(siguiente);
  }

  function confirmarEntrega() {
    if (!foto) {
      setAviso("Tenés que adjuntar la foto del DNI del receptor para marcar como Entregado.");
      return;
    }
    enviarCambio("entregado", { foto });
  }

  function confirmarCancelacion() {
    if (!motivo.trim()) {
      setAviso("Tenés que indicar el motivo de la cancelación.");
      return;
    }
    enviarCambio("cancelado", { motivo: motivo.trim() });
  }

  return (
    <li className="repartidor-item">
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

      {finalizado ? (
        <p className="repartidor-mensaje">Este pedido ya no admite cambios de estado.</p>
      ) : (
        <div className="repartidor-actualizar">
          {pidiendoFoto ? (
            <>
              <label>
                Foto del DNI del receptor
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={(e) => setFoto(e.target.files?.[0] ?? null)}
                  disabled={enviando}
                />
              </label>
              <div className="repartidor-acciones">
                <button
                  type="button"
                  className="repartidor-primario"
                  onClick={confirmarEntrega}
                  disabled={enviando}
                >
                  {enviando ? "Guardando..." : "Confirmar entrega"}
                </button>
                <button
                  type="button"
                  className="repartidor-secundario"
                  onClick={() => {
                    setPidiendoFoto(false);
                    setFoto(null);
                    setAviso("");
                  }}
                  disabled={enviando}
                >
                  Volver
                </button>
              </div>
            </>
          ) : cancelando ? (
            <>
              <label>
                Motivo de la cancelación
                <textarea
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  rows={2}
                  disabled={enviando}
                />
              </label>
              <div className="repartidor-acciones">
                <button
                  type="button"
                  className="repartidor-primario"
                  onClick={confirmarCancelacion}
                  disabled={enviando}
                >
                  {enviando ? "Guardando..." : "Confirmar cancelación"}
                </button>
                <button
                  type="button"
                  className="repartidor-secundario"
                  onClick={() => {
                    setCancelando(false);
                    setMotivo("");
                    setAviso("");
                  }}
                  disabled={enviando}
                >
                  Volver
                </button>
              </div>
            </>
          ) : (
            <div className="repartidor-acciones">
              <button
                type="button"
                className="repartidor-primario"
                onClick={avanzar}
                disabled={enviando}
              >
                {enviando ? "Guardando..." : TEXTO_BOTON[p.estado]}
              </button>
              <button
                type="button"
                className="repartidor-secundario"
                onClick={() => {
                  setCancelando(true);
                  setAviso("");
                  setExito("");
                }}
                disabled={enviando}
              >
                Cancelar pedido
              </button>
            </div>
          )}

          {aviso && (
            <p className="repartidor-error" role="alert">
              {aviso}
            </p>
          )}
          {exito && (
            <p className="repartidor-mensaje" role="status">
              {exito}
            </p>
          )}
        </div>
      )}
    </li>
  );
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

  function actualizarEstadoLocal(id: number, nuevoEstado: string) {
    setPaquetes((prev) => prev.map((p) => (p.id === id ? { ...p, estado: nuevoEstado } : p)));
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
          <h2 className="repartidor-subtitulo">Mis pedidos</h2>
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

        {/* Lista vacía */}
        {!loading && !error && paquetes.length === 0 && (
          <p className="repartidor-mensaje repartidor-vacio">No tenés pedidos en espera.</p>
        )}

        {/* Lista de pedidos asignados */}
        {!loading && !error && paquetes.length > 0 && (
          <ul className="repartidor-lista">
            {paquetes.map((p) => (
              <PedidoItem
                key={p.id}
                paquete={p}
                token={repartidor.token}
                onActualizado={actualizarEstadoLocal}
              />
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

export default DashboardRepartidor;