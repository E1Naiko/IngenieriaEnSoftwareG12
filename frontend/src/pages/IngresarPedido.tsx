import { useEffect, useState } from "react";
import type { ComponentType, FormEvent, ReactNode } from "react";
import FormularioComercio from "../components/login/FormularioComercio";
import FormularioCliente from "../components/login/FormularioCliente";
import "./IngresarPedido.css";

/* ---------- Tipos ---------- */

export type Tamano = "pequeño" | "mediano" | "grande";

export interface Comercio {
  id: number;
  nombre: string;
}

export interface Cliente {
  id: number;
  nombre: string;
  dni?: number;
  direccion?: string;
}

// Props que recibirán tus formularios de alta (el de comercio ya lo tenés).
export interface FormularioAltaProps {
  onGuardado: () => void; // llamalo cuando se guarde bien
  onCancelar: () => void;
}

/* ---------- Endpoints ---------- */

const URL_COMERCIOS = "/api/comercios/";
const URL_CLIENTES = "/api/clientes/";
const URL_PEDIDOS = "/api/pedidos/"; // a crear en el backend

/* ---------- Popup genérico ---------- */

interface PopupProps {
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
  pie: ReactNode;
}

function Popup({ titulo, onCerrar, children, pie }: PopupProps) {
  return (
    <div className="fondo" onClick={onCerrar}>
      <div className="popup" role="dialog" aria-label={titulo} onClick={(e) => e.stopPropagation()}>
        <div className="popup-head">
          <strong>{titulo}</strong>
          <button type="button" onClick={onCerrar} aria-label="Cerrar">✕</button>
        </div>
        {children}
        <div className="popup-foot">{pie}</div>
      </div>
    </div>
  );
}

/* ---------- Botón select con popup (sirve para comercio y cliente) ---------- */

interface SelectorProps<T extends { id: number }> {
  etiqueta: string;          // "Comercio", "Cliente"
  singular: string;          // "comercio", "cliente"
  url: string;
  texto: (item: T) => string;
  valor: T | null;
  onChange: (item: T) => void;
  FormularioAlta?: ComponentType<FormularioAltaProps>;
}

function SelectorConPopup<T extends { id: number }>({
  etiqueta, singular, url, texto, valor, onChange, FormularioAlta,
}: SelectorProps<T>) {
  const [abierto, setAbierto] = useState(false);
  const [agregando, setAgregando] = useState(false);
  const [items, setItems] = useState<T[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  async function cargar() {
    setCargando(true);
    setError("");
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setItems(data.results ?? data);
    } catch {
      setError(`No se pudieron cargar los ${singular}s. Reintentá.`);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    if (abierto && !agregando) cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, agregando]);

  const cerrar = () => { setAbierto(false); setAgregando(false); };

  return (
    <div className="campo">
      <span className="label">{etiqueta}</span>
      <button type="button" className="control" onClick={() => setAbierto(true)}>
        {valor ? texto(valor) : `Seleccionar ${singular}`}
      </button>

      {abierto && (
        <Popup
          titulo={agregando ? `Agregar ${singular}` : `Elegir ${singular}`}
          onCerrar={cerrar}
          pie={
            agregando ? null : (
              <button type="button" className="primario" onClick={() => setAgregando(true)} disabled={!FormularioAlta}>
                Agregar {singular}
              </button>
            )
          }
        >
          {agregando && FormularioAlta ? (
            <div style={{ padding: 16, overflowY: "auto" }}>
              <FormularioAlta onGuardado={() => setAgregando(false)} onCancelar={() => setAgregando(false)} />
            </div>
          ) : (
            <ul className="lista">
              {cargando && <li className="vacio">Cargando…</li>}
              {error && <li className="vacio">{error}</li>}
              {!cargando && !error && items.length === 0 && (
                <li className="vacio">Todavía no hay {singular}s cargados.</li>
              )}
              {items.map((it) => (
                <li key={it.id}>
                  <button type="button" className="item" onClick={() => { onChange(it); cerrar(); }}>
                    {texto(it)}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Popup>
      )}
    </div>
  );
}

/* ---------- Pantalla principal ---------- */

export default function IngresarPedido() {
  const [tamano, setTamano] = useState<Tamano | "">("");
  const [comercio, setComercio] = useState<Comercio | null>(null);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);

  const completo = tamano !== "" && comercio !== null && cliente !== null;

  async function guardar(e: FormEvent) {
    e.preventDefault();
    if (!completo) return;
    setError("");
    setOk(false);
    setGuardando(true);
    try {
      const res = await fetch(URL_PEDIDOS, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tamano,
          comercio: comercio.id,
          cliente: cliente.id,
        }),
      });
      if (!res.ok) {
        setError(JSON.stringify(await res.json().catch(() => ({}))));
        return;
      }
      setOk(true);
      setTamano("");
      setComercio(null);
      setCliente(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form className="form" onSubmit={guardar}>
      <h1 style={{ margin: 0, fontSize: 24 }}>Ingresar pedido</h1>

      <div className="campo">
        <label className="label" htmlFor="tamano">Tamaño del paquete</label>
        <select
          id="tamano"
          className="control"
          value={tamano}
          onChange={(e) => setTamano(e.target.value as Tamano)}
        >
          <option value="" disabled>Elegir tamaño</option>
          <option value="pequeño">Pequeño</option>
          <option value="mediano">Mediano</option>
          <option value="grande">Grande</option>
        </select>
      </div>

      <SelectorConPopup<Comercio>
        etiqueta="Comercio"
        singular="comercio"
        url={URL_COMERCIOS}
        texto={(c) => c.nombre}
        valor={comercio}
        onChange={setComercio}
        FormularioAlta={FormularioComercio}
      />

      <SelectorConPopup<Cliente>
        etiqueta="Cliente"
        singular="cliente"
        url={URL_CLIENTES}
        texto={(c) => (c.dni ? `${c.nombre} (DNI ${c.dni})` : c.nombre)}
        valor={cliente}
        onChange={setCliente}
        FormularioAlta={FormularioCliente}
      />

      {error && <p style={{ color: "red", margin: 0 }}>{error}</p>}
      {ok && <p style={{ color: "green", margin: 0 }}>Pedido guardado.</p>}

      <button
        type="submit"
        className="primario"
        style={{ opacity: completo && !guardando ? 1 : 0.5 }}
        disabled={!completo || guardando}
      >
        {guardando ? "Guardando…" : "Guardar pedido"}
      </button>
    </form>
  );
}