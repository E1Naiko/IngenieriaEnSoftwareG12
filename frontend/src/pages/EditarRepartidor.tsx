import { useEffect, useState, type FormEvent } from "react";
import "../styles/EditarRepartidor.css";

// Datos del repartidor que recibimos desde el componente padre.
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

// Campos que se pueden editar en el formulario.
type Campo =
  | "dni"
  | "nombre"
  | "apellido"
  | "telefono"
  | "mail"
  | "tipo_vehiculo";

// Todos los valores del formulario se manejan como texto.
type Valores = Record<Campo, string>;

// Estructura para guardar un mensaje de error por campo.
type Errores = Partial<Record<Campo, string>>;

// Mensajes que se muestran en la interfaz.
const MSG_OBLIGATORIO = "Campo obligatorio";
const MSG_REPETIDO = "Este dato ya existe en el sistema";
const MSG_DNI = "El DNI debe contener solamente números";
const MSG_TELEFONO = "El celular debe contener solamente números";
const MSG_MAIL = "Ingresá un email válido";
const MSG_VEHICULO = "Seleccioná un tipo de vehículo";

// Opciones permitidas para el tipo de vehículo.
const TIPOS_VEHICULO = [
  { value: "moto", label: "Moto" },
  { value: "auto", label: "Auto" },
  { value: "camioneta", label: "Camioneta" },
  { value: "camion", label: "Camión" },
];

// Propiedades que recibe el componente desde su componente padre.
/*interface Props {
  abierto: boolean;
  repartidor: Repartidor | null;
  onCerrar: () => void;
  onActualizado?: () => void;
} */

// Comprueba que el valor esté formado solamente por números.
function contieneSoloNumeros(valor: string): boolean {
  return /^[0-9]+$/.test(valor);
}

// Valida todos los campos antes de enviar los cambios.
function validar(valores: Valores): Errores {
  const errores: Errores = {};

  // Comprueba que ningún campo esté vacío.
  if (!valores.dni.trim()) {
    errores.dni = MSG_OBLIGATORIO;
  }

  if (!valores.nombre.trim()) {
    errores.nombre = MSG_OBLIGATORIO;
  }

  if (!valores.apellido.trim()) {
    errores.apellido = MSG_OBLIGATORIO;
  }

  if (!valores.telefono.trim()) {
    errores.telefono = MSG_OBLIGATORIO;
  }

  if (!valores.mail.trim()) {
    errores.mail = MSG_OBLIGATORIO;
  }

  if (!valores.tipo_vehiculo.trim()) {
    errores.tipo_vehiculo = MSG_OBLIGATORIO;
  }

  // Comprueba que el DNI tenga solamente números.
  if (!errores.dni && !contieneSoloNumeros(valores.dni.trim())) {
    errores.dni = MSG_DNI;
  }

  // Comprueba que el celular tenga solamente números.
  if (
    !errores.telefono &&
    !contieneSoloNumeros(valores.telefono.trim())
  ) {
    errores.telefono = MSG_TELEFONO;
  }

  // Comprueba que el email tenga un formato básico válido.
  if (
    !errores.mail &&
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valores.mail.trim())
  ) {
    errores.mail = MSG_MAIL;
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

// Convierte el valor de un error del backend en un texto.
function textoDe(valor: unknown): string {
  if (Array.isArray(valor)) {
    return String(valor[0] ?? "");
  }

  if (typeof valor === "string") {
    return valor;
  }

  return "";
}

// Convierte los errores del backend en mensajes para la interfaz.
function mensajeDeCampo(campo: Campo, texto: string): string {
  // El backend puede informar que un dato ya está registrado.
  if (/exist|already|unique|duplic|repetid/i.test(texto)) {
    return MSG_REPETIDO;
  }

  // Comprueba si el backend informa que falta completar el campo.
  if (/obligatorio|blank|null|required|vac[ií]o/i.test(texto)) {
    return MSG_OBLIGATORIO;
  }

  // Mensajes específicos para cada campo.
  if (campo === "dni" && /number|integer|n[uú]mero/i.test(texto)) {
    return MSG_DNI;
  }

  if (campo === "telefono" && /number|integer|n[uú]mero/i.test(texto)) {
    return MSG_TELEFONO;
  }

  if (campo === "mail" && /email|correo|valid/i.test(texto)) {
    return MSG_MAIL;
  }

  if (campo === "tipo_vehiculo") {
    return MSG_VEHICULO;
  }

  return texto || "Dato inválido";
}

// Componente para editar los datos de un repartidor.
/*function EditarRepartidor({
  abierto,
  repartidor,
  onCerrar,
  onActualizado,
}: Props) {   */
function EditarRepartidor() {
  // Lista de repartidores que se mostrarán para seleccionar.
  const [repartidores, setRepartidores] = useState<Repartidor[]>([]);

  // Repartidor seleccionado para editar.
  const [repartidor, setRepartidor] = useState<Repartidor | null>(null);

  // Indica si se está cargando la lista.
  const [cargandoLista, setCargandoLista] = useState(true);

  // Error al intentar cargar la lista.
  const [errorLista, setErrorLista] = useState("");

  // Estado que guarda los valores escritos en el formulario.
  const [valores, setValores] = useState<Valores>({
    dni: "",
    nombre: "",
    apellido: "",
    telefono: "",
    mail: "",
    tipo_vehiculo: "",
  });

  // Estado que guarda los errores de cada campo.
  const [errores, setErrores] = useState<Errores>({});

  // Mensaje para errores que no pertenecen a un campo específico.
  const [errorGeneral, setErrorGeneral] = useState("");

  // Indica si se está enviando la modificación.
  const [cargando, setCargando] = useState(false);

  // Indica si la modificación se realizó correctamente.
  const [exito, setExito] = useState(false);

  useEffect(() => {
  async function cargarRepartidores() {
    try {
      setCargandoLista(true);
      setErrorLista("");

      const response = await fetch(
        "/api/dashboard/repartidores-disponibles/"
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

    cargarRepartidores();
  }, []);

  async function seleccionarRepartidor(id: number) {
  try {
    setErrorGeneral("");

    const response = await fetch(`/api/repartidores/${id}/`);

    if (!response.ok) {
      throw new Error("No se pudieron obtener los datos del repartidor.");
    }

    const data = await response.json();

    // El backend devuelve los datos dentro de la propiedad repartidor.
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
  }
}

  // Cuando se abre el formulario, carga los datos actuales del repartidor.
  useEffect(() => {
  if (repartidor) {
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
  }
}, [repartidor]);

  // Si el formulario está cerrado o no hay repartidor seleccionado, no se muestra.
  /*if (!abierto || !repartidor) {
    return null;
  } */

  // Actualiza el valor de un campo y elimina su error anterior.
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

  // Envía los datos modificados al backend.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    // Primero se validan los datos en el frontend.
    const erroresLocales = validar(valores);

    // Si hay errores, se muestran y no se envía la petición.
    if (Object.keys(erroresLocales).length > 0) {
      setErrores(erroresLocales);
      return;
    }

    setCargando(true);
    setErrores({});
    setErrorGeneral("");
    
    try {
      // Se envían todos los campos al endpoint del repartidor seleccionado.
      // Se utiliza PUT porque se envía el conjunto completo de datos editables.

      if (!repartidor) {
        return;
      }
      const response = await fetch(
        `/api/repartidores/${repartidor.id}/`,
        {
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
        }
      );

      // Convierte la respuesta del backend a JSON.
      const data = await response.json().catch(() => null);

      // Si el backend respondió correctamente, muestra el mensaje de éxito.
      if (response.ok) {
        setExito(true);
        return;
      }

      // Si el backend devolvió errores por campo, los muestra en el formulario.
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

      // Si no se identifica un error de campo, muestra un mensaje general.
      setErrorGeneral(
        textoDe(
          data && typeof data === "object"
            ? (data as Record<string, unknown>).message
            : null
        ) || "No se pudieron modificar los datos. Intentá nuevamente."
      );
    } catch {
      // Se ejecuta si no se puede establecer conexión con el backend.
      setErrorGeneral("No se pudo conectar con el servidor.");
    } finally {
      // Finaliza el estado de carga.
      setCargando(false);
    }
  }

  // Renderiza la pantalla de edición o el mensaje de éxito.
  return (
  <main className="editar-pagina">

    {!repartidor ? (
      <section className="editar-lista">

        <h2>Seleccionar repartidor</h2>

        <p>Elegí el repartidor cuyos datos querés modificar.</p>

        {cargandoLista && <p>Cargando repartidores...</p>}

        {errorLista && (
          <p className="editar-error-general">{errorLista}</p>
        )}

        {!cargandoLista && repartidores.map((item) => (
          <div className="editar-repartidor-item" key={item.id}>
            <div>
              <strong>
                {item.nombre} {item.apellido}
              </strong>
              <p>DNI: {item.dni}</p>
            </div>

            <button
              type="button"
              onClick={() => seleccionarRepartidor(item.id)}
            >
              Seleccionar
            </button>
          </div>
        ))}

        <button
          type="button"
          onClick={() => window.history.back()}
        >
          Volver
        </button>

      </section>
    ) : (
          
          // Formulario con los datos actuales del repartidor.
          <form onSubmit={handleSubmit} noValidate>
            <h2 id="editar-titulo">Editar repartidor</h2>
            <p className="editar-subtitulo">
              Modificá los datos del repartidor seleccionado.
            </p>

            {/* Campo DNI. */}
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

            {/* Campo nombre. */}
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

            {/* Campo apellido. */}
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

            {/* Token: solamente se muestra, no se puede modificar. 
            readOnly: Esto permite visualizar y seleccionar el token,
            pero impide que el usuario lo cambie desde el formulario.*/}
            <div className="editar-campo">
              <label htmlFor="editar-token">Token</label>
              <input
                id="editar-token"
                type="text"
                value={repartidor.token}
                readOnly
                className="editar-input-solo-lectura"
              />
            </div>

            {/* Campo celular. */}
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

            {/* Campo email. */}
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

            {/* Selector del tipo de vehículo. */}
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

            {/* Mensaje para errores generales. */}
            {errorGeneral && (
              <p className="editar-error-general" role="alert">
                {errorGeneral}
              </p>
            )}

            {/* Botones para cancelar o guardar los cambios. */}
            <div className="editar-acciones">
              <button
                type="button"
                className="editar-btn editar-btn-secundario"
                onClick={onCerrar}
                disabled={cargando}
              >
                Cancelar
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
        )}
      </div>
    </div>
  );
}

export default EditarRepartidor;
