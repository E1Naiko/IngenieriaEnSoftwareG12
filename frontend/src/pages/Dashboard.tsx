import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import "../styles/Dashboard.css";

import Flota from "./Flota";
import PaquetesEnCurso from "./PaquetesEnCurso";
import Comercios from "./Comercios";

function Dashboard() {
  const navigate = useNavigate();
  const guardado = localStorage.getItem("coordinador");

  // Controla la visibilidad del panel lateral.
  const [sidebarAbierto, setSidebarAbierto] = useState(true);

  // Controla los menús desplegables de cada sección.
  const [flotaAbierta, setFlotaAbierta] = useState(true);
  const [paquetesAbiertos, setPaquetesAbiertos] = useState(true);
  const [comerciosAbiertos, setComerciosAbiertos] = useState(true);

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
    setSidebarAbierto(!sidebarAbierto);
  }

  return (
    <div
      className={`dashboard-layout ${
        sidebarAbierto ? "" : "sidebar-cerrado"
      }`}
    >
      {/* Panel lateral */}
      <aside className="dashboard-sidebar">
        <h2 className="sidebar-logo">
          {sidebarAbierto ? "Panel de Gestión" : "PG"}
        </h2>

        <nav className="sidebar-navigation">
          <Link
            to="/dashboard"
            className="sidebar-link"
            title="Dashboard"
          >
            <span className="sidebar-icon">🏠</span>
            {sidebarAbierto && <span>Dashboard</span>}
          </Link>

          <Link
            to="/comercios"
            className="sidebar-link"
            title="Gestionar comercios"
          >
            <span className="sidebar-icon">🏪</span>
            {sidebarAbierto && <span>Gestionar comercios</span>}
          </Link>

          <Link
            to="/flota"
            className="sidebar-link"
            title="Flota disponible"
          >
            <span className="sidebar-icon">🚚</span>
            {sidebarAbierto && <span>Flota disponible</span>}
          </Link>

          <Link
            to="/paquetesencurso"
            className="sidebar-link"
            title="Paquetes en curso"
          >
            <span className="sidebar-icon">📦</span>
            {sidebarAbierto && <span>Paquetes en curso</span>}
          </Link>
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
        </nav>
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
                  Consulta y gestión de comercios
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
              <Comercios />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default Dashboard;