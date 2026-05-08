import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# PARÁMETROS DEFAULT
PROB_CERCANO    = 0.35
PROB_INTERMEDIO = 0.40
PROB_LEJANO     = 0.25

PROB_PARADA_CARTEL = 0.45
MEDIA_CARTEL_SEG  = 60.0
DESVIO_CARTEL_SEG = 20.0

PROB_BLOQUEO   = 0.40
FACTOR_BLOQUEO = 1.80

T_CUADRA_MIN = 30.0
T_CUADRA_MAX = 45.0

PROB_PARADA_EXTRA = 60 / 250
MEDIA_EXTRA_SEG = 80.0

# Cuadras promedio por sector (valor esperado del rango del enunciado)
# Cercano: (1+2)/2=1.5 | Intermedio: (2+3)/2=2.5 | Lejano: (3+5)/2=4.0
CUADRAS_SECTOR = {"Cercano": 1.5, "Intermedio": 2.5, "Lejano": 4.0}


def sector_cuadras_local(rnd, p_cercano, p_intermedio, p_lejano):
    acum1 = p_cercano
    acum2 = p_cercano + p_intermedio
    if rnd < acum1:
        return "Cercano"
    elif rnd < acum2:
        return "Intermedio"
    else:
        return "Lejano"


def simular(n_dias, prob_cercano, prob_intermedio, prob_lejano,
            prob_cartel, media_cartel, desvio_cartel,
            prob_bloqueo, factor_bloqueo,
            t_cuadra_min, t_cuadra_max,
            prob_extra, media_extra,
            fila_inicio):

    # Acumuladores globales
    tiempo_total_acum = 0.0
    tiempo_max = -np.inf
    tiempo_min = np.inf
    cnt_cartel_y_extra = 0
    cnt_sin_cartel_sin_extra = 0
    cnt_bloqueo = 0
    cnt_cercano = 0
    cnt_intermedio = 0
    cnt_lejano = 0
    tiempo_sector = {"Cercano": 0.0, "Intermedio": 0.0, "Lejano": 0.0}

    tiempo_acum_parcial = 0.0
    vector_estado = []
    fila_fin_rango = fila_inicio + 200

    for i in range(1, n_dias + 1):

        # 1. Sector
        rnd_sector = np.random.rand()
        nombre_sector = sector_cuadras_local(rnd_sector, prob_cercano, prob_intermedio, prob_lejano)
        n_cuadras = CUADRAS_SECTOR[nombre_sector]

        # 2. Tiempo por cuadra: Uniforme(30, 45)
        rnd_t_cuadra = np.random.rand()
        t_por_cuadra = t_cuadra_min + rnd_t_cuadra * (t_cuadra_max - t_cuadra_min)
        t_base_total = n_cuadras * t_por_cuadra   # tiempo total de recorrido base

        # 3. Detención en panel/cartel: Bernoulli + Normal(media, desvio)
        rnd_detencion = np.random.rand()
        parada_cartel = rnd_detencion < prob_cartel
        if parada_cartel:
            rnd1_normal = np.random.rand()
            rnd2_normal = np.random.rand()
            z = np.sqrt(-2 * np.log(rnd1_normal + 1e-15)) * np.cos(2 * np.pi * rnd2_normal)
            t_cartel = max(0.0, media_cartel + desvio_cartel * z)
        else:
            rnd1_normal = np.nan
            rnd2_normal = np.nan
            t_cartel = 0.0

        t_circulacion = t_base_total + t_cartel   # base + demora panel

        # 4. Bloqueo de UNA cuadra (solo Cercano y Lejano)
        #    El enunciado: "una de las cuadras... tiempo de circulación en esa cuadra aumente 80%"
        #    → el exceso es t_por_cuadra × 0.80  (solo de esa cuadra bloqueada)
        aplica_bloqueo = nombre_sector in ("Cercano", "Lejano")
        rnd_bloqueo = np.random.rand() if aplica_bloqueo else np.nan
        hubo_bloqueo = aplica_bloqueo and (rnd_bloqueo < prob_bloqueo)

        if hubo_bloqueo:
            t_bloqueo_extra = t_por_cuadra * (factor_bloqueo - 1)  # 80% extra de 1 cuadra
            t_para_sumar = t_circulacion + t_bloqueo_extra
        else:
            t_bloqueo_extra = 0.0
            t_para_sumar = t_circulacion

        # 5. Parada extra: Bernoulli + Exponencial(media)
        rnd_parada_extra = np.random.rand()
        parada_extra = rnd_parada_extra < prob_extra
        if parada_extra:
            rnd_exp = np.random.rand()
            t_extra = -media_extra * np.log(1 - rnd_exp)
        else:
            rnd_exp = np.nan
            t_extra = 0.0

        # 6. Tiempo total de la jornada
        t_total = t_para_sumar + t_extra

        # Acumuladores
        tiempo_total_acum += t_total
        tiempo_acum_parcial += t_total
        if t_total > tiempo_max:
            tiempo_max = t_total
        if t_total < tiempo_min:
            tiempo_min = t_total

        if parada_cartel and parada_extra:
            cnt_cartel_y_extra += 1
        if (not parada_cartel) and (not hubo_bloqueo) and (not parada_extra):
            cnt_sin_cartel_sin_extra += 1
        if hubo_bloqueo:
            cnt_bloqueo += 1

        if nombre_sector == "Cercano":
            cnt_cercano += 1
            tiempo_sector["Cercano"] += t_total
        elif nombre_sector == "Intermedio":
            cnt_intermedio += 1
            tiempo_sector["Intermedio"] += t_total
        else:
            cnt_lejano += 1
            tiempo_sector["Lejano"] += t_total

        # Construir fila del vector de estado 
        en_rango  = fila_inicio <= i <= fila_fin_rango
        es_ultima = i == n_dias

        if en_rango or es_ultima:
            fila = {
                # Sector 
                "Jornada":             i,
                "RND_Sector":          round(rnd_sector, 4),
                "Sector":              nombre_sector,
                "N_Cuadras":           n_cuadras,

                # Recorrido base (Uniforme)
                "RND_T_Cuadra":        round(rnd_t_cuadra, 4),
                "T_x_Cuadra(s)":       round(t_por_cuadra, 2),
                "T_Base_Total(s)":     round(t_base_total, 2),

                # Detención panel (Normal)
                "RND_Detencion":       round(rnd_detencion, 4),
                "Detencion":           "Sí" if parada_cartel else "No",
                "RND1_Normal":         round(rnd1_normal, 4) if parada_cartel else "-",
                "RND2_Normal":         round(rnd2_normal, 4) if parada_cartel else "-",
                "T_Detencion(s)":      round(t_cartel, 2),

                # Circulación acumulada hasta aquí
                "T_Circulacion(s)":    round(t_circulacion, 2),

                # Bloqueo (solo Cercano/Lejano)
                "RND_Bloqueo":         round(rnd_bloqueo, 4) if aplica_bloqueo else "-",
                "Hay_Bloqueo":         "Sí" if hubo_bloqueo else ("No" if aplica_bloqueo else "N/A"),
                "T_Bloqueo_Extra(s)":  round(t_bloqueo_extra, 2),

                # Parada extra (Exponencial)
                "RND_Parada_Extra":    round(rnd_parada_extra, 4),
                "Parada_Extra":        "Sí" if parada_extra else "No",
                "RND_Exp":             round(rnd_exp, 4) if parada_extra else "-",
                "T_Extra(s)":          round(t_extra, 2),

                # Totales y acumuladores de columna
                "T_Total(s)":              round(t_total, 2),
                "T_Acum(s)":               round(tiempo_acum_parcial, 2),
                "T_Prom_Acum(s)":          round(tiempo_acum_parcial / i, 2),
                "Cnt_CartelExtra_Acum":    cnt_cartel_y_extra,
                "Cnt_SinNada_Acum":        cnt_sin_cartel_sin_extra,
                "Cnt_Bloqueo_Acum":        cnt_bloqueo,
            }
            vector_estado.append((i, fila))

    #  KPIs finales
    estadisticas = {
        "t_promedio":               round(tiempo_total_acum / n_dias, 2),
        "pct_cartel_y_extra":       round(cnt_cartel_y_extra / n_dias * 100, 2),
        "cnt_sin_cartel_sin_extra": cnt_sin_cartel_sin_extra,
        "tiempo_max":               round(tiempo_max, 2),
        "tiempo_min":               round(tiempo_min, 2),
        "pct_bloqueo":              round(cnt_bloqueo / n_dias * 100, 2),
        "t_prom_cercano":           round(tiempo_sector["Cercano"] / cnt_cercano, 2) if cnt_cercano else 0,
        "t_prom_lejano":            round(tiempo_sector["Lejano"]  / cnt_lejano,  2) if cnt_lejano  else 0,
        "pct_sector_cercano":       round(cnt_cercano    / n_dias * 100, 2),
        "pct_sector_intermedio":    round(cnt_intermedio / n_dias * 100, 2),
        "pct_sector_lejano":        round(cnt_lejano     / n_dias * 100, 2),
    }

    filas_rango = [f for (idx, f) in vector_estado if fila_inicio <= idx <= fila_fin_rango]
    ultima_fila = [f for (idx, f) in vector_estado if idx == n_dias]

    return filas_rango, ultima_fila[0] if ultima_fila else None, estadisticas


# Helper formato tiempo
def seg_y_min(seg):
    """108.22  →  '108.22 seg  (1 min 48.22 seg)'"""
    minutos = int(seg // 60)
    resto   = seg - minutos * 60
    return f"{seg} seg  ({minutos} min {resto:.2f} seg)"


# INTERFAZ GRÁFICA
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("TP3 – Simulación Parqueando (Montecarlo)")
        self.root.geometry("1400x820")
        self.root.resizable(True, True)

        # Variables de parámetros
        self.n_dias_var = tk.IntVar(value=1000)
        self.semilla_var = tk.IntVar(value=42)
        self.fila_inicio_var = tk.IntVar(value=1)

        self.prob_cercano_var = tk.DoubleVar(value=PROB_CERCANO)
        self.prob_intermedio_var = tk.DoubleVar(value=PROB_INTERMEDIO)
        self.prob_lejano_var = tk.DoubleVar(value=PROB_LEJANO)

        self.prob_cartel_var = tk.DoubleVar(value=PROB_PARADA_CARTEL)
        self.media_cartel_var = tk.DoubleVar(value=MEDIA_CARTEL_SEG)
        self.desvio_cartel_var = tk.DoubleVar(value=DESVIO_CARTEL_SEG)

        self.prob_bloqueo_var = tk.DoubleVar(value=PROB_BLOQUEO)
        self.factor_bloqueo_var = tk.DoubleVar(value=FACTOR_BLOQUEO)

        self.t_cuadra_min_var = tk.DoubleVar(value=T_CUADRA_MIN)
        self.t_cuadra_max_var = tk.DoubleVar(value=T_CUADRA_MAX)

        self.prob_extra_var = tk.DoubleVar(value=round(PROB_PARADA_EXTRA, 4))
        self.media_extra_var = tk.DoubleVar(value=MEDIA_EXTRA_SEG)

        # Variables de resultados
        self.t_prom_var = tk.StringVar(value="–")
        self.pct_cartel_extra_var = tk.StringVar(value="–")
        self.cnt_sin_var = tk.StringVar(value="–")
        self.t_max_var = tk.StringVar(value="–")
        self.t_min_var = tk.StringVar(value="–")
        self.pct_bloqueo_var = tk.StringVar(value="–")
        self.t_prom_cercano_var = tk.StringVar(value="–")
        self.t_prom_lejano_var = tk.StringVar(value="–")
        self.pct_sec_cercano_var = tk.StringVar(value="–")
        self.pct_sec_inter_var = tk.StringVar(value="–")
        self.pct_sec_lejano_var = tk.StringVar(value="–")

        self.df_resultado = None

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.nb = nb

        self.tab_config = ttk.Frame(nb)
        self.tab_tabla = ttk.Frame(nb)
        self.tab_kpi = ttk.Frame(nb)
        self.tab_graficos = ttk.Frame(nb)

        nb.add(self.tab_config, text="⚙ Configuración")
        nb.add(self.tab_tabla, text="Tabla de Simulación")
        nb.add(self.tab_kpi, text="Resultados / KPIs")
        nb.add(self.tab_graficos, text="Gráficos")

        self._build_config_tab()
        self._build_tabla_tab()
        self._build_kpi_tab()
        self._build_graficos_tab()

    # Tab Configuración 
    def _build_config_tab(self):
        tab = self.tab_config

        gen = ttk.LabelFrame(tab, text="Parámetros Generales")
        gen.pack(fill="x", padx=10, pady=6)
        for r, (lbl, var) in enumerate([
            ("N (jornadas a simular):", self.n_dias_var),
            ("Semilla aleatoria:", self.semilla_var),
            ("Fila de inicio visualización:", self.fila_inicio_var),
        ]):
            ttk.Label(gen, text=lbl).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(gen, textvariable=var, width=12).grid(row=r, column=1, padx=6, pady=3)

        sec = ttk.LabelFrame(tab, text="Probabilidades de Sector (deben sumar 1.0)")
        sec.pack(fill="x", padx=10, pady=6)
        for r, (lbl, var) in enumerate([
            ("P(Sector Cercano  1-2 cuadras):", self.prob_cercano_var),
            ("P(Sector Intermedio 2-3 cuadras):", self.prob_intermedio_var),
            ("P(Sector Lejano   3-5 cuadras):", self.prob_lejano_var),
        ]):
            ttk.Label(sec, text=lbl).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(sec, textvariable=var, width=12).grid(row=r, column=1, padx=6, pady=3)

        car = ttk.LabelFrame(tab, text="Detención en Panel/Cartel [Normal] — 45% de ocasiones")
        car.pack(fill="x", padx=10, pady=6)
        for r, (lbl, var) in enumerate([
            ("P(Detención en panel/cartel):", self.prob_cartel_var),
            ("Media demora panel (seg):", self.media_cartel_var),
            ("Desviación demora panel (seg):", self.desvio_cartel_var),
        ]):
            ttk.Label(car, text=lbl).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(car, textvariable=var, width=12).grid(row=r, column=1, padx=6, pady=3)

        blq = ttk.LabelFrame(tab, text="Bloqueo de Cuadra (solo Cercano/Lejano) — 40% de casos")
        blq.pack(fill="x", padx=10, pady=6)
        for r, (lbl, var) in enumerate([
            ("P(Bloqueo cuadra):", self.prob_bloqueo_var),
            ("Factor aumento por bloqueo (×):", self.factor_bloqueo_var),
            ("T_cuadra mínimo (seg):", self.t_cuadra_min_var),
            ("T_cuadra máximo (seg):", self.t_cuadra_max_var),
        ]):
            ttk.Label(blq, text=lbl).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(blq, textvariable=var, width=12).grid(row=r, column=1, padx=6, pady=3)

        ext = ttk.LabelFrame(tab, text="Parada Extra [Exponencial] — 60/250 jornadas")
        ext.pack(fill="x", padx=10, pady=6)
        for r, (lbl, var) in enumerate([
            ("P(Parada extra) — 60/250 = 0.24:", self.prob_extra_var),
            ("Media demora extra (seg):", self.media_extra_var),
        ]):
            ttk.Label(ext, text=lbl).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(ext, textvariable=var, width=12).grid(row=r, column=1, padx=6, pady=3)

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="▶  Ejecutar Simulación",
                command=self.ejecutar).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="↺  Restablecer Defaults",
                command=self.restablecer).pack(side="left", padx=6)

    # Tab Tabla 
    def _build_tabla_tab(self):
        tab = self.tab_tabla
        frame = ttk.Frame(tab)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(frame)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")

        self.tree.tag_configure("ultima", background="#fffacd")
        self.tree.tag_configure("sep", background="#d0d0d0")

    def _cargar_tabla(self, filas_rango, ultima_fila):
        tree = self.tree
        for item in tree.get_children():
            tree.delete(item)
        if not filas_rango and ultima_fila is None:
            return
        cols = list(filas_rango[0].keys()) if filas_rango else list(ultima_fila.keys())
        tree["columns"] = cols
        tree["show"] = "headings"
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor="center")
        for fila in filas_rango:
            tree.insert("", "end", values=list(fila.values()))
        if ultima_fila and (
            not filas_rango or filas_rango[-1]["Jornada"] != ultima_fila["Jornada"]
        ):
            tree.insert("", "end", values=["..."] * len(cols), tags=("sep",))
            tree.insert("", "end", values=list(ultima_fila.values()), tags=("ultima",))

    # Tab KPIs 
    def _build_kpi_tab(self):
        tab = self.tab_kpi

        requeridos = ttk.LabelFrame(tab, text="KPIs Requeridos por la Consigna")
        requeridos.pack(fill="x", padx=10, pady=8)
        for r, (lbl, var) in enumerate([
            ("1. Tiempo promedio de estacionamiento:", self.t_prom_var),
            ("2. % Jornadas con detención en panel Y parada extra:", self.pct_cartel_extra_var),
            ("3. Jornadas SIN detención, SIN bloqueo y SIN extra:", self.cnt_sin_var),
            ("4. Tiempo MÁXIMO de estacionamiento:", self.t_max_var),
            ("5. Tiempo MÍNIMO de estacionamiento:", self.t_min_var),
        ]):
            ttk.Label(requeridos, text=lbl, width=58, anchor="w").grid(
                row=r, column=0, sticky="w", padx=8, pady=4)
            ttk.Label(requeridos, textvariable=var, font=("", 10, "bold"),
                    foreground="#005580").grid(row=r, column=1, padx=8, pady=4, sticky="w")

        extras = ttk.LabelFrame(tab, text="KPIs Adicionales (propuestos por el grupo)")
        extras.pack(fill="x", padx=10, pady=8)
        for r, (lbl, var) in enumerate([
            ("6. % Jornadas con bloqueo de cuadra:", self.pct_bloqueo_var),
            ("7. Tiempo promedio sector Cercano:", self.t_prom_cercano_var),
            ("8. Tiempo promedio sector Lejano:", self.t_prom_lejano_var),
            ("   % Jornadas en sector Cercano:", self.pct_sec_cercano_var),
            ("   % Jornadas en sector Intermedio:", self.pct_sec_inter_var),
            ("   % Jornadas en sector Lejano:", self.pct_sec_lejano_var),
        ]):
            ttk.Label(extras, text=lbl, width=58, anchor="w").grid(
                row=r, column=0, sticky="w", padx=8, pady=4)
            ttk.Label(extras, textvariable=var, font=("", 10, "bold"),
                    foreground="#005500").grid(row=r, column=1, padx=8, pady=4, sticky="w")

        ley = ttk.LabelFrame(tab, text="Leyenda de columnas")
        ley.pack(fill="x", padx=10, pady=8)
        leyenda = (
            "RND_Sector           → define el sector (Cercano / Intermedio / Lejano)\n"
            "N_Cuadras            → cuadras promedio del sector (1.5 / 2.5 / 4.0)\n"
            "RND_T_Cuadra         → RND para Uniforme(30,45): tiempo por cuadra\n"
            "T_x_Cuadra(s)        → tiempo de una sola cuadra = Uniforme(30,45)\n"
            "T_Base_Total(s)      → N_Cuadras × T_x_Cuadra  (recorrido sin eventos)\n"
            "RND_Detencion        → define si se detiene en panel (<0.45 = Sí)\n"
            "RND1/RND2_Normal     → Box-Muller para Normal(60s, 20s) de la detención\n"
            "T_Detencion(s)       → tiempo de demora en el panel (Normal)\n"
            "T_Circulacion(s)     → T_Base_Total + T_Detencion\n"
            "RND_Bloqueo          → define si hay bloqueo (<0.40 = Sí, solo Cerc/Lej)\n"
            "T_Bloqueo_Extra(s)   → 80% extra de T_x_Cuadra (solo la cuadra bloqueada)\n"
            "RND_Parada_Extra     → define si hay parada extra (<60/250 = Sí)\n"
            "RND_Exp              → RND para Exponencial(80s) de la parada extra\n"
            "T_Extra(s)           → tiempo de demora adicional (Exponencial)\n"
            "T_Total(s)           → T_Circulacion + T_Bloqueo_Extra + T_Extra\n"
            "T_Acum(s)            → suma acumulada de T_Total hasta la jornada i\n"
            "T_Prom_Acum(s)       → T_Acum / i  (promedio corriente)\n"
            "Cnt_CartelExtra_Acum → acum. jornadas con panel Y parada extra\n"
            "Cnt_SinNada_Acum     → acum. jornadas sin panel, bloqueo ni extra\n"
            "Cnt_Bloqueo_Acum     → acum. jornadas con bloqueo de cuadra"
        )
        ttk.Label(ley, text=leyenda, justify="left", font=("Courier", 8)).pack(
            padx=8, pady=6, anchor="w")

    # Tab Gráficos 
    def _build_graficos_tab(self):
        tab = self.tab_graficos
        self.fig, self.axs = plt.subplots(1, 2, figsize=(11, 5))
        self.canvas_graf = FigureCanvasTkAgg(self.fig, master=tab)
        self.canvas_graf.get_tk_widget().pack(fill="both", expand=True)
        self.fig.tight_layout(pad=3)

    def _actualizar_graficos(self, estadisticas):
        for ax in self.axs:
            ax.clear()

        # Gráfico 1 — Distribución de sectores
        sectores = ["Cercano", "Intermedio", "Lejano"]
        pcts = [estadisticas["pct_sector_cercano"],
                estadisticas["pct_sector_intermedio"],
                estadisticas["pct_sector_lejano"]]
        self.axs[0].bar(sectores, pcts, color=["#F2DDA4", "#B4E1D0", "#F4B3A8"],
                        edgecolor="#888", linewidth=0.8)
        self.axs[0].set_title("Distribución de Sectores (%)", fontsize=10, fontweight="bold")
        self.axs[0].set_ylabel("%")
        self.axs[0].set_ylim(0, max(pcts) * 1.25)
        for i, v in enumerate(pcts):
            self.axs[0].text(i, v + max(pcts) * 0.03, f"{v:.1f}%", ha="center", fontsize=9)
        for ref in [25, 50, 75]:
            if ref < max(pcts) * 1.25:
                self.axs[0].axhline(ref, color="gray", linestyle="--", linewidth=0.5, alpha=0.5)

        # Gráfico 2 — % eventos (parámetros vs simulados)
        eventos  = ["Detención\nPanel", "Parada\nExtra", "Bloqueo\nCuadra", "Panel\n+ Extra"]
        vals3    = [self.prob_cartel_var.get() * 100,
                    self.prob_extra_var.get()  * 100,
                    estadisticas["pct_bloqueo"],
                    estadisticas["pct_cartel_y_extra"]]
        colores3 = ["#ACF4F4", "#ACF4F4", "#B4E1D0", "#B4E1D0"]
        self.axs[1].bar(eventos, vals3, color=colores3, edgecolor="#888", linewidth=0.8)
        self.axs[1].set_title(
            "% de Ocurrencia de Eventos\n(azul = parámetro ingresado | verde = resultado simulado)",
            fontsize=9, fontweight="bold")
        self.axs[1].set_ylabel("%")
        self.axs[1].set_ylim(0, max(vals3) * 1.25)
        for i, v in enumerate(vals3):
            etiqueta = "↑ param." if i < 2 else "← sim."
            self.axs[1].text(i, v + max(vals3) * 0.03,
                            f"{v:.1f}%\n{etiqueta}", ha="center", fontsize=7.5)

        self.fig.tight_layout(pad=3)
        self.canvas_graf.draw()

    # Lógica de ejecución
    def ejecutar(self):
        n       = self.n_dias_var.get()
        semilla = self.semilla_var.get()
        fila_i  = self.fila_inicio_var.get()

        p_c = self.prob_cercano_var.get()
        p_i = self.prob_intermedio_var.get()
        p_l = self.prob_lejano_var.get()
        if abs(p_c + p_i + p_l - 1.0) > 0.001:
            messagebox.showwarning("Error", "Las probabilidades de sector deben sumar 1.0")
            return
        if fila_i < 1 or fila_i > n:
            messagebox.showwarning("Error", f"Fila de inicio debe estar entre 1 y {n}")
            return
        if n < 1:
            messagebox.showwarning("Error", "N debe ser al menos 1")
            return

        np.random.seed(semilla)

        filas_rango, ultima_fila, stats = simular(
            n_dias=n,
            prob_cercano=p_c, prob_intermedio=p_i, prob_lejano=p_l,
            prob_cartel=self.prob_cartel_var.get(),
            media_cartel=self.media_cartel_var.get(),
            desvio_cartel=self.desvio_cartel_var.get(),
            prob_bloqueo=self.prob_bloqueo_var.get(),
            factor_bloqueo=self.factor_bloqueo_var.get(),
            t_cuadra_min=self.t_cuadra_min_var.get(),
            t_cuadra_max=self.t_cuadra_max_var.get(),
            prob_extra=self.prob_extra_var.get(),
            media_extra=self.media_extra_var.get(),
            fila_inicio=fila_i,
        )

        if filas_rango:
            self.df_resultado = pd.DataFrame(filas_rango)
        elif ultima_fila:
            self.df_resultado = pd.DataFrame([ultima_fila])

        self._cargar_tabla(filas_rango, ultima_fila)

        self.t_prom_var.set(seg_y_min(stats["t_promedio"]))
        self.pct_cartel_extra_var.set(f"{stats['pct_cartel_y_extra']} %")
        self.cnt_sin_var.set(f"{stats['cnt_sin_cartel_sin_extra']} jornadas")
        self.t_max_var.set(seg_y_min(stats["tiempo_max"]))
        self.t_min_var.set(seg_y_min(stats["tiempo_min"]))
        self.pct_bloqueo_var.set(f"{stats['pct_bloqueo']} %")
        self.t_prom_cercano_var.set(seg_y_min(stats["t_prom_cercano"]))
        self.t_prom_lejano_var.set(seg_y_min(stats["t_prom_lejano"]))
        self.pct_sec_cercano_var.set(f"{stats['pct_sector_cercano']} %")
        self.pct_sec_inter_var.set(f"{stats['pct_sector_intermedio']} %")
        self.pct_sec_lejano_var.set(f"{stats['pct_sector_lejano']} %")

        self._actualizar_graficos(stats)
        self.nb.select(self.tab_tabla)
        messagebox.showinfo(
            "Simulación completada",
            f"Se simularon {n:,} jornadas.\n"
            f"Se muestran jornadas {fila_i} a {min(fila_i + 200, n)} "
            f"y la jornada N = {n}.")

    def restablecer(self):
        self.n_dias_var.set(1000)
        self.semilla_var.set(42)
        self.fila_inicio_var.set(1)
        self.prob_cercano_var.set(PROB_CERCANO)
        self.prob_intermedio_var.set(PROB_INTERMEDIO)
        self.prob_lejano_var.set(PROB_LEJANO)
        self.prob_cartel_var.set(PROB_PARADA_CARTEL)
        self.media_cartel_var.set(MEDIA_CARTEL_SEG)
        self.desvio_cartel_var.set(DESVIO_CARTEL_SEG)
        self.prob_bloqueo_var.set(PROB_BLOQUEO)
        self.factor_bloqueo_var.set(FACTOR_BLOQUEO)
        self.t_cuadra_min_var.set(T_CUADRA_MIN)
        self.t_cuadra_max_var.set(T_CUADRA_MAX)
        self.prob_extra_var.set(round(PROB_PARADA_EXTRA, 4))
        self.media_extra_var.set(MEDIA_EXTRA_SEG)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()