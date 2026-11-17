
import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import "../styles/PedidosPorReasignar.css";

interface Pedido {
  id: number;
  destinatario: string;
  direccion: string;
  tamanio: string;
  estado: string;
}

const API_URL = "/api/pedidos-por-reasignar/";

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

  const obtenerPedidos = async () => {
    try {
      setCargando(true);
      setError("");

      const respuesta = await fetch(API_URL);

      if (!respuesta.ok) {
        throw new Error("No se pudieron obtener los pedidos.");
      }

      const datos = await respuesta.json();
      setPedidos(datos);

    } catch (err) {
      console.error(err);
      setError("No fue posible cargar los pedidos.");
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    obtenerPedidos();
  }, []);

  // Aceptar un pedido
  const aceptarPedido = async () => {
    if (!pedidoSeleccionado) return;

    try {
      setProcesando(true);
      setError("");

      /*
       * Endpoint provisional.
       * Debe coincidir con el endpoint que implemente Django.
       */
      const respuesta = await fetch(
        `${API_URL}aceptar/${pedidoSeleccionado.id}/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          // Si Django necesita identificar al repartidor,
          // habrá que enviar también su identificación.
        }
      );

      if (!respuesta.ok) {
        throw new Error("No se pudo aceptar el pedido.");
      }

      setPedidoSeleccionado(null);

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

        {cargando ? (
          <p className="reasignar-mensaje">
            Cargando pedidos...
          </p>
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

                  <span className="pedido-reasignar-estado">
                    {pedido.estado}
                  </span>
                </div>

                <div className="pedido-reasignar-info">
                  <p>
                    <strong>Destinatario</strong>
                    <span>{pedido.destinatario}</span>
                  </p>

                  <p>
                    <strong>Dirección</strong>
                    <span>{pedido.direccion}</span>
                  </p>

                  <p>
                    <strong>Tamaño</strong>
                    <span>{pedido.tamanio}</span>
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

            <p>
              Pedido #{pedidoSeleccionado.id}
            </p>

            <div className="reasignar-modal-info">
              <span>
                <strong>Destinatario:</strong>{" "}
                {pedidoSeleccionado.destinatario}
              </span>

              <span>
                <strong>Dirección:</strong>{" "}
                {pedidoSeleccionado.direccion}
              </span>

              <span>
                <strong>Tamaño:</strong>{" "}
                {pedidoSeleccionado.tamanio}
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
