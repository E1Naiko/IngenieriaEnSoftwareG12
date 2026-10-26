import { useEffect, useState } from "react";
import type { ComponentType, FormEvent, ReactNode } from "react";
import "./IngresarPedido.css";
import FormularioComercio from "../components/login/FormularioComercio";
import FormularioCliente from "../components/login/FormularioCliente";

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
    <div className="pedido-fondo" onClick={onCerrar}>
      <div className="pedido-popup" role="dialog" aria-label={titulo} onClick={(e) => e.stopPropagation()}>
        <div className="pedido-popup-head">
          <strong>{titulo}</strong>
          <button type="button" onClick={onCerrar} aria-label="Cerrar">✕</button>
        </div>
        {children}
        <div className="pedido-popup-foot">{pie}</div>
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
    <div className="pedido-campo">
      <span className="pedido-label">{etiqueta}</span>
      <button type="button" className="pedido-control" onClick={() => setAbierto(true)}>
        {valor ? texto(valor) : `Seleccionar ${singular}`}
      </button>

      {abierto && (
        <Popup
          titulo={agregando ? `Agregar ${singular}` : `Elegir ${singular}`}
          onCerrar={cerrar}
          pie={
            agregando ? null : (
              <button type="button" className="pedido-primario" onClick={() => setAgregando(true)} disabled={!FormularioAlta}>
                Agregar {singular}
              </button>
            )
          }
        >
          {agregando && FormularioAlta ? (
            <div className="pedido-popup-alta">
              <FormularioAlta onGuardado={() => setAgregando(false)} onCancelar={() => setAgregando(false)} />
            </div>
          ) : (
            <ul className="pedido-lista">
              {cargando && <li className="pedido-vacio">Cargando…</li>}
              {error && <li className="pedido-vacio">{error}</li>}
              {!cargando && !error && items.length === 0 && (
                <li className="pedido-vacio">Todavía no hay {singular}s cargados.</li>
              )}
              {items.map((it) => (
                <li key={it.id}>
                  <button type="button" className="pedido-item" onClick={() => { onChange(it); cerrar(); }}>
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
  const [fecha, setFecha] = useState(""); // formato AAAA-MM-DD
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);

  const completo = tamano !== "" && comercio !== null && cliente !== null && fecha !== "";

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
          fecha,
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
      setFecha("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form className="pedido-form" onSubmit={guardar}>
      <h1 className="pedido-titulo">Ingresar pedido</h1>

      <div className="pedido-campo">
        <label className="pedido-label" htmlFor="tamano">Tamaño del paquete</label>
        <select
          id="tamano"
          className="pedido-control"
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

      <div className="pedido-campo">
        <label className="pedido-label" htmlFor="fecha">Fecha</label>
        <input
          id="fecha"
          type="date"
          className="pedido-control"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          onClick={(e) => e.currentTarget.showPicker?.()}
          required
        />
      </div>

      {error && <p className="pedido-error">{error}</p>}
      {ok && <p className="pedido-ok">Pedido guardado.</p>}

      <button
        type="submit"
        className="pedido-primario"
        disabled={!completo || guardando}
      >
        {guardando ? "Guardando…" : "Guardar pedido"}
      </button>
    </form>
  );
}
