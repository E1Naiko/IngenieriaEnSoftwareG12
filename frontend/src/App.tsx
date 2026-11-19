import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./components/login/login";
import Dashboard from "./pages/Dashboard";
import Comercios from "./pages/Comercios";
import IngresarPedido from "./pages/IngresarPedido";
import Flota from "./pages/Flota";
import LoginRepartidor from "./components/loginRepartidor/LoginRepartidor";
import DashboardRepartidor from "./pages/Dashboardrepartidor";
import PaquetesEnCurso from "./pages/PaquetesEnCurso";
import HistorialEnvios from "./pages/HistorialEnvios";
import ConsultarPaquete from "./pages/ConsultarEnvio";
import PedidosPorReasignar from "./pages/PedidosPorReasignar";

import EditarRepartidor from "./pages/EditarRepartidor";
import EditarComercio from "./pages/EditarComercio";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/ingresar-pedido" element={<IngresarPedido />} />
        <Route path="/flota" element={<Flota />} />
        <Route path="/listado-comercios" element={<Comercios />} />
        <Route path="/loginrepartidor" element={<LoginRepartidor />} />
        <Route path="/dashboardrepartidor" element={<DashboardRepartidor />} />
        <Route path="/paquetesencurso" element={<PaquetesEnCurso />} />
        <Route path="/historialenvios" element={<HistorialEnvios />} />
        <Route path="/seguimiento" element={<ConsultarPaquete />} />
        <Route path="/dashboardrepartidor/reasignar" element={<PedidosPorReasignar />} />
        <Route path="/repartidores" element={<EditarRepartidor />} />
        <Route path="/comercios" element={<EditarComercio />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;