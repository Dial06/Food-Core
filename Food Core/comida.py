# comida.py
import sqlite3
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Sistema POS | Control de Caja",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_NAME = "comida_caja.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registro_pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            monto_pedido INTEGER,
            monto_cobrado INTEGER,
            cambio_entregado INTEGER,
            dinero_tomado INTEGER,
            metodo_pago TEXT DEFAULT 'Efectivo'
        )
    """)
    conn.commit()
    conn.close()


def registrar_pedido(
    monto_pedido, monto_cobrado, cambio_entregado, dinero_tomado, metodo_pago
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO registro_pedidos (monto_pedido, monto_cobrado, cambio_entregado, dinero_tomado, metodo_pago)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            monto_pedido,
            monto_cobrado,
            cambio_entregado,
            dinero_tomado,
            metodo_pago,
        ),
    )
    conn.commit()
    conn.close()


def cargar_datos():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT id, fecha, monto_pedido, monto_cobrado, cambio_entregado, dinero_tomado, metodo_pago FROM registro_pedidos ORDER BY id DESC",
        conn,
    )
    conn.close()
    return df


def borrar_ultimo_registro():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM registro_pedidos WHERE id = (SELECT MAX(id) FROM registro_pedidos)"
    )
    conn.commit()
    conn.close()


def vaciar_base_de_datos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registro_pedidos")
    conn.commit()
    conn.close()


def redondear_a_cinco(valor):
    if valor <= 0:
        return 0
    return int(5 * round(valor / 5))


# --- ESTILOS CSS ---
st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 18px 20px;
        border-radius: 12px;
    }
    .app-header {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

init_db()

st.markdown(
    """
    <div class="app-header">
        <h2 style="color:white; margin:0;">⚡ POS & Control de Operaciones</h2>
    </div>
""",
    unsafe_allow_html=True,
)

# --- SIDEBAR ---
st.sidebar.title("🎛️ Operaciones")
tab_registrar, tab_admin = st.sidebar.tabs(["➕ Registrar", "⚙️ Ajustes"])

with tab_registrar:
    monto_pedido = st.number_input(
        "Monto del Pedido ($)", min_value=0, step=10, value=0
    )
    monto_cobrado = st.number_input(
        "Monto Recibido ($)", min_value=0, step=10, value=0
    )

    metodo_pago = st.radio(
        "Método de Pago",
        ["Efectivo", "Transferencia / QR"],
        horizontal=True,
    )

    cambio = max(0, monto_cobrado - monto_pedido)
    if monto_cobrado > 0 and metodo_pago == "Efectivo":
        st.info(f"💵 Cambio: **${cambio:,}**")

    st.markdown("---")
    dinero_tomado = st.number_input(
        "Retiro de Caja ($)", min_value=0, step=10, value=0
    )

    if st.button("🚀 Guardar Operación", use_container_width=True):
        if monto_pedido > 0 or dinero_tomado > 0:
            registrar_pedido(
                monto_pedido,
                monto_cobrado,
                cambio,
                dinero_tomado,
                metodo_pago,
            )
            st.toast("Registrado con éxito", icon="✅")
            st.rerun()
        else:
            st.error("Ingresa un monto válido")

with tab_admin:
    if st.button("↩️ Revertir Último Registro", use_container_width=True):
        borrar_ultimo_registro()
        st.toast("Registro eliminado", icon="🗑️")
        st.rerun()

    st.markdown("---")
    if st.checkbox("Habilitar Reinicio"):
        if st.button(
            "🔥 VACIAR REGISTROS", type="primary", use_container_width=True
        ):
            vaciar_base_de_datos()
            st.toast("Base de datos limpia", icon="🚨")
            st.rerun()

# --- CÁLCULOS ---
df = cargar_datos()

if not df.empty:
    # Filtrado por tipo de pago para balance de efectivo
    efectivo_df = df[df["metodo_pago"] == "Efectivo"]
    total_efectivo = int(efectivo_df["monto_pedido"].sum())
    total_transferencias = int(
        df[df["metodo_pago"] == "Transferencia / QR"]["monto_pedido"].sum()
    )
    total_tomado = int(df["dinero_tomado"].sum())

    # El balance físico solo descuenta retiros del efectivo recaudado
    balance_calculado = (total_efectivo - total_tomado) - 200
    total_caja_ajustado = redondear_a_cinco(balance_calculado)
else:
    total_efectivo = 0
    total_transferencias = 0
    total_tomado = 0
    total_caja_ajustado = 0

# --- METRICAS ---
col1, col2, col3 = st.columns(3)
col1.metric("Total en Caja (Efectivo)", f"${total_caja_ajustado:,}")
col2.metric("Ventas por Transferencia", f"${total_transferencias:,}")
col3.metric("Total Retirado de Caja", f"${total_tomado:,}")

st.markdown("<br>", unsafe_allow_html=True)

# --- ANÁLISIS DE VENTAS POR HORA ---
if not df.empty:
    st.subheader("📈 Flujo de Ventas por Hora")

    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    df["Hora"] = df["fecha_dt"].dt.strftime("%H:00")

    ventas_por_hora = (
        df.groupby("Hora")["monto_pedido"].sum().reset_index()
    )

    st.bar_chart(
        ventas_por_hora,
        x="Hora",
        y="monto_pedido",
        color="#00d2ff",
        use_container_width=True,
    )

st.divider()

# --- HISTORIAL ---
st.subheader("📊 Historial General")
if not df.empty:
    st.dataframe(
        df.drop(columns=["fecha_dt"], errors="ignore").rename(
            columns={
                "id": "ID",
                "fecha": "Fecha / Hora",
                "monto_pedido": "Pedido ($)",
                "monto_cobrado": "Cobrado ($)",
                "cambio_entregado": "Cambio ($)",
                "dinero_tomado": "Retiro ($)",
                "metodo_pago": "Método",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Sin operaciones registradas.")