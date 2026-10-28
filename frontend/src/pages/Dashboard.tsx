import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import "../styles/Dashboard.css";
import Flota from "./Flota";
import PaquetesEnCurso from "./PaquetesEnCurso";
import Comercios from "./Comercios";
import GestionarComercios from "./GestionarComercios";
import IngresarPedido from "./IngresarPedido";

function Dashboard() {
  const navigate = useNavigate();
  const guardado = localStorage.getItem("coordinador");

  // Controla la visibilidad del panel lateral.
  const [sidebarAbierto, setSidebarAbierto] = useState(true);

  // Referencia al panel lateral para detectar clics externos.
  const sidebarRef = useRef<HTMLElement>(null);

  // Controla los menús desplegables.
  const [flotaAbierta, setFlotaAbierta] = useState(true);
  const [paquetesAbiertos, setPaquetesAbiertos] = useState(true);
  const [comerciosAbiertos, setComerciosAbiertos] = useState(true);

  // Controla la ventana modal de gestión de comercios.
  const [modalComerciosAbierto, setModalComerciosAbierto] = useState(false);
  // Controla la ventana modal para ingresar pedidos.
  const [modalPedidoAbierto, setModalPedidoAbierto] = useState(false);

  // Permite actualizar el listado después de modificar comercios.
  const [refreshComercios, setRefreshComercios] = useState(0);

  // Contrae el sidebar al hacer clic fuera de él.
  useEffect(() => {
    function manejarClickExterno(event: MouseEvent) {
      if (
        sidebarRef.current &&
        !sidebarRef.current.contains(event.target as Node)
      ) {
        setSidebarAbierto(false);
      }
    }

    document.addEventListener("mousedown", manejarClickExterno);

    return () => {
      document.removeEventListener("mousedown", manejarClickExterno);
    };
  }, []);

  // Si no hay sesión iniciada, vuelve al login.
  if (!guardado) {
    return <Navigate to="/" replace />;
  }

  const coordinador = JSON.parse(guardado);

  // Cierra la sesión y vuelve al login.
  function cerrarSesion() {
    localStorage.removeItem("coordinador");
    navigate("/");
  }

  // Muestra u oculta el panel lateral.
  function alternarSidebar() {
    setSidebarAbierto((abierto) => !abierto);
  }

  // Actualiza el listado después de una operación exitosa.
  function actualizarComercios() {
    setRefreshComercios((actual) => actual + 1);
  }

  return (
    <div
      className={`dashboard-layout ${
        sidebarAbierto ? "" : "sidebar-cerrado"
      }`}
    >
      {/* Panel lateral */}
      <aside
        ref={sidebarRef}
        className="dashboard-sidebar"
        onClick={() => {
          if (!sidebarAbierto) {
            setSidebarAbierto(true);
          }
        }}
      >
        <h2 className="sidebar-logo">
          {sidebarAbierto ? "🏠Panel de Gestión" : "PG"}
        </h2>

        <nav className="sidebar-navigation">
          {/* Abre el modal para cargar un comercio. */}
          <button
            type="button"
            className="sidebar-link"
            title="Cargar comercio"
            onClick={() => setModalComerciosAbierto(true)}
          >
            <span className="sidebar-icon">🏪</span>
            {sidebarAbierto && <span>Cargar comercio</span>}
          </button>

          <Link
            to="/alta-repartidor"
            className="sidebar-link"
            title="Alta Repartidor"
          >
            <span className="sidebar-icon">🚚</span>
            {sidebarAbierto && <span>Alta Repartidor</span>}
          </Link>

          {/* Abre el modal para ingresar un pedido. */}
          <button
            type="button"
            className="sidebar-link"
            title="Ingresar pedido"
            onClick={() => setModalPedidoAbierto(true)}
          >
            <span className="sidebar-icon">📦</span>
            {sidebarAbierto && <span>Ingresar Pedido</span>}
          </button>
          
          <Link
            to="/asignar-pedido"
            className="sidebar-link"
            title="Asignar Pedido"
          >
            <span className="sidebar-icon">📦</span>
            {sidebarAbierto && <span>Asignar Pedido</span>}
          </Link>

          <Link
            to="/historial"
            className="sidebar-link"
            title="Historial de Pedidos"
          >
            <span className="sidebar-icon">📋</span>
            {sidebarAbierto && <span>Historial de Pedidos</span>}
          </Link>
        </nav>

        {/* Botón para cerrar sesión */}
        <button
          type="button"
          className="sidebar-logout"
          onClick={cerrarSesion}
          title="Cerrar sesión"
        >
          <span className="sidebar-icon">🚪</span>
          {sidebarAbierto && <span>Cerrar sesión</span>}
        </button>
      </aside>

      {/* Contenido principal */}
      <main className="dashboard-content">
        <header className="dashboard-header">
          <button
            type="button"
            className="sidebar-toggle"
            onClick={alternarSidebar}
            aria-label={
              sidebarAbierto
                ? "Ocultar menú lateral"
                : "Mostrar menú lateral"
            }
            aria-expanded={sidebarAbierto}
          >
            {sidebarAbierto ? "◀" : "☰"}
          </button>

          <h1>Bienvenido, {coordinador.username}</h1>
        </header>

        {/* Sección desplegable: Flota */}
        <section
          className={`dashboard-section ${
            flotaAbierta ? "section-open" : ""
          }`}
        >
          <button
            type="button"
            className="dashboard-section-toggle"
            onClick={() => setFlotaAbierta(!flotaAbierta)}
            aria-expanded={flotaAbierta}
          >
            <span className="section-heading">
              <span className="section-icon flota-icon">🚚</span>

              <span className="section-title-group">
                <span className="section-title">
                  Flota disponible
                </span>
                <span className="section-subtitle">
                  Consulta y gestión de repartidores
                </span>
              </span>
            </span>

            <span className="section-action">
              <span className="section-action-text">
                {flotaAbierta ? "Ocultar" : "Ver información"}
              </span>
              <span className="accordion-arrow">
                {flotaAbierta ? "⌃" : "⌄"}
              </span>
            </span>
          </button>

          {flotaAbierta && (
            <div className="dashboard-section-content">
              <Flota />
            </div>
          )}
        </section>

        {/* Sección desplegable: Paquetes en curso */}
        <section
          className={`dashboard-section ${
            paquetesAbiertos ? "section-open" : ""
          }`}
        >
          <button
            type="button"
            className="dashboard-section-toggle"
            onClick={() => setPaquetesAbiertos(!paquetesAbiertos)}
            aria-expanded={paquetesAbiertos}
          >
            <span className="section-heading">
              <span className="section-icon paquetes-icon">📦</span>

              <span className="section-title-group">
                <span className="section-title">
                  Paquetes en curso
                </span>
                <span className="section-subtitle">
                  Consulta el estado de los envíos
                </span>
              </span>
            </span>

            <span className="section-action">
              <span className="section-action-text">
                {paquetesAbiertos ? "Ocultar" : "Ver información"}
              </span>
              <span className="accordion-arrow">
                {paquetesAbiertos ? "⌃" : "⌄"}
              </span>
            </span>
          </button>

          {paquetesAbiertos && (
            <div className="dashboard-section-content">
              <PaquetesEnCurso />
            </div>
          )}
        </section>

        {/* Sección desplegable: Comercios */}
        <section
          className={`dashboard-section ${
            comerciosAbiertos ? "section-open" : ""
          }`}
        >
          <button
            type="button"
            className="dashboard-section-toggle"
            onClick={() => setComerciosAbiertos(!comerciosAbiertos)}
            aria-expanded={comerciosAbiertos}
          >
            <span className="section-heading">
              <span className="section-icon comercios-icon">🏪</span>

              <span className="section-title-group">
                <span className="section-title">Comercios</span>
                <span className="section-subtitle">
                  Consulta los comercios registrados
                </span>
              </span>
            </span>

            <span className="section-action">
              <span className="section-action-text">
                {comerciosAbiertos ? "Ocultar" : "Ver información"}
              </span>
              <span className="accordion-arrow">
                {comerciosAbiertos ? "⌃" : "⌄"}
              </span>
            </span>
          </button>

          {comerciosAbiertos && (
            <div className="dashboard-section-content">
              <Comercios refreshKey={refreshComercios} />
            </div>
          )}
        </section>
      </main>

      {/* Ventana modal para cargar comercios */}
      {modalComerciosAbierto && (
        <div
          className="modal-overlay"
          onClick={() => setModalComerciosAbierto(false)}
        >
          <section
            className="modal-comercios"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-comercios-titulo"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="modal-comercios-header">
              <h2 id="modal-comercios-titulo">
                Cargar comercio
              </h2>

              <button
                type="button"
                className="modal-comercios-cerrar"
                aria-label="Cerrar ventana"
                onClick={() => setModalComerciosAbierto(false)}
              >
                ✕
              </button>
            </header>

            <div className="modal-comercios-body">
              <GestionarComercios
                onChange={actualizarComercios}
              />
            </div>
          </section>
        </div>
      )}

      {/* Ventana modal para ingresar pedidos */}
      {modalPedidoAbierto && (
        <div
          className="modal-overlay"
          onClick={() => setModalPedidoAbierto(false)}
        >
          <section
            className="modal-pedido"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-pedido-titulo"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="modal-pedido-header">
              <h2 id="modal-pedido-titulo">
                Ingresar Pedido
              </h2>

              <button
                type="button"
                className="modal-pedido-cerrar"
                aria-label="Cerrar ventana"
                onClick={() => setModalPedidoAbierto(false)}
              >
                ✕
              </button>
            </header>

            <div className="modal-pedido-body">
              <IngresarPedido />
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
