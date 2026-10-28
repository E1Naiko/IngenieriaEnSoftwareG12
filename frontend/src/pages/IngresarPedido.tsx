import { useEffect, useState } from "react";
import type { ComponentType, FormEvent, ReactNode } from "react";
import "./IngresarPedido.css";
import FormularioComercio from "../components/formularios/FormularioComercio";
import FormularioCliente from "../components/formularios/FormularioCliente";
import { createPortal } from "react-dom";
/* ---------- Tipos ---------- */
// Valores que acepta el back (el texto que ve el usuario puede ser otro)
export type Tamano = "chico" | "mediano" | "grande";

export interface Comercio {
  id: number;
  nombre: string;
}

export interface Cliente {
  id: number;
  nombre: string;
  apellido: string;
  dni: number;
  direccion: string;
  telefono?: string;
}

// Pedido que devuelve el back dentro del 409
interface PedidoSimilar {
  id: number;
  cod_seguimiento: string;
  estado: string;
  tamanio: string;
  comercio: number;
  cliente: number;
  fecha_origen: string;
  fecha_destino: string;
}

interface AvisoSimilar {
  detail: string;
  similar?: PedidoSimilar;
}

// Props que reciben los formularios de alta
export interface FormularioAltaProps {
  onGuardado: () => void; // se llama cuando se guarda bien
  onCancelar: () => void;
}

/* ---------- Endpoints ---------- */

const URL_COMERCIOS = "/api/comercios/";
const URL_CLIENTES = "/api/clientes/";
const URL_PEDIDOS = "/api/pedidos/";

/* ---------- Popup genérico ---------- */

interface PopupProps {
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
  pie: ReactNode;
}


function Popup({ titulo, onCerrar, children, pie }: PopupProps) {
  // Portal: el popup se dibuja fuera del <form> del pedido, porque los
  // formularios de alta tienen su propio <form> y HTML no permite anidarlos.
  return createPortal(
    <div className="fondo" onClick={onCerrar}
         // En React el submit igual sube al form del pedido aunque haya portal: se corta acá
         onSubmit={(e) => e.stopPropagation()}>
      ...lo mismo que hoy...
    </div>,
    document.body,
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
  const [fecha, setFecha] = useState(""); // fecha de entrega, formato AAAA-MM-DD
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);
  const [aviso, setAviso] = useState<AvisoSimilar | null>(null);

  const completo = tamano !== "" && comercio !== null && cliente !== null && fecha !== "";

  async function enviar(forzar: boolean) {
    if (tamano === "" || !comercio || !cliente || fecha === "") return;
    setError("");
    setOk(false);
    setGuardando(true);
    try {
      const body: Record<string, unknown> = {
        comercio: comercio.id,
        cliente: cliente.id,
        tamanio: tamano,
        fecha_destino: fecha,
      };
      if (forzar) body.forzar = true;

      const res = await fetch(URL_PEDIDOS, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      // Ya existe un pedido similar: se pregunta si se carga igualmente
      if (res.status === 409) {
        const data = await res.json().catch(() => ({}));
        setAviso({
          detail: data.detail ?? "Hay un pedido similar ¿Desea cargarlo igualmente?",
          similar: data.similar,
        });
        return;
      }

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

  function guardar(e: FormEvent) {
    e.preventDefault();
    enviar(false);
  }

  function cargarIgualmente() {
    setAviso(null);
    enviar(true);
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
          <option value="chico">Chico</option>
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
        texto={(c) => `${c.nombre} ${c.apellido} – DNI ${c.dni}`}
        valor={cliente}
        onChange={setCliente}
        FormularioAlta={FormularioCliente}
      />

      <div className="pedido-campo">
        <label className="pedido-label" htmlFor="fecha">Fecha de entrega</label>
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

      {aviso && (
        <Popup
          titulo="Pedido similar"
          onCerrar={() => setAviso(null)}
          pie={
            <div className="pedido-botones">
              <button type="button" className="pedido-secundario" onClick={() => setAviso(null)}>
                Cancelar
              </button>
              <button type="button" className="pedido-primario" onClick={cargarIgualmente}>
                Cargar igualmente
              </button>
            </div>
          }
        >
          <div className="pedido-similar">
            <p className="pedido-similar-texto">{aviso.detail}</p>
            {aviso.similar && (
              <dl className="pedido-similar-datos">
                <dt>Código</dt>
                <dd>{aviso.similar.cod_seguimiento}</dd>
                <dt>Estado</dt>
                <dd>{aviso.similar.estado}</dd>
                <dt>Tamaño</dt>
                <dd>{aviso.similar.tamanio}</dd>
                <dt>Fecha de carga</dt>
                <dd>{aviso.similar.fecha_origen}</dd>
                <dt>Fecha de entrega</dt>
                <dd>{aviso.similar.fecha_destino}</dd>
              </dl>
            )}
          </div>
        </Popup>
      )}
    </form>
  );
}
