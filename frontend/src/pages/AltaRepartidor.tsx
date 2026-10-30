
import { useEffect, useState, type FormEvent } from "react";
import "../styles/AltaRepartidor.css";

// Endpoint del backend.
const ALTA_REPARTIDOR_URL =
  "http://127.0.0.1:8000/api/repartidores/";

const MSG_OBLIGATORIO = "Campo obligatorio";
const MSG_REPETIDO = "Este dato ya existe en el sistema";
const MSG_EXITO = "Repartidor cargado con éxito";
const MSG_DNI = "El DNI debe ser un número";
const MSG_VEHICULO = "Tipo de vehículo inválido";

// Campos que se envían al backend.
type Campo =
  | "dni"
  | "nombre"
  | "apellido"
  | "telefono"
  | "mail"
  | "tipo_vehiculo";

// Estructura de los valores del formulario.
type Valores = Record<Campo, string>;

// Estructura de los errores asociados a cada campo.
type Errores = Partial<Record<Campo, string>>;

// Valores iniciales del formulario.
const VALORES_INICIALES: Valores = {
  dni: "",
  nombre: "",
  apellido: "",
  telefono: "",
  mail: "",
  tipo_vehiculo: "",
};

// Lista de campos obligatorios.
const CAMPOS: Campo[] = [
  "dni",
  "nombre",
  "apellido",
  "telefono",
  "mail",
  "tipo_vehiculo",
];

// Opciones de vehículos permitidos.
const TIPOS_VEHICULO = [
  { value: "moto", label: "Moto" },
  { value: "auto", label: "Auto" },
  { value: "camioneta", label: "Camioneta" },
  { value: "camion", label: "Camión" },
];

// Datos que devuelve el backend cuando crea un repartidor.
interface RepartidorCreado {
  id: number;
  nombre: string;
  apellido: string;
  dni: number;
  telefono: string;
  mail: string;
  tipo_vehiculo: string;
  estado: string;
  token: string;
}

// Estructura de la respuesta exitosa del backend.
interface RespuestaAlta {
  message: string;
  repartidor: RepartidorCreado;
}

// Propiedades que recibe el modal desde el componente padre.
interface Props {
  abierto: boolean;
  onCerrar: () => void;
  onCreado?: () => void;
}

// Valida los campos antes de enviar los datos al backend.
function validar(valores: Valores): Errores {
  const errores: Errores = {};

  // Comprueba que ningún campo esté vacío.
  // También considera vacío un campo con solamente espacios.
  CAMPOS.forEach((campo) => {
    if (!valores[campo].trim()) {
      errores[campo] = MSG_OBLIGATORIO;
    }
  });

  // Comprueba que el DNI contenga solamente números.
  if (
    !errores.dni &&
    !/^\d+$/.test(valores.dni.trim())
  ) {
    errores.dni = MSG_DNI;
  }

  // Comprueba que el vehículo pertenezca a las opciones permitidas.
  if (
    !errores.tipo_vehiculo &&
    !TIPOS_VEHICULO.some(
      (vehiculo) => vehiculo.value === valores.tipo_vehiculo
    )
  ) {
    errores.tipo_vehiculo = MSG_VEHICULO;
  }

  return errores;
}

// Convierte un error del backend en un mensaje legible.
function textoDe(valor: unknown): string {
  if (Array.isArray(valor)) {
    return String(valor[0] ?? "");
  }

  if (typeof valor === "string") {
    return valor;
  }

  return "";
}

// Traduce los errores del backend a los mensajes de la HU.
function mensajeDeCampo(campo: Campo, texto: string): string {
  if (/exist|already|unique|duplic|repetid/i.test(texto)) {
    return MSG_REPETIDO;
  }

  if (/obligatorio|blank|null|required|vac[ií]o/i.test(texto)) {
    return MSG_OBLIGATORIO;
  }

  if (campo === "dni" && /number|integer|n[uú]mero/i.test(texto)) {
    return MSG_DNI;
  }

  if (campo === "tipo_vehiculo") {
    return MSG_VEHICULO;
  }

  return texto || "Dato inválido";
}

function AltaRepartidor({
  abierto,
  onCerrar,
  onCreado,
}: Props) {
  // Estados del formulario.
  const [valores, setValores] =
    useState<Valores>(VALORES_INICIALES);

  // Errores asociados a los campos.
  const [errores, setErrores] = useState<Errores>({});

  // Mensaje de error general.
  const [errorGeneral, setErrorGeneral] = useState("");

  // Indica si se está enviando el formulario.
  const [cargando, setCargando] = useState(false);

  // Guarda los datos devueltos por el backend.
  const [repartidorCreado, setRepartidorCreado] =
    useState<RepartidorCreado | null>(null);

  // Indica si el alta fue exitosa.
  const [exito, setExito] = useState(false);

  // Indica si se copió el token.
  const [copiado, setCopiado] = useState(false);

  // Limpia los estados del modal.
  function reiniciar() {
    setValores(VALORES_INICIALES);
    setErrores({});
    setErrorGeneral("");
    setRepartidorCreado(null);
    setExito(false);
    setCopiado(false);
  }

  // Cada vez que se abre el modal se limpia el formulario.
  useEffect(() => {
    if (abierto) {
      reiniciar();
    }
  }, [abierto]);

  // Permite cerrar el modal utilizando la tecla Escape.
  useEffect(() => {
    if (!abierto) return;

    function manejarTecla(event: KeyboardEvent) {
      if (event.key === "Escape" && !cargando) {
        onCerrar();
      }
    }

    window.addEventListener("keydown", manejarTecla);

    return () => {
      window.removeEventListener("keydown", manejarTecla);
    };
  }, [abierto, cargando, onCerrar]);

  // Si el modal está cerrado, no se renderiza.
  if (!abierto) return null;

  // Actualiza el valor de un campo.
  function cambiar(campo: Campo, valor: string) {
    setValores((anterior) => ({
      ...anterior,
      [campo]: valor,
    }));

    // Si el campo tenía un error, lo elimina al modificarlo.
    setErrores((anterior) => ({
      ...anterior,
      [campo]: undefined,
    }));

    setErrorGeneral("");
  }

  // Procesa el envío del formulario.
  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    // Primero se validan los datos en el frontend.
    const erroresLocales = validar(valores);

    if (Object.keys(erroresLocales).length > 0) {
      setErrores(erroresLocales);
      return;
    }

    setCargando(true);
    setErrores({});
    setErrorGeneral("");

    try {
      // Envía los datos al endpoint de Django.
      const response = await fetch(ALTA_REPARTIDOR_URL, {
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

      // Convierte la respuesta del backend a JSON.
      const data = await response.json().catch(() => null);

      // ESCENARIO 1: alta exitosa.
      if (response.ok) {
        // IMPORTANTE:
        // Django devuelve los datos dentro de data.repartidor.
        const repartidor: RepartidorCreado | undefined =
          data?.repartidor;

        if (!repartidor) {
          setErrorGeneral(
            "El servidor confirmó el alta, pero no devolvió los datos del repartidor."
          );
          return;
        }

        // Guarda TODOS los datos devueltos por Django,
        // incluido el token generado automáticamente.
        setRepartidorCreado(repartidor);

        // Muestra la pantalla de éxito.
        setExito(true);

        // Notifica al componente padre para actualizar su lista.
        onCreado?.();

        return;
      }

      // ESCENARIOS 2, 3 y 4:
      // El backend devuelve directamente un objeto con los errores.
      // Ejemplo: { dni: "...", telefono: "..." }
      if (data && typeof data === "object") {
        const mapeados: Errores = {};

        CAMPOS.forEach((campo) => {
          if (data[campo] !== undefined) {
            mapeados[campo] = mensajeDeCampo(
              campo,
              textoDe(data[campo])
            );
          }
        });

        if (Object.keys(mapeados).length > 0) {
          setErrores(mapeados);
          return;
        }
      }

      // Si no hay errores asociados a campos, muestra el error general.
      setErrorGeneral(
        textoDe(data?.message) ||
          "Error del servidor. Intentá nuevamente."
      );

    } catch {
      // Se ejecuta cuando no se puede conectar con Django.
      setErrorGeneral("No se pudo conectar con el servidor.");

    } finally {
      // Finaliza el estado de carga.
      setCargando(false);
    }
  }

  // Copia el token al portapapeles.
  async function copiarToken() {
    if (!repartidorCreado?.token) return;

    try {
      await navigator.clipboard.writeText(
        repartidorCreado.token
      );

      setCopiado(true);

    } catch {
      setCopiado(false);
      setErrorGeneral("No se pudo copiar el token.");
    }
  }

  // Renderizado del modal.
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
        onClick={(event) => event.stopPropagation()}
      >
        {/* Botón para cerrar el modal. */}
        <button
          type="button"
          className="modal-close"
          onClick={onCerrar}
          disabled={cargando}
          aria-label="Cerrar modal"
        >
          ×
        </button>

        {exito && repartidorCreado ? (
          // ESCENARIO 1: pantalla de confirmación.
          <div className="modal-success">

            <div className="success-icon">✓</div>

            <h2 id="modal-titulo">{MSG_EXITO}</h2>

            <p className="success-description">
              El repartidor fue registrado correctamente.
            </p>

            {/* Token generado por el backend. */}
            <div className="token-container">
              <span className="token-label">
                Token de acceso
              </span>

              <div className="modal-token">
                <strong>{repartidorCreado.token}</strong>

                <button
                  type="button"
                  onClick={copiarToken}
                  disabled={!repartidorCreado.token}
                >
                  {copiado ? "Copiado ✓" : "Copiar"}
                </button>
              </div>
            </div>

            {/* Datos completos del repartidor. */}
            <h3 className="datos-titulo">
              Datos del repartidor
            </h3>

            <dl className="modal-datos">

              <div>
                <dt>ID</dt>
                <dd>{repartidorCreado.id}</dd>
              </div>

              <div>
                <dt>Nombre</dt>
                <dd>
                  {repartidorCreado.nombre}{" "}
                  {repartidorCreado.apellido}
                </dd>
              </div>

              <div>
                <dt>DNI</dt>
                <dd>{repartidorCreado.dni}</dd>
              </div>

              <div>
                <dt>Celular</dt>
                <dd>{repartidorCreado.telefono}</dd>
              </div>

              <div>
                <dt>Email</dt>
                <dd>{repartidorCreado.mail}</dd>
              </div>

              <div>
                <dt>Vehículo</dt>
                <dd>
                  {TIPOS_VEHICULO.find(
                    (vehiculo) =>
                      vehiculo.value ===
                      repartidorCreado.tipo_vehiculo
                  )?.label ?? repartidorCreado.tipo_vehiculo}
                </dd>
              </div>

              <div>
                <dt>Estado</dt>
                <dd className="estado-activo">
                  {repartidorCreado.estado}
                </dd>
              </div>

            </dl>

            {/* Acciones posteriores al alta. */}
            <div className="modal-actions">

              <button
                type="button"
                className="modal-btn-secondary"
                onClick={reiniciar}
              >
                Cargar otro
              </button>

              <button
                type="button"
                className="modal-btn-primary"
                onClick={onCerrar}
              >
                Cerrar
              </button>

            </div>
          </div>

        ) : (
          // FORMULARIO DE ALTA.
          <form onSubmit={handleSubmit} noValidate>

            <h2 id="modal-titulo">
              Alta de repartidor
            </h2>

            <p className="modal-subtitulo">
              Completá los datos para registrar un nuevo repartidor.
            </p>

            {/* Campo DNI. */}
            <div className="modal-field">
              <label htmlFor="dni">DNI</label>

              <input
                id="dni"
                type="text"
                inputMode="numeric"
                value={valores.dni}
                onChange={(e) => cambiar("dni", e.target.value)}
                placeholder="Ej: 40123456"
                autoComplete="off"
                className={errores.dni ? "input-error" : ""}
              />

              {errores.dni && (
                <span className="modal-field-error">
                  {errores.dni}
                </span>
              )}
            </div>

            {/* Campo nombre. */}
            <div className="modal-field">
              <label htmlFor="nombre">Nombre</label>

              <input
                id="nombre"
                type="text"
                value={valores.nombre}
                onChange={(e) => cambiar("nombre", e.target.value)}
                placeholder="Ingresá el nombre"
                autoComplete="off"
                className={errores.nombre ? "input-error" : ""}
              />

              {errores.nombre && (
                <span className="modal-field-error">
                  {errores.nombre}
                </span>
              )}
            </div>

            {/* Campo apellido. */}
            <div className="modal-field">
              <label htmlFor="apellido">Apellido</label>

              <input
                id="apellido"
                type="text"
                value={valores.apellido}
                onChange={(e) => cambiar("apellido", e.target.value)}
                placeholder="Ingresá el apellido"
                autoComplete="off"
                className={errores.apellido ? "input-error" : ""}
              />

              {errores.apellido && (
                <span className="modal-field-error">
                  {errores.apellido}
                </span>
              )}
            </div>

            {/* Campo celular. */}
            <div className="modal-field">
              <label htmlFor="telefono">Celular</label>

              <input
                id="telefono"
                type="tel"
                value={valores.telefono}
                onChange={(e) => cambiar("telefono", e.target.value)}
                placeholder="Ej: 3777123456"
                autoComplete="off"
                className={errores.telefono ? "input-error" : ""}
              />

              {errores.telefono && (
                <span className="modal-field-error">
                  {errores.telefono}
                </span>
              )}
            </div>

            {/* Campo email. */}
            <div className="modal-field">
              <label htmlFor="mail">Email</label>

              <input
                id="mail"
                type="email"
                value={valores.mail}
                onChange={(e) => cambiar("mail", e.target.value)}
                placeholder="nombre@correo.com"
                autoComplete="off"
                className={errores.mail ? "input-error" : ""}
              />

              {errores.mail && (
                <span className="modal-field-error">
                  {errores.mail}
                </span>
              )}
            </div>

            {/* Selección del tipo de vehículo. */}
            <div className="modal-field">
              <label htmlFor="tipo_vehiculo">
                Tipo de vehículo
              </label>

              <select
                id="tipo_vehiculo"
                value={valores.tipo_vehiculo}
                onChange={(e) =>
                  cambiar("tipo_vehiculo", e.target.value)
                }
                className={
                  errores.tipo_vehiculo ? "input-error" : ""
                }
              >
                <option value="">
                  Seleccioná un vehículo
                </option>

                {TIPOS_VEHICULO.map((vehiculo) => (
                  <option
                    key={vehiculo.value}
                    value={vehiculo.value}
                  >
                    {vehiculo.label}
                  </option>
                ))}
              </select>

              {errores.tipo_vehiculo && (
                <span className="modal-field-error">
                  {errores.tipo_vehiculo}
                </span>
              )}
            </div>

            {/* Mensaje de error general. */}
            {errorGeneral && (
              <p className="modal-error" role="alert">
                {errorGeneral}
              </p>
            )}

            {/* Botones del formulario. */}
            <div className="modal-actions">

              <button
                type="button"
                className="modal-btn-secondary"
                onClick={onCerrar}
                disabled={cargando}
              >
                Cancelar
              </button>

              <button
                type="submit"
                className="modal-btn-primary"
                disabled={cargando}
              >
                {cargando
                  ? "Guardando..."
                  : "Cargar repartidor"}
              </button>

            </div>

          </form>
        )}
      </div>
    </div>
  );
}

export default AltaRepartidor;
