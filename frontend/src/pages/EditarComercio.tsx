import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
// Reutiliza los mismos estilos que EditarRepartidor.
import "../styles/EditarRepartidor.css";
// Formulario de alta de comercio (el que antes se mostraba en el modal del Dashboard).
import GestionarComercios from "./GestionarComercios";

interface Comercio {
  id: number;
  nombre: string;
  telefono: string;
  direccion: string;
}

type Campo = "nombre" | "telefono" | "direccion";
type Valores = Record<Campo, string>;
type Errores = Partial<Record<Campo, string>>;

const MSG_OBLIGATORIO = "Campo obligatorio";
const MSG_REPETIDO = "Este dato ya existe en el sistema";
const MSG_TELEFONO = "El teléfono debe contener solamente números";

const VALORES_INICIALES: Valores = {
  nombre: "",
  telefono: "",
  direccion: "",
};

function contieneSoloNumeros(valor: string): boolean {
  return /^[0-9]+$/.test(valor);
}

function validar(valores: Valores): Errores {
  const errores: Errores = {};

  if (!valores.nombre.trim()) errores.nombre = MSG_OBLIGATORIO;
  if (!valores.telefono.trim()) errores.telefono = MSG_OBLIGATORIO;
  if (!valores.direccion.trim()) errores.direccion = MSG_OBLIGATORIO;

  if (!errores.telefono && !contieneSoloNumeros(valores.telefono.trim())) {
    errores.telefono = MSG_TELEFONO;
  }

  return errores;
}

function textoDe(valor: unknown): string {
  if (Array.isArray(valor)) return String(valor[0] ?? "");
  if (typeof valor === "string") return valor;
  return "";
}

function mensajeDeCampo(campo: Campo, texto: string): string {
  if (/exist|already|unique|duplic|repetid/i.test(texto)) return MSG_REPETIDO;
  if (/obligatorio|blank|null|required|vac[ií]o/i.test(texto)) {
    return MSG_OBLIGATORIO;
  }
  if (campo === "telefono" && /number|integer|n[uú]mero/i.test(texto)) {
    return MSG_TELEFONO;
  }
  return texto || "Dato inválido";
}

function EditarComercio() {
  const navigate = useNavigate();

  const [comercios, setComercios] = useState<Comercio[]>([]);
  const [comercio, setComercio] = useState<Comercio | null>(null);

  const [cargandoLista, setCargandoLista] = useState(true);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [cargando, setCargando] = useState(false);

  const [errorLista, setErrorLista] = useState("");
  const [errorGeneral, setErrorGeneral] = useState("");
  const [valores, setValores] = useState<Valores>(VALORES_INICIALES);
  const [errores, setErrores] = useState<Errores>({});
  const [exito, setExito] = useState(false);

  // Controla la ventana modal para dar de alta comercios.
  const [modalComercioAbierto, setModalComercioAbierto] = useState(false);

  function cerrarModalAlta() {
    setModalComercioAbierto(false);
    void cargarComercios();
  }

  // Carga la lista que se ofrece para seleccionar.
  async function cargarComercios() {
    try {
      setCargandoLista(true);
      setErrorLista("");

      const response = await fetch("/api/comercios/");

      if (!response.ok) {
        throw new Error("No se pudo cargar la lista de comercios.");
      }

      const data = await response.json();
      // Acepta [] directo o { comercios: [] } según lo que devuelva el backend.
      setComercios(
        Array.isArray(data) ? data : data.results ?? data.comercios ?? []
    );
    } catch (error) {
      setErrorLista(
        error instanceof Error
          ? error.message
          : "Error al cargar los comercios."
      );
    } finally {
      setCargandoLista(false);
    }
  }

  useEffect(() => {
    void cargarComercios();
  }, []);

  // Obtiene los datos completos del comercio seleccionado.
  async function seleccionarComercio(id: number) {
    try {
      setCargandoDetalle(true);
      setErrorLista("");

      const response = await fetch(`/api/comercios/${id}/`);

      if (!response.ok) {
        throw new Error("No se pudieron obtener los datos del comercio.");
      }

      const data = await response.json();
      const detalle = data.comercio ?? data;

      if (!detalle) {
        throw new Error("El servidor no devolvió los datos del comercio.");
      }

      setComercio({ ...detalle, id });
    } catch (error) {
      setErrorLista(
        error instanceof Error
          ? error.message
          : "Error al seleccionar el comercio."
      );
    } finally {
      setCargandoDetalle(false);
    }
  }

  // Cuando se selecciona un comercio, carga sus datos en el formulario.
  useEffect(() => {
    if (!comercio) return;

    setValores({
      nombre: comercio.nombre ?? "",
      telefono: String(comercio.telefono ?? ""),
      direccion: comercio.direccion ?? "",
    });

    setErrores({});
    setErrorGeneral("");
    setExito(false);
  }, [comercio]);

  function cambiar(campo: Campo, valor: string) {
    setValores((anterior) => ({ ...anterior, [campo]: valor }));
    setErrores((anterior) => ({ ...anterior, [campo]: undefined }));
    setErrorGeneral("");
  }

  // Envía al backend todos los campos editables mediante PUT.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!comercio) return;

    const erroresLocales = validar(valores);

    if (Object.keys(erroresLocales).length > 0) {
      setErrores(erroresLocales);
      return;
    }

    setCargando(true);
    setErrores({});
    setErrorGeneral("");

    try {
      const response = await fetch(`/api/comercios/${comercio.id}/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: valores.nombre.trim(),
          telefono: valores.telefono.trim(),
          direccion: valores.direccion.trim(),
        }),
      });

      const data = await response.json().catch(() => null);

      if (response.ok) {
        setExito(true);
        return;
      }

      if (data && typeof data === "object") {
        const datosError = data as Record<string, unknown>;
        const campos: Campo[] = ["nombre", "telefono", "direccion"];
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
    setComercio(null);
    setValores(VALORES_INICIALES);
    setErrores({});
    setErrorGeneral("");
    setExito(false);
    void cargarComercios();
  }

  return (
    <main className="editar-pagina">
      {!comercio ? (
        <section className="editar-lista">
          <div className="editar-header">
            <div>
              <h1>Gestionar Comercios</h1>

              <p className="editar-subtitulo">
                Seleccioná el comercio cuyos datos querés modificar.
              </p>
            </div>

            <button
              type="button"
              className="editar-btn editar-btn-principal"
              onClick={() => setModalComercioAbierto(true)}
            >
              🏪 Alta Comercio
            </button>
          </div>

          {cargandoLista && <p>Cargando comercios...</p>}

          {errorLista && (
            <p className="editar-error-general" role="alert">
              {errorLista}
            </p>
          )}

          {!cargandoLista && !errorLista && comercios.length === 0 && (
            <p>No hay comercios para mostrar.</p>
          )}

          {!cargandoLista &&
            comercios.map((item) => (
              <div className="editar-repartidor-item" key={item.id}>
                <div>
                  <strong>{item.nombre}</strong>
                  <p>{item.direccion}</p>
                </div>

                <button
                  type="button"
                  onClick={() => void seleccionarComercio(item.id)}
                  disabled={cargandoDetalle}
                >
                  {cargandoDetalle ? "Cargando..." : "Seleccionar"}
                </button>
              </div>
            ))}

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
              <h2>Comercio modificado con éxito</h2>
              <p>Los datos del comercio se actualizaron correctamente.</p>

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
              <h1>Editar comercio</h1>
              <p className="editar-subtitulo">
                Modificá los datos de {comercio.nombre}.
              </p>

              <form onSubmit={handleSubmit} noValidate>
                <div className="editar-campo">
                  <label htmlFor="editar-nombre">Nombre del comercio</label>
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
                  <label htmlFor="editar-telefono">Teléfono</label>
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
                  <label htmlFor="editar-direccion">Dirección</label>
                  <input
                    id="editar-direccion"
                    type="text"
                    value={valores.direccion}
                    onChange={(e) => cambiar("direccion", e.target.value)}
                    className={errores.direccion ? "editar-input-error" : ""}
                  />
                  {errores.direccion && (
                    <span className="editar-error">{errores.direccion}</span>
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

      {/* Modal "Cargar comercio": reutiliza el formulario y las clases del modal existente */}
      {modalComercioAbierto && (
        <div className="modal-overlay" onClick={cerrarModalAlta}>
          <section
            className="modal-comercios"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-comercios-titulo"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="modal-comercios-header">
              <h2 id="modal-comercios-titulo">Cargar comercio</h2>

              <button
                type="button"
                className="modal-comercios-cerrar"
                aria-label="Cerrar ventana"
                onClick={cerrarModalAlta}
              >
                ✕
              </button>
            </header>

            <div className="modal-comercios-body">
              <GestionarComercios onChange={() => void cargarComercios()} />
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

export default EditarComercio;