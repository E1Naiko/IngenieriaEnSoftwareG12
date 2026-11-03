
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
import "./App.css";
import ConsultarPaquete from "./pages/ConsultarEnvio";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/comercios" element={<Comercios />} />
        <Route path="/ingresar-pedido" element={<IngresarPedido />} />
        <Route path="/flota" element={<Flota />} />
        <Route path="/comercios" element={<Comercios />} /> 
        <Route path="/loginrepartidor" element={<LoginRepartidor />} />
        <Route path="/dashboardrepartidor" element={<DashboardRepartidor />} />
        <Route path="/paquetesencurso" element={<PaquetesEnCurso />} />
        <Route path="/historialenvios" element={<HistorialEnvios />} />
        <Route path="/seguimiento" element={<ConsultarPaquete />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
