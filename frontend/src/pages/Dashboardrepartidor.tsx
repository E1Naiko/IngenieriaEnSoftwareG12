import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import "../styles/DashboardRepartidor.css";

const API_URL = "/api";

interface PaqueteAsignado {
  id: number;
  cod_seguimiento: string;
  estado: string;
  tamanio: string;
  destinatario: string;
  direccion: string;
  comercio: string;
  fecha_destino: string; // AAAA-MM-DD
  // Siguientes dos: los devuelve /api/cambiar-estado-pedido/ al cambiar el estado.
  direccion_comercio?: string; // solo cuando vuelve en devolución al comercio
  id_repartidor_asignado?: number | null; // null = el pedido ya no es suyo
}

const ETIQUETAS_ESTADO: Record<string, string> = {
  asignado: "Asignado",
  retirado: "Retirado",
  en_camino: "En camino",
  entregado: "Entregado",
  cancelado: "Cancelado",
  en_devolucion: "Devolución al comercio",
};

// Flujo que maneja el repartidor: asignado/retirado -> en_camino -> entregado.
const SIGUIENTE_ESTADO: Record<string, string | null> = {
  asignado: "en_camino",
  retirado: "en_camino",
  en_camino: "entregado",
  entregado: null,
  cancelado: null,
  en_devolucion: "cancelado",
};

// Texto del botón según el estado actual
const TEXTO_BOTON: Record<string, string> = {
  asignado: "Marcar como En camino",
  retirado: "Marcar como En camino",
  en_camino: "Marcar como Entregado",
  en_devolucion: "Confirmar devolución al comercio",
};

// Causas de cancelación que acepta el backend (Paquete.CausaCancelacion).
const CAUSAS = [
  { valor: "fuerza_mayor", texto: "Fuerza mayor" },
  { valor: "cliente_ausente", texto: "Cliente ausente" },
  { valor: "cliente_rechaza", texto: "El cliente rechazó el pedido" },
] as const;

const AYUDA_CAUSA: Record<string, string> = {
  fuerza_mayor: "El paquete se publica como pedido cercano para otro repartidor.",
  cliente_ausente: "El paquete se devuelve al comercio; vos lo confirmás al llegar.",
  cliente_rechaza: "El paquete se devuelve al comercio; vos lo confirmás al llegar.",
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
  onActualizado: (id: number, cambios: Partial<PaqueteAsignado>) => void;
  onEliminado: (id: number) => void;
}

function PedidoItem({ paquete: p, token, onActualizado, onEliminado }: PedidoItemProps) {
  const [foto, setFoto] = useState<File | null>(null);
  const [pidiendoFoto, setPidiendoFoto] = useState(false);
  const [cancelando, setCancelando] = useState(false);
  const [causa, setCausa] = useState("");
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [exito, setExito] = useState("");

  const siguiente = SIGUIENTE_ESTADO[p.estado] ?? null;
  const finalizado = siguiente === null;
  const esDevolucion = p.estado === "en_devolucion";
  // Antes de entregar hace falta la foto; antes de cancelar, causa y motivo.
  const esEntrega = siguiente === "entregado";

  function limpiarFormularios() {
    setFoto(null);
    setCausa("");
    setMotivo("");
    setPidiendoFoto(false);
    setCancelando(false);
  }

  async function enviarCambio(
    estado: string,
    extra?: { foto?: File; causa?: string; motivo?: string },
  ) {
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
      if (extra?.causa) cuerpo.causa = extra.causa;
      if (extra?.foto) cuerpo.foto_dni = await archivoABase64(extra.foto);

      const res = await fetch(`${API_URL}/cambiar-estado-pedido/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        console.error("Error al actualizar estado:", res.status, data);
        if (data?.campo === "causa") setCausa("");
        if (data?.campo === "motivo") setMotivo("");
        if (data?.campo === "foto_dni") setFoto(null);
        setAviso(
          data?.message ??
            data?.error ??
            data?.detail ??
            `No se pudo actualizar el estado (código ${res.status})`,
        );
        return;
      }

      // El backend decide el estado final: cancelar por fuerza mayor lo pasa a
      // "pendiente_reasignacion" (sale de la lista) y por ausencia/rechazo a
      // "en_devolucion" (sigue en la lista para confirmar la devolución).
      const paqueteActualizado = data?.paquete as Partial<PaqueteAsignado> | undefined;
      const estadoFinal = paqueteActualizado?.estado ?? estado;
      const yaNoEsMio = !paqueteActualizado?.id_repartidor_asignado;
      if (yaNoEsMio) {
        onEliminado(p.id);
      } else {
        onActualizado(p.id, {
          estado: estadoFinal,
          direccion_comercio: paqueteActualizado?.direccion_comercio ?? p.direccion_comercio,
        });
      }
      setExito(
        data?.message ??
          `Estado actualizado a "${ETIQUETAS_ESTADO[estadoFinal] ?? estadoFinal}".`,
      );
      limpiarFormularios();
    } catch {
      setAviso("No se pudo conectar con el servidor");
    } finally {
      setEnviando(false);
    }
  }

  function avanzar() {
    if (!siguiente) return;

    // Antes de pasar a Entregado se pide la foto del DNI
    if (esEntrega) {
      setPidiendoFoto(true);
      setAviso("");
      setExito("");
      return;
    }

    // Confirmar la devolución al comercio no lleva datos extra
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
    if (!causa) {
      setAviso("Seleccioná el motivo de la cancelación.");
      return;
    }
    if (!motivo.trim()) {
      setAviso("Contanos brevemente qué pasó (máximo 500 caracteres).");
      return;
    }
    enviarCambio("cancelado", { causa, motivo: motivo.trim() });
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
        {esDevolucion && p.direccion_comercio && (
          <>
            <dt>Devolver a</dt>
            <dd>{p.direccion_comercio}</dd>
          </>
        )}
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
          {esDevolucion ? (
            <div className="repartidor-acciones">
              <button
                type="button"
                className="repartidor-primario"
                onClick={avanzar}
                disabled={enviando}
              >
                {enviando ? "Guardando..." : TEXTO_BOTON.en_devolucion}
              </button>
            </div>
          ) : pidiendoFoto ? (
            <>
              <label>
                Foto del DNI del receptor
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
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
              <fieldset className="repartidor-causas" disabled={enviando}>
                <legend>Motivo de la cancelación</legend>
                {CAUSAS.map((opcion) => (
                  <label key={opcion.valor} className="repartidor-causa">
                    <input
                      type="radio"
                      name={`causa-${p.id}`}
                      value={opcion.valor}
                      checked={causa === opcion.valor}
                      onChange={() => setCausa(opcion.valor)}
                    />
                    <span>{opcion.texto}</span>
                  </label>
                ))}
              </fieldset>
              {causa && <p className="repartidor-ayuda">{AYUDA_CAUSA[causa]}</p>}
              <label>
                ¿Qué pasó?
                <textarea
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  rows={2}
                  maxLength={500}
                  placeholder="Ej.: el cliente no estaba y no atendía el teléfono."
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
                    setCausa("");
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

  function actualizarEstadoLocal(id: number, cambios: Partial<PaqueteAsignado>) {
    setPaquetes((prev) => prev.map((p) => (p.id === id ? { ...p, ...cambios } : p)));
  }

  function quitarPedido(id: number) {
    setPaquetes((prev) => prev.filter((p) => p.id !== id));
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
                onEliminado={quitarPedido}
              />
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

export default DashboardRepartidor;
