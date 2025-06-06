import pandas as pd, re
from pathlib import Path
import streamlit as st
import pandas as pd
import re
from io import StringIO, BytesIO

# ───── 1. Analiza una línea ─────────────────────────────────────────
def parse_line(line:str):
    # Acepta solo líneas que comienzan con la fecha legible
    if not re.match(r'^[A-Za-z]{3} \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2}', line):
        return None

    rest  = line.split(",", 1)[1].lstrip()
    parts = [p.replace('\x02','').replace('\x03','').strip()
             for p in rest.split(",") if p != ""]

    # Elimina la columna “Q”
    if parts and parts[0] == "Q":
        parts.pop(0)

    # Quita el CRC (última columna: 1–2 dígitos hexadecimales)
    if parts and re.fullmatch(r'[0-9A-Fa-f]{1,2}', parts[-1]):
        crc = parts.pop()          # guardado si luego lo quieres

    # Ahora deben quedar 13 campos (incluyendo “m” y Flag)
    if len(parts) != 13:
        return None

    # Posiciones: 0 Dir, 1 Vel, 2 DirCorr, 3 P, 4 H, 5 Temp, 6 Dew,
    # 7 PrecipTot, 8 IntPrec, 9 Irrad, 10 FechaISO, 11 m, 12 Flag
    # ── Limpia signos “+” en Temp y Dew
    parts[5] = parts[5].lstrip("+")
    parts[6] = parts[6].lstrip("+")

    # ── Elimina la variable m (penúltima)
    parts.pop(-2)           # elimina índice 11

    return parts            # 12 columnas finales

# ───── 2. Lee el archivo completo ───────────────────────────────────
def parse_file(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return [row for l in f if (row:=parse_line(l))]

# ───── 3. Procesa y exporta promedios horarios ──────────────────────
def procesar(path_txt):
    filas = parse_file(path_txt)
    if not filas:
        print("⚠️  No se encontraron registros válidos.")
        return

    cols = ["DirViento","VelViento","DirVientoCorr","Presion","Humedad",
            "Temp","PuntoRocio","PrecipTotal","IntensidadPrec",
            "Irradiancia","FechaISO","Flag"]

    df = pd.DataFrame(filas, columns=cols)

    # Numéricas
    num = [c for c in cols if c not in ("FechaISO","Flag")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")

    # Fecha
    df["FechaISO"] = pd.to_datetime(df["FechaISO"], errors="coerce")
    df = df.dropna(subset=["FechaISO"])

    # Promedio por hora
    df["FechaHora"] = df["FechaISO"].dt.floor("h")
    df_h = df.groupby("FechaHora")[num].mean().reset_index()

    # Nombres de salida
    base = Path(path_txt)
    csv_out  = base.with_name(base.stem + "_promedios.csv")
    xlsx_out = base.with_name(base.stem + "_promedios.xlsx")

    df_h.to_csv(csv_out, index=False)
    try:
        import openpyxl
        df_h.to_excel(xlsx_out, index=False)
        print(f"✅ Exportados: {csv_out.name} y {xlsx_out.name}")
    except ImportError:
        print(f"✅ Exportado: {csv_out.name} (instala openpyxl para Excel)")

def procesar_buffer(uploaded_file):
    filas = [parse_line(l.decode('utf-8','ignore')) for l in uploaded_file.readlines()]
    filas = [f for f in filas if f]
    if not filas:
        raise ValueError("Sin registros válidos.")
    cols = ["DirViento","VelViento","DirVientoCorr","Presion","Humedad",
            "Temp","PuntoRocio","PrecipTotal","IntensidadPrec",
            "Irradiancia","FechaISO","Flag"]
    df = pd.DataFrame(filas,columns=cols)
    num = [c for c in cols if c not in ("FechaISO","Flag")]
    df[num] = df[num].apply(pd.to_numeric,errors="coerce")
    df["FechaISO"] = pd.to_datetime(df["FechaISO"],errors="coerce")
    df = df.dropna(subset=["FechaISO"])
    df["FechaHora"] = df["FechaISO"].dt.floor("h")
    return df.groupby("FechaHora")[num].mean().reset_index()

# ---------- interfaz Streamlit ----------
st.set_page_config(page_title="Promedios horarios",page_icon="☁️")
st.title("☁️ Procesador de datos meteorológicos")

archivo=st.file_uploader("Sube el archivo .txt",type="txt")
if archivo:
    try:
        df=procesar_buffer(archivo)
        st.success(f"Procesadas {len(df)} horas de datos.")
        st.dataframe(df,use_container_width=True)

        # Descarga CSV
        csv=StringIO(); df.to_csv(csv,index=False,sep=";")
        st.download_button("⬇️ Descargar CSV",csv.getvalue(),
                           "promedios_horarios.csv","text/csv")

        # Descarga Excel en memoria
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        st.download_button("⬇️ Descargar Excel", bio.getvalue(),
                           "promedios_horarios.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Cargar un .txt para comenzar.")


