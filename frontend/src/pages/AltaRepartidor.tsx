import { useEffect, useState, type FormEvent } from "react";
import "../styles/AltaRepartidor.css";

// Ruta del backend para dar de alta un repartidor (POST).
const ALTA_REPARTIDOR_URL = "http://127.0.0.1:8000/api";

const MSG_OBLIGATORIO = "Campo obligatorio";
const MSG_REPETIDO = "Este dato ya existe en el sistema";
const MSG_EXITO = "Repartidor cargado con éxito";
const MSG_DNI = "El DNI debe ser un número";
const MSG_VEHICULO = "Tipo de vehículo inválido";

// Los nombres coinciden con los campos del modelo Repartidor del backend.
type Campo = "dni" | "nombre" | "apellido" | "telefono" | "mail" | "tipo_vehiculo";
type Valores = Record<Campo, string>;
type Errores = Partial<Record<Campo, string>>;

const VALORES_INICIALES: Valores = {
  dni: "",
  nombre: "",
  apellido: "",
  telefono: "",
  mail: "",
  tipo_vehiculo: "",
};

const CAMPOS: Campo[] = ["dni", "nombre", "apellido", "telefono", "mail", "tipo_vehiculo"];

const CAMPOS_TEXTO: {
  campo: Exclude<Campo, "tipo_vehiculo">;
  etiqueta: string;
  type: string;
  inputMode?: "numeric" | "tel" | "email" | "text";
  placeholder: string;
}[] = [
  { campo: "dni", etiqueta: "DNI", type: "text", inputMode: "numeric", placeholder: "Ej: 40123456" },
  { campo: "nombre", etiqueta: "Nombre", type: "text", placeholder: "Ingresá el nombre" },
  { campo: "apellido", etiqueta: "Apellido", type: "text", placeholder: "Ingresá el apellido" },
  { campo: "telefono", etiqueta: "Celular", type: "tel", inputMode: "tel", placeholder: "Ej: 3777123456" },
  { campo: "mail", etiqueta: "Email", type: "email", inputMode: "email", placeholder: "nombre@correo.com" },
];

// Tipos permitidos por la historia de usuario: moto, auto, camioneta y camión.
const TIPOS_VEHICULO = [
  { value: "moto", label: "Moto" },
  { value: "auto", label: "Auto" },
  { value: "camioneta", label: "Camioneta" },
  { value: "camion", label: "Camión" },
];

function validar(valores: Valores): Errores {
  const errores: Errores = {};

  // Escenario 2: un campo vacío o solo con espacios se considera en blanco
  CAMPOS.forEach((campo) => {
    if (!valores[campo].trim()) errores[campo] = MSG_OBLIGATORIO;
  });

  // Escenario 4: formato inválido (solo se revisa si el campo no está vacío)
  if (!errores.dni && !/^\d+$/.test(valores.dni.trim())) {
    errores.dni = MSG_DNI;
  }
  if (!errores.tipo_vehiculo && !TIPOS_VEHICULO.some((t) => t.value === valores.tipo_vehiculo)) {
    errores.tipo_vehiculo = MSG_VEHICULO;
  }
  if (!errores.mail && !/^\S+@\S+\.\S+$/.test(valores.mail.trim())) {
    errores.mail = "Email inválido";
  }
  return errores;
}

// Detecta si el texto que manda el backend habla de un dato repetido.
function esRepetido(texto: string) {
  return /exist|already|unique|duplic|repetid/i.test(texto);
}

// Detecta si el texto que manda el backend habla de un campo vacío.
function esVacio(texto: string) {
  return !texto || /obligatorio|blank|null|field is required|vac[ií]o/i.test(texto);
}

function textoDe(valor: unknown): string {
  return Array.isArray(valor) ? String(valor[0] ?? "") : String(valor ?? "");
}

// Traduce el error que manda el backend para un campo al mensaje de la historia.
function mensajeDeCampo(campo: Campo, texto: string): string {
  if (esRepetido(texto)) return MSG_REPETIDO;
  if (esVacio(texto)) return MSG_OBLIGATORIO;
  if (campo === "dni") return MSG_DNI;
  if (campo === "tipo_vehiculo") return MSG_VEHICULO;
  return texto;
}

// Datos que devuelve el backend al crear el repartidor (incluye el token).
interface RepartidorCreado {
  id?: number;
  nombre?: string;
  apellido?: string;
  dni?: number;
  telefono?: string;
  mail?: string;
  tipo_vehiculo?: string;
  estado?: string;
  token?: string;
}

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  onCreado?: () => void; // para que la pantalla del coordinador refresque su lista
}

function AltaRepartidor({ abierto, onCerrar, onCreado }: Props) {
  const [valores, setValores] = useState<Valores>(VALORES_INICIALES);
  const [errores, setErrores] = useState<Errores>({});
  const [errorGeneral, setErrorGeneral] = useState("");
  const [cargando, setCargando] = useState(false);
  const [tokenCreado, setTokenCreado] = useState<string | null>(null);
  const [repartidorCreado, setRepartidorCreado] = useState<RepartidorCreado | null>(null);
  const [exito, setExito] = useState(false);
  const [copiado, setCopiado] = useState(false);

  function reiniciar() {
    setValores(VALORES_INICIALES);
    setErrores({});
    setErrorGeneral("");
    setTokenCreado(null);
    setRepartidorCreado(null);
    setExito(false);
    setCopiado(false);
  }

  // Cada vez que se abre el modal arranca con el formulario limpio
  useEffect(() => {
    if (abierto) reiniciar();
  }, [abierto]);

  // Escape cierra el modal
  useEffect(() => {
    if (!abierto) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !cargando) onCerrar();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [abierto, cargando, onCerrar]);

  if (!abierto) return null;

  function cambiar(campo: Campo, valor: string) {
    setValores((prev) => ({ ...prev, [campo]: valor }));
    if (errores[campo]) setErrores((prev) => ({ ...prev, [campo]: undefined }));
    if (errorGeneral) setErrorGeneral("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    // Escenarios 2 y 4: valida en el front antes de enviar al backend
    const erroresLocales = validar(valores);
    if (Object.keys(erroresLocales).length > 0) {
      setErrores(erroresLocales);
      return;
    }

    setCargando(true);
    setErrores({});
    setErrorGeneral("");

    try {
      const response = await fetch(`${ALTA_REPARTIDOR_URL}/repartidores/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dni: Number(valores.dni.trim()),
          nombre: valores.nombre.trim(),
          apellido: valores.apellido.trim(),
          telefono: valores.telefono.trim(),
          mail: valores.mail.trim(),
          tipo_vehiculo: valores.tipo_vehiculo,
        }),
      });

      const data = await response.json().catch(() => null);

      // Escenario 1: alta exitosa → mensaje de éxito, datos del repartidor y token
      if (response.ok) {
        setRepartidorCreado(data ?? null);
        setTokenCreado(data?.token ?? null);
        setExito(true);
        onCreado?.();
        return;
      }

      // Escenarios 2, 3 y 4 desde el backend: errores asociados a cada campo
      const erroresServidor = data?.errors ?? data?.errores;
      if (erroresServidor && typeof erroresServidor === "object") {
        const mapeados: Errores = {};
        CAMPOS.forEach((campo) => {
          if (erroresServidor[campo] !== undefined) {
            mapeados[campo] = mensajeDeCampo(campo, textoDe(erroresServidor[campo]));
          }
        });
        if (Object.keys(mapeados).length > 0) {
          setErrores(mapeados);
          return;
        }
      }

      const mensaje = textoDe(data?.message);
      if (response.status === 409 || esRepetido(mensaje)) {
        setErrorGeneral(MSG_REPETIDO);
      } else {
        setErrorGeneral(mensaje || "Error del servidor. Intentá de nuevo");
      }
    } catch {
      setErrorGeneral("No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }

  async function copiarToken() {
    if (!tokenCreado) return;
    try {
      await navigator.clipboard.writeText(tokenCreado);
      setCopiado(true);
    } catch {
      setCopiado(false);
    }
  }

  return (
    <div
      className="modal-overlay"
      onClick={() => !cargando && onCerrar()}
      role="presentation"
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-titulo"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="modal-close"
          onClick={onCerrar}
          disabled={cargando}
          aria-label="Cerrar"
        >
          ×
        </button>

        {exito ? (
          <div className="modal-success">
            <h2 id="modal-titulo">{MSG_EXITO}</h2>

            {tokenCreado && (
              <>
                <p>Token de acceso generado para el repartidor:</p>
                <div className="modal-token">
                  <span>{tokenCreado}</span>
                  <button type="button" onClick={copiarToken}>
                    {copiado ? "Copiado" : "Copiar"}
                  </button>
                </div>
              </>
            )}

            {repartidorCreado && (
              <dl className="modal-datos">
                <dt>Nombre</dt>
                <dd>
                  {repartidorCreado.nombre} {repartidorCreado.apellido}
                </dd>
                <dt>DNI</dt>
                <dd>{repartidorCreado.dni}</dd>
                <dt>Celular</dt>
                <dd>{repartidorCreado.telefono}</dd>
                <dt>Email</dt>
                <dd>{repartidorCreado.mail}</dd>
                <dt>Vehículo</dt>
                <dd>
                  {TIPOS_VEHICULO.find((t) => t.value === repartidorCreado.tipo_vehiculo)?.label ??
                    repartidorCreado.tipo_vehiculo}
                </dd>
                <dt>Estado</dt>
                <dd>{repartidorCreado.estado}</dd>
              </dl>
            )}

            <div className="modal-actions">
              <button type="button" className="modal-btn-secondary" onClick={reiniciar}>
                Cargar otro
              </button>
              <button type="button" className="modal-btn-primary" onClick={onCerrar}>
                Cerrar
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <h2 id="modal-titulo">Cargar repartidor</h2>

            {CAMPOS_TEXTO.map(({ campo, etiqueta, type, inputMode, placeholder }) => (
              <div className="modal-field" key={campo}>
                <label htmlFor={campo}>{etiqueta}</label>
                <input
                  id={campo}
                  type={type}
                  inputMode={inputMode}
                  value={valores[campo]}
                  onChange={(e) => cambiar(campo, e.target.value)}
                  placeholder={placeholder}
                  autoComplete="off"
                  className={errores[campo] ? "input-error" : ""}
                />
                {errores[campo] && <span className="modal-field-error">{errores[campo]}</span>}
              </div>
            ))}

            <div className="modal-field">
              <label htmlFor="tipo_vehiculo">Tipo de vehículo</label>
              <select
                id="tipo_vehiculo"
                value={valores.tipo_vehiculo}
                onChange={(e) => cambiar("tipo_vehiculo", e.target.value)}
                className={errores.tipo_vehiculo ? "input-error" : ""}
              >
                <option value="">Seleccioná un vehículo</option>
                {TIPOS_VEHICULO.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              {errores.tipo_vehiculo && (
                <span className="modal-field-error">{errores.tipo_vehiculo}</span>
              )}
            </div>

            {errorGeneral && (
              <p className="modal-error" role="alert">
                {errorGeneral}
              </p>
            )}

            <div className="modal-actions">
              <button
                type="button"
                className="modal-btn-secondary"
                onClick={onCerrar}
                disabled={cargando}
              >
                Cancelar
              </button>
              <button type="submit" className="modal-btn-primary" disabled={cargando}>
                {cargando ? "Guardando..." : "Cargar repartidor"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default AltaRepartidor;