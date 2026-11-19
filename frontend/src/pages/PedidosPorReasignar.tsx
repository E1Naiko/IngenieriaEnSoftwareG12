import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import "../styles/PedidosPorReasignar.css";

interface Persona {
  nombre: string;
  apellido: string;
}

interface Pedido {
  id: number;
  direccion_retiro: string;
  direccion_destino: string;
  tamanio: string;
  // Última persona que tuvo/retiró el paquete (paquete.repartidor).
  ultimo_repartidor: Persona | null;
}

const API_URL = "/api/pedidos-por-reasignar/";

function nombreCompleto(persona: Persona | null): string {
  return persona ? `${persona.nombre} ${persona.apellido}`.trim() : "Sin repartidor previo";
}

function PedidosPorReasignar() {
  const navigate = useNavigate();
  const guardado = localStorage.getItem("repartidor");
  const repartidor = guardado ? JSON.parse(guardado) : null;

  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [pedidoSeleccionado, setPedidoSeleccionado] =
    useState<Pedido | null>(null);
  const [cargando, setCargando] = useState(true);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");

  function cerrarSesion() {
    localStorage.removeItem("repartidor");
    navigate("/loginrepartidor", { replace: true });
  }

  const obtenerPedidos = async () => {
    if (!repartidor) return;

    try {
      setCargando(true);
      setError("");

      // El backend no guarda sesión: el token viaja en cada pedido.
      const respuesta = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: repartidor.token }),
      });

      // Token inválido o repartidor que ya no está operativo.
      if (respuesta.status === 404 || respuesta.status === 403) {
        cerrarSesion();
        return;
      }

      if (!respuesta.ok) {
        throw new Error("No se pudieron obtener los pedidos.");
      }

      const datos = await respuesta.json();
      // Escenario 2: el backend responde {"pedidos": [], "mensaje": "..."}.
      setPedidos(datos.pedidos ?? []);
    } catch (err) {
      console.error(err);
      setError("No fue posible cargar los pedidos.");
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    obtenerPedidos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Aceptar un pedido: el primero en hacerlo se lo queda.
  const aceptarPedido = async () => {
    if (!pedidoSeleccionado) return;

    try {
      setProcesando(true);
      setError("");
      setExito("");

      const respuesta = await fetch(
        `${API_URL}aceptar/${pedidoSeleccionado.id}/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: repartidor?.token }),
        }
      );

      const datos = await respuesta.json().catch(() => null);

      if (respuesta.status === 404 || respuesta.status === 403) {
        cerrarSesion();
        return;
      }

      // 409: otro repartidor lo tomó primero. Se refresca la lista para que
      // el pedido desaparezca y se avisa en pantalla.
      if (respuesta.status === 409) {
        setPedidoSeleccionado(null);
        await obtenerPedidos();
        setError(datos?.message ?? "Otro repartidor tomó este pedido.");
        return;
      }

      if (!respuesta.ok) {
        throw new Error("No se pudo aceptar el pedido.");
      }

      setPedidoSeleccionado(null);
      setExito("Pedido aceptado. Ya figura en Mis pedidos.");
      await obtenerPedidos();
    } catch (err) {
      console.error(err);
      setError("No se pudo aceptar el pedido. Intenta nuevamente.");
    } finally {
      setProcesando(false);
    }
  };

  // Si no hay sesión iniciada, vuelve al login
  if (!repartidor) return <Navigate to="/loginrepartidor" replace />;

  return (
    <main className="reasignar-container">
      <header className="reasignar-header">
        <button
          type="button"
          className="repartidor-secundario"
          onClick={() => navigate("/dashboardrepartidor")}
        >
          ← Pedidos asignados
        </button>

        <h1>Pedidos por reasignar</h1>
        <p>Seleccioná un pedido para decidir si querés aceptarlo.</p>
      </header>

      <section className="reasignar-listado">
        <div className="reasignar-listado-header">
          <h2>Listado de pedidos</h2>

          <button
            type="button"
            className="reasignar-actualizar"
            onClick={obtenerPedidos}
            disabled={cargando}
          >
            Actualizar
          </button>
        </div>

        {exito && <p className="reasignar-mensaje">{exito}</p>}

        {cargando ? (
          <p className="reasignar-mensaje">Cargando pedidos...</p>
        ) : error && pedidos.length === 0 ? (
          <p className="reasignar-error">{error}</p>
        ) : pedidos.length === 0 ? (
          <p className="reasignar-mensaje">
            No hay pedidos pendientes de reasignación.
          </p>
        ) : (
          <div className="reasignar-tarjetas">
            {pedidos.map((pedido) => (
              <button
                type="button"
                key={pedido.id}
                className="pedido-reasignar-card"
                onClick={() => setPedidoSeleccionado(pedido)}
              >
                <div className="pedido-reasignar-top">
                  <span className="pedido-reasignar-id">
                    Pedido #{pedido.id}
                  </span>
                </div>

                <div className="pedido-reasignar-info">
                  <p>
                    <strong>Dirección de retiro</strong>
                    <span>{pedido.direccion_retiro}</span>
                  </p>

                  <p>
                    <strong>Dirección de destino</strong>
                    <span>{pedido.direccion_destino}</span>
                  </p>

                  <p>
                    <strong>Tamaño</strong>
                    <span>{pedido.tamanio}</span>
                  </p>

                  <p>
                    <strong>Última persona que lo retiró</strong>
                    <span>{nombreCompleto(pedido.ultimo_repartidor)}</span>
                  </p>
                </div>

                <span className="pedido-reasignar-indicacion">
                  Tocar para ver opciones →
                </span>
              </button>
            ))}
          </div>
        )}

        {error && pedidos.length > 0 && (
          <p className="reasignar-error">{error}</p>
        )}
      </section>

      {/* Ventana de confirmación */}
      {pedidoSeleccionado && (
        <div
          className="reasignar-modal-overlay"
          onClick={() => {
            if (!procesando) setPedidoSeleccionado(null);
          }}
        >
          <div
            className="reasignar-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <h2>¿Aceptar este pedido?</h2>

            <p>Pedido #{pedidoSeleccionado.id}</p>

            <div className="reasignar-modal-info">
              <span>
                <strong>Retiro:</strong> {pedidoSeleccionado.direccion_retiro}
              </span>

              <span>
                <strong>Destino:</strong> {pedidoSeleccionado.direccion_destino}
              </span>

              <span>
                <strong>Tamaño:</strong> {pedidoSeleccionado.tamanio}
              </span>

              <span>
                <strong>Última persona que lo retiró:</strong>{" "}
                {nombreCompleto(pedidoSeleccionado.ultimo_repartidor)}
              </span>
            </div>

            <p className="reasignar-modal-aviso">
              Si aceptás, el pedido quedará bajo tu responsabilidad.
            </p>

            <div className="reasignar-modal-botones">
              <button
                type="button"
                className="reasignar-btn-rechazar"
                onClick={() => setPedidoSeleccionado(null)}
                disabled={procesando}
              >
                No aceptar
              </button>

              <button
                type="button"
                className="reasignar-btn-aceptar"
                onClick={aceptarPedido}
                disabled={procesando}
              >
                {procesando ? "Procesando..." : "Aceptar pedido"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default PedidosPorReasignar;
