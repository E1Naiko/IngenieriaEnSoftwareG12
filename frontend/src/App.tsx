
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./components/login/login";
import Dashboard from "./pages/Dashboard";
import Comercios from "./pages/Comercios";
import Flota from "./pages/Flota";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/comercios" element={<Comercios />} />
        <Route path="/flota" element={<Flota />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
