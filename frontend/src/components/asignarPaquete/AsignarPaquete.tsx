import { useEffect, useState } from "react";
import "./AsignarPaquete.css";

interface Paquete {
  id: number;
  destinatario: string;
  direccion: string;
  repartidor: string | null;
  estado: string;
}

interface AsignarPaqueteProps {
  repartidor: {
    id: number;
    nombre: string;
    apellido: string;
  };
  onClose: () => void;
}

function AsignarPaquete({
  repartidor,
  onClose,
}: AsignarPaqueteProps) {
  const [paquetes, setPaquetes] = useState<Paquete[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelado = false;

    async function cargarPaquetes() {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(
          "/api/dashboard/paquetes-en-curso/"
        );

        if (!res.ok) {
          throw new Error("No se pudieron cargar los pedidos.");
        }

        const data = await res.json();

        // Conserva únicamente los paquetes sin repartidor asignado.
        const lista: Paquete[] = data.paquetes ?? [];

        const sinAsignar = lista.filter((paquete) => {
          const repartidorAsignado = paquete.repartidor;

          return (
            repartidorAsignado == null ||
            String(repartidorAsignado).trim() === "" ||
            String(repartidorAsignado).trim().toLowerCase() ===
              "sin asignar"
          );
        });

        if (!cancelado) {
          setPaquetes(sinAsignar);
        }
      } catch (e) {
        if (!cancelado) {
          setError(
            e instanceof Error
              ? e.message
              : "Error al cargar los pedidos."
          );
        }
      } finally {
        if (!cancelado) {
          setLoading(false);
        }
      }
    }

    cargarPaquetes();

    return () => {
      cancelado = true;
    };
  }, []);

  return (
    <div
      className="asignar-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="asignar-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="asignar-titulo"
      >
        <header className="asignar-header">
          <div>
            <h2 id="asignar-titulo">
              Pedidos sin asignar
            </h2>

            <p>
              Repartidor:{" "}
              <strong>
                {repartidor.nombre} {repartidor.apellido}
              </strong>
            </p>
          </div>

          <button
            type="button"
            className="asignar-cerrar"
            onClick={onClose}
            aria-label="Cerrar modal"
          >
            ×
          </button>
        </header>

        <div className="asignar-contenido">
          {loading && (
            <p className="asignar-mensaje" role="status">
              Cargando pedidos...
            </p>
          )}

          {!loading && error && (
            <p className="asignar-error" role="alert">
              {error}
            </p>
          )}

          {!loading && !error && paquetes.length === 0 && (
            <p className="asignar-mensaje">
              No hay pedidos sin asignar.
            </p>
          )}

          {!loading && !error && paquetes.length > 0 && (
            <ul className="asignar-lista">
              {paquetes.map((paquete) => (
                <li
                  key={paquete.id}
                  className="asignar-item"
                >
                  <div className="asignar-item-info">
                    <strong>
                      Pedido #{paquete.id}
                    </strong>

                    <span>
                      Destinatario: {paquete.destinatario}
                    </span>

                    <span>
                      Dirección: {paquete.direccion}
                    </span>
                  </div>

                  <span className="asignar-estado">
                    Sin asignar
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <footer className="asignar-footer">
          <span>
            {paquetes.length} pedido
            {paquetes.length !== 1 ? "s" : ""}
          </span>

          <button
            type="button"
            className="asignar-boton-cancelar"
            onClick={onClose}
          >
            Cerrar
          </button>
        </footer>
      </section>
    </div>
  );
}

export default AsignarPaquete;