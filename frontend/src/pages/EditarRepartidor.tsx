import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/EditarRepartidor.css";
// Importación del componente para dar de alta repartidores.
import AltaRepartidor from "./AltaRepartidor";

// Definición de tipos y constantes para la validación de campos y mensajes de error.
interface Repartidor {
  id: number;
  dni: number | string;
  nombre: string;
  apellido: string;
  token: string;
  telefono: string;
  mail: string;
  tipo_vehiculo: string;
}
// Definición de la interfaz para la lista de repartidores.
interface RepartidorLista {
  id: number;
  dni: number | string;
  nombre: string;
  apellido: string;
}
// Definición de tipos para los campos del formulario, valores y errores.
type Campo =
  | "dni"
  | "nombre"
  | "apellido"
  | "telefono"
  | "mail"
  | "tipo_vehiculo";
// Definición de tipos para los valores y errores del formulario.
type Valores = Record<Campo, string>;
type Errores = Partial<Record<Campo, string>>;

const MSG_OBLIGATORIO = "Campo obligatorio";
const MSG_REPETIDO = "Este dato ya existe en el sistema";
const MSG_DNI = "El DNI debe contener solamente números";
const MSG_TELEFONO = "El celular debe contener solamente números";
const MSG_MAIL = "Ingresá un email válido";
const MSG_VEHICULO = "Seleccioná un tipo de vehículo";
const MSG_NOMBRE = "El nombre solo puede contener letras";
const MSG_APELLIDO = "El apellido solo puede contener letras";

const TIPOS_VEHICULO = [
  { value: "moto", label: "Moto" },
  { value: "auto", label: "Auto" },
  { value: "camioneta", label: "Camioneta" },
  { value: "camion", label: "Camión" },
];
// Valores iniciales para el formulario de edición de repartidores.
const VALORES_INICIALES: Valores = {
  dni: "",
  nombre: "",
  apellido: "",
  telefono: "",
  mail: "",
  tipo_vehiculo: "",
};

// Función para validar que un valor contenga solo números
function contieneSoloNumeros(valor: string): boolean {
  return /^[0-9]+$/.test(valor);
}

// Función para validar que un valor contenga solo letras y espacios
function contieneSoloLetras(valor: string): boolean {
  return /^[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ\s]+$/.test(valor);
}
// Función para validar los valores del formulario y devolver los errores correspondientes
function validar(valores: Valores): Errores {
  const errores: Errores = {};

  if (!valores.dni.trim()) errores.dni = MSG_OBLIGATORIO;
  if (!valores.nombre.trim()) errores.nombre = MSG_OBLIGATORIO;
  if (!valores.apellido.trim()) errores.apellido = MSG_OBLIGATORIO;
  if (!valores.telefono.trim()) errores.telefono = MSG_OBLIGATORIO;
  if (!valores.mail.trim()) errores.mail = MSG_OBLIGATORIO;
  if (!valores.tipo_vehiculo.trim()) errores.tipo_vehiculo = MSG_OBLIGATORIO;

  if (!errores.dni && !contieneSoloNumeros(valores.dni.trim())) {
    errores.dni = MSG_DNI;
  }
  // Validar que el teléfono contenga solamente números.
  if (!errores.telefono && !contieneSoloNumeros(valores.telefono.trim())) {
    errores.telefono = MSG_TELEFONO;
  }

  // Validar que el nombre contenga solamente letras.
  if (
    !errores.nombre &&
    !contieneSoloLetras(valores.nombre.trim())
  ) {
    errores.nombre = MSG_NOMBRE;
  }

  // Validar que el apellido contenga solamente letras.
  if (
    !errores.apellido &&
    !contieneSoloLetras(valores.apellido.trim())
  ) {
    errores.apellido = MSG_APELLIDO;
  }
  // Validar que el email tenga un formato válido.
  if (
    !errores.mail &&
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valores.mail.trim())
  ) {
    errores.mail = MSG_MAIL;
  }

  if (
    !errores.tipo_vehiculo &&
    !TIPOS_VEHICULO.some((vehiculo) => vehiculo.value === valores.tipo_vehiculo)
  ) {
    errores.tipo_vehiculo = MSG_VEHICULO;
  }

  return errores;
}

function textoDe(valor: unknown): string {
  if (Array.isArray(valor)) return String(valor[0] ?? "");
  if (typeof valor === "string") return valor;
  return "";
}
// Función para mapear los mensajes de error del backend a mensajes más amigables para el usuario
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

  if (campo === "telefono" && /number|integer|n[uú]mero/i.test(texto)) {
    return MSG_TELEFONO;
  }

  if (campo === "mail" && /email|correo|valid/i.test(texto)) {
    return MSG_MAIL;
  }

  if (campo === "tipo_vehiculo") return MSG_VEHICULO;

  return texto || "Dato inválido";
}

function EditarRepartidor() {
  const navigate = useNavigate();

  const [repartidores, setRepartidores] = useState<RepartidorLista[]>([]);
  const [repartidor, setRepartidor] = useState<Repartidor | null>(null);

  const [cargandoLista, setCargandoLista] = useState(true);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [cargando, setCargando] = useState(false);

  const [errorLista, setErrorLista] = useState("");
  const [errorGeneral, setErrorGeneral] = useState("");
  const [valores, setValores] = useState<Valores>(VALORES_INICIALES);
  const [errores, setErrores] = useState<Errores>({});
  const [exito, setExito] = useState(false);

  // Controla la ventana modal para dar de alta repartidores.
  const [modalRepartidorAbierto, setModalRepartidorAbierto] =useState(false);


  // Carga la lista que se ofrece para seleccionar.
  async function cargarRepartidores() {
    try {
      setCargandoLista(true);
      setErrorLista("");

      const response = await fetch(
        "/api/repartidores/lista"
      );

      if (!response.ok) {
        throw new Error("No se pudo cargar la lista de repartidores.");
      }

      const data = await response.json();
      setRepartidores(data.repartidores ?? []);
    } catch (error) {
      setErrorLista(
        error instanceof Error
          ? error.message
          : "Error al cargar los repartidores."
      );
    } finally {
      setCargandoLista(false);
    }
  }

  useEffect(() => {
    void cargarRepartidores();
  }, []);

  // Obtiene los datos completos del repartidor seleccionado.
  async function seleccionarRepartidor(id: number) {
    try {
      setCargandoDetalle(true);
      setErrorLista("");

      const response = await fetch(`/api/repartidores/${id}/`);

      if (!response.ok) {
        throw new Error("No se pudieron obtener los datos del repartidor.");
      }

      const data = await response.json();

      if (!data.repartidor) {
        throw new Error("El servidor no devolvió los datos del repartidor.");
      }

      setRepartidor({
        id,
        ...data.repartidor,
      });
    } catch (error) {
      setErrorLista(
        error instanceof Error
          ? error.message
          : "Error al seleccionar el repartidor."
      );
    } finally {
      setCargandoDetalle(false);
    }
  }

  // Cuando se selecciona un repartidor, carga sus datos en el formulario.
  useEffect(() => {
    if (!repartidor) return;

    setValores({
      dni: String(repartidor.dni ?? ""),
      nombre: repartidor.nombre ?? "",
      apellido: repartidor.apellido ?? "",
      telefono: repartidor.telefono ?? "",
      mail: repartidor.mail ?? "",
      tipo_vehiculo: repartidor.tipo_vehiculo ?? "",
    });

    setErrores({});
    setErrorGeneral("");
    setExito(false);
  }, [repartidor]);

  function cambiar(campo: Campo, valor: string) {
    setValores((anterior) => ({
      ...anterior,
      [campo]: valor,
    }));

    setErrores((anterior) => ({
      ...anterior,
      [campo]: undefined,
    }));

    setErrorGeneral("");
  }

  // Envía al backend todos los campos editables mediante PUT.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Si no hay repartidor seleccionado, no se puede enviar el formulario.
    if (!repartidor) return;

    const erroresLocales = validar(valores);

    if (Object.keys(erroresLocales).length > 0) {
      setErrores(erroresLocales);
      return;
    }

    setCargando(true);
    setErrores({});
    setErrorGeneral("");

    try {
      const response = await fetch(`/api/repartidores/${repartidor.id}/`, {
        method: "PUT",
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

      if (response.ok) {
        setExito(true);
        return;
      }

      if (data && typeof data === "object") {
        const datosError = data as Record<string, unknown>;
        const campos: Campo[] = [
          "dni",
          "nombre",
          "apellido",
          "telefono",
          "mail",
          "tipo_vehiculo",
        ];

        const erroresBackend: Errores = {};

        campos.forEach((campo) => {
          if (datosError[campo] !== undefined) {
            erroresBackend[campo] = mensajeDeCampo(
              campo,
              textoDe(datosError[campo])
            );
          }
        });

        if (Object.keys(erroresBackend).length > 0) {
          setErrores(erroresBackend);
          return;
        }
      }

      setErrorGeneral(
        textoDe(
          data && typeof data === "object"
            ? (data as Record<string, unknown>).message
            : null
        ) || "No se pudieron modificar los datos. Intentá nuevamente."
      );
    } catch {
      setErrorGeneral("No se pudo conectar con el servidor.");
    } finally {
      setCargando(false);
    }
  }

  function volverALista() {
    setRepartidor(null);
    setValores(VALORES_INICIALES);
    setErrores({});
    setErrorGeneral("");
    setExito(false);
    void cargarRepartidores();
  }

  return (
    <main className="editar-pagina">
      {!repartidor ? (
        <section className="editar-lista">
          <div className="editar-header">
            <div>
              <h1>Gestionar Repartidores</h1>

              <p className="editar-subtitulo">
                Seleccioná el repartidor cuyos datos querés modificar.
              </p>
            </div>

            <button
              type="button"
              className="editar-btn editar-btn-principal"
              onClick={() => setModalRepartidorAbierto(true)}
            >
              🚚 Alta Repartidor
            </button>
          </div>

          {cargandoLista && <p>Cargando repartidores...</p>}

          {errorLista && (
            <p className="editar-error-general" role="alert">
              {errorLista}
            </p>
          )}

          {!cargandoLista && !errorLista && repartidores.length === 0 && (
            <p>No hay repartidores para mostrar.</p>
          )}

          {!cargandoLista &&
            repartidores.map((item) => (
              <div className="editar-repartidor-item" key={item.id}>
                <div>
                  <strong>
                    {item.nombre} {item.apellido}
                  </strong>
                  <p>DNI: {item.dni}</p>
                </div>

                <button
                  type="button"
                  onClick={() => void seleccionarRepartidor(item.id)}
                  disabled={cargandoDetalle}
                >
                  {cargandoDetalle ? "Cargando..." : "Seleccionar"}
                </button>
              </div>
            ))}
            
            {/*Boton para volver al Dashboard o pagina principal */}
          <div className="editar-acciones">
            <button
              type="button"
              className="editar-btn editar-btn-secundario"
              onClick={() => navigate("/dashboard")}
            >
              Volver
            </button>
          </div>
        </section>
      ) : (
        <section className="editar-formulario">
          {exito ? (
            <div className="editar-exito">
              <div className="editar-exito-icono">✓</div>
              <h2>Repartidor modificado con éxito</h2>
              <p>Los datos del repartidor se actualizaron correctamente.</p>

              <div className="editar-acciones">
                <button
                  type="button"
                  className="editar-btn editar-btn-secundario"
                  onClick={volverALista}
                >
                  Volver a la lista
                </button>
                <button
                  type="button"
                  className="editar-btn editar-btn-principal"
                  onClick={() => navigate("/dashboard")}
                >
                  Ir al dashboard
                </button>
              </div>
            </div>
          ) : (
            <>
              <h1>Editar repartidor</h1>
              <p className="editar-subtitulo">
                Modificá los datos de {repartidor.nombre} {repartidor.apellido}.
              </p>

              <form onSubmit={handleSubmit} noValidate>
                <div className="editar-campo">
                  <label htmlFor="editar-dni">DNI</label>
                  <input
                    id="editar-dni"
                    type="text"
                    inputMode="numeric"
                    value={valores.dni}
                    onChange={(e) => cambiar("dni", e.target.value)}
                    className={errores.dni ? "editar-input-error" : ""}
                  />
                  {errores.dni && (
                    <span className="editar-error">{errores.dni}</span>
                  )}
                </div>

                <div className="editar-campo">
                  <label htmlFor="editar-nombre">Nombre</label>
                  <input
                    id="editar-nombre"
                    type="text"
                    value={valores.nombre}
                    onChange={(e) => cambiar("nombre", e.target.value)}
                    className={errores.nombre ? "editar-input-error" : ""}
                  />
                  {errores.nombre && (
                    <span className="editar-error">{errores.nombre}</span>
                  )}
                </div>

                <div className="editar-campo">
                  <label htmlFor="editar-apellido">Apellido</label>
                  <input
                    id="editar-apellido"
                    type="text"
                    value={valores.apellido}
                    onChange={(e) => cambiar("apellido", e.target.value)}
                    className={errores.apellido ? "editar-input-error" : ""}
                  />
                  {errores.apellido && (
                    <span className="editar-error">{errores.apellido}</span>
                  )}
                </div>

                <div className="editar-campo">
                  <label htmlFor="editar-token">Token</label>
                  <input
                    id="editar-token"
                    type="text"
                    value={repartidor.token ?? ""}
                    readOnly
                    className="editar-input-solo-lectura"
                  />
                </div>

                <div className="editar-campo">
                  <label htmlFor="editar-telefono">Celular</label>
                  <input
                    id="editar-telefono"
                    type="tel"
                    inputMode="numeric"
                    value={valores.telefono}
                    onChange={(e) => cambiar("telefono", e.target.value)}
                    className={errores.telefono ? "editar-input-error" : ""}
                  />
                  {errores.telefono && (
                    <span className="editar-error">{errores.telefono}</span>
                  )}
                </div>

                <div className="editar-campo">
                  <label htmlFor="editar-mail">Email</label>
                  <input
                    id="editar-mail"
                    type="email"
                    value={valores.mail}
                    onChange={(e) => cambiar("mail", e.target.value)}
                    placeholder="nombre@correo.com"
                    className={errores.mail ? "editar-input-error" : ""}
                  />
                  {errores.mail && (
                    <span className="editar-error">{errores.mail}</span>
                  )}
                </div>

                <div className="editar-campo">
                  <label htmlFor="editar-vehiculo">Tipo de vehículo</label>
                  <select
                    id="editar-vehiculo"
                    value={valores.tipo_vehiculo}
                    onChange={(e) =>
                      cambiar("tipo_vehiculo", e.target.value)
                    }
                    className={
                      errores.tipo_vehiculo ? "editar-input-error" : ""
                    }
                  >
                    <option value="">Seleccioná un vehículo</option>
                    {TIPOS_VEHICULO.map((vehiculo) => (
                      <option key={vehiculo.value} value={vehiculo.value}>
                        {vehiculo.label}
                      </option>
                    ))}
                  </select>
                  {errores.tipo_vehiculo && (
                    <span className="editar-error">
                      {errores.tipo_vehiculo}
                    </span>
                  )}
                </div>

                {errorGeneral && (
                  <p className="editar-error-general" role="alert">
                    {errorGeneral}
                  </p>
                )}

                <div className="editar-acciones">
                  <button
                    type="button"
                    className="editar-btn editar-btn-secundario"
                    onClick={volverALista}
                    disabled={cargando}
                  >
                    Volver a la lista
                  </button>

                  <button
                    type="submit"
                    className="editar-btn editar-btn-principal"
                    disabled={cargando}
                  >
                    {cargando ? "Guardando..." : "Guardar cambios"}
                  </button>
                </div>
              </form>
            </>
          )}
        </section>
      )}
      {/* Modal para dar de alta repartidores */}
      <AltaRepartidor
        abierto={modalRepartidorAbierto}
        onCerrar={() => setModalRepartidorAbierto(false)}
        onCreado={() => {
          void cargarRepartidores();
        }}
      />
    </main>
  );
}

export default EditarRepartidor;
