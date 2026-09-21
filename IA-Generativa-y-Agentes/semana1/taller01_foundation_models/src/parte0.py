"""Mediciones locales de la Parte 0; sin API ni credenciales."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.logits_process import TopKLogitsWarper, TopPLogitsWarper

from barridos import anotar

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "openai-community/gpt2"
REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
TEMPERATURAS = (0.1, 0.7, 1.0, 1.5, 2.0)
PREFIJOS = {
    "seguro": "As easy as one, two,",
    "abierto": "To calculate the total, we need to",
}


def cargar_modelo():
    # CPU y pocos hilos evitan el coste de coordinar demasiados núcleos.
    torch.set_num_threads(4)
    kwargs = {"revision": REVISION}
    try:
        tok = AutoTokenizer.from_pretrained(MODELO, local_files_only=True, **kwargs)
        modelo = AutoModelForCausalLM.from_pretrained(
            MODELO, local_files_only=True, **kwargs
        )
    except OSError:
        tok = AutoTokenizer.from_pretrained(MODELO, **kwargs)
        modelo = AutoModelForCausalLM.from_pretrained(MODELO, **kwargs)
    return tok, modelo.cpu().eval()


def logits_siguiente(prefijo, tok, modelo):
    ids = tok(prefijo, return_tensors="pt")
    with torch.inference_mode():
        return modelo(**ids).logits[0, -1].double().cpu().numpy()


def softmax(x):
    x = np.asarray(x, dtype=np.float64)
    e = np.exp(x - x.max())
    return e / e.sum()


def entropia_bits(p):
    positivos = np.asarray(p)[np.asarray(p) > 0]
    return float(-np.sum(positivos * np.log2(positivos)))


def tam_nucleo(p, umbral=0.9):
    if not 0 < umbral <= 1:
        raise ValueError("El umbral debe estar en (0, 1].")
    acumulada = np.cumsum(np.sort(p)[::-1])
    # Tolera un ULP: 0.6 + 0.3 se representa ligeramente por debajo de 0.9.
    limite = np.nextafter(float(umbral), -np.inf)
    return min(len(p), int(np.searchsorted(acumulada, limite, side="left")) + 1)


def medir_distribuciones(logits_por_prefijo, tok):
    """Conserva TODOS los logits para reconstruir las métricas y los cortes."""
    filas = []
    for nombre, logits in logits_por_prefijo.items():
        for temperatura in TEMPERATURAS:
            p = softmax(logits / temperatura)
            filas.append({
                "prefijo_id": nombre, "prefijo": PREFIJOS[nombre],
                "temperature": temperatura, "entropia_bits": entropia_bits(p),
                "nucleo_09": tam_nucleo(p), "probabilidad_maxima": float(p.max()),
            })
    ruta = RAIZ / "datos" / "parte0_distribuciones.csv"
    pd.DataFrame(filas).to_csv(ruta, index=False)
    # Es un CSV crudo de un forward por prefijo, no solo los 15 tokens del gráfico.
    crudos = pd.DataFrame({"token_id": np.arange(len(next(iter(logits_por_prefijo.values()))))})
    crudos["token"] = [tok.decode([i]) for i in crudos.token_id]
    for nombre, logits in logits_por_prefijo.items():
        crudos[f"logit_{nombre}"] = logits
    crudos.to_csv(RAIZ / "datos" / "parte0_logits.csv", index=False)
    return pd.read_csv(ruta)


def graficar_distribuciones(crudos, destino):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(13, 9), constrained_layout=True)
    for ax, nombre in zip(axes, PREFIJOS):
        logits = crudos[f"logit_{nombre}"].to_numpy()
        orden = np.argsort(-logits, kind="stable")[:15]
        for temperatura in TEMPERATURAS:
            ax.plot(range(15), softmax(logits / temperatura)[orden],
                    marker="o", markersize=3, label=f"T={temperatura}")
        ax.set_xticks(range(15), [repr(crudos.iloc[i].token) for i in orden],
                      rotation=45, ha="right")
        ax.set_title(f"{nombre}: {PREFIJOS[nombre]!r}")
        ax.set_ylabel("Probabilidad (vocabulario completo)")
        ax.legend(ncol=5)
    fig.savefig(destino, dpi=160)
    return fig


def graficar_cortes(crudos, destino):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    resumen = []
    for fila, nombre in enumerate(PREFIJOS):
        logits = crudos[f"logit_{nombre}"].to_numpy()
        p = softmax(logits)
        orden = np.argsort(-p, kind="stable")
        n = tam_nucleo(p)
        # Verifica los conjuntos contra los filtros reales de transformers.
        scores = torch.tensor(logits)[None, :]
        dummy = torch.zeros((1, 1), dtype=torch.long)
        k_ids = set(torch.isfinite(TopKLogitsWarper(5)(dummy, scores.clone()))[0].nonzero().flatten().tolist())
        p_ids = set(torch.isfinite(TopPLogitsWarper(0.9)(dummy, scores.clone()))[0].nonzero().flatten().tolist())
        assert k_ids == set(orden[:5])
        assert p_ids == set(orden[:n])
        ax = axes[fila, 0]
        ax.bar(range(15), p[orden[:15]], color=["tab:green" if i in p_ids else "lightgray" for i in orden[:15]])
        ax.scatter(range(5), p[orden[:5]], marker="x", color="black", label="top_k=5", zorder=3)
        ax.set_xticks(range(15), [repr(crudos.iloc[i].token) for i in orden[:15]], rotation=45, ha="right")
        ax.set_title(f"{nombre}, T=1: verde = sobrevive top_p=0.9")
        ax.set_ylabel("Probabilidad antes del filtro")
        ax.legend()
        ax = axes[fila, 1]
        ax.plot(np.arange(1, len(p) + 1), np.cumsum(p[orden]))
        ax.axhline(0.9, color="tab:green", linestyle="--")
        ax.axvline(5, color="black", linestyle=":", label="top_k: 5 tokens")
        ax.axvline(n, color="tab:green", linestyle="--", label=f"top_p: {n} tokens")
        ax.set_xscale("log")
        ax.set_xlabel("Número de tokens ordenados por probabilidad")
        ax.set_ylabel("Masa acumulada")
        ax.legend()
        resumen.append({"prefijo": nombre, "top_k": 5, "nucleo_09": n,
                        "masa_top_k": p[orden[:5]].sum(), "masa_top_p": p[orden[:n]].sum(),
                        "conjuntos_iguales": k_ids == p_ids})
    fig.savefig(destino, dpi=160)
    return fig, pd.DataFrame(resumen)


def generar(tok, modelo, prompt, experimento, *, do_sample=False,
            temperature=1.0, top_k=0, top_p=1.0, semilla=123,
            corrida=0, max_new_tokens=40, exactamente=False, caso_id=None):
    """Cronometra generate (sin carga/tokenización) y anota inmediatamente."""
    torch.manual_seed(semilla)
    entrada = tok(prompt, return_tensors="pt")
    config = dict(do_sample=do_sample, temperature=temperature, top_k=top_k,
                  top_p=top_p, max_new_tokens=max_new_tokens,
                  pad_token_id=tok.eos_token_id, repetition_penalty=1.0,
                  no_repeat_ngram_size=0, num_beams=1,
                  return_dict_in_generate=True, output_scores=True)
    if exactamente:
        config["min_new_tokens"] = max_new_tokens
    inicio = time.perf_counter()
    with torch.inference_mode():
        resultado = modelo.generate(**entrada, **config)
    latencia = time.perf_counter() - inicio
    ids = resultado.sequences[0, entrada.input_ids.shape[1]:].tolist()
    salida = tok.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    soportes = [int(torch.isfinite(s[0]).sum()) for s in resultado.scores]
    fila = {
        "caso_id": caso_id or experimento, "tipo": "demostracion",
        "modelo": MODELO, "plantilla": experimento,
        "temperature": temperature, "top_p": top_p, "top_k": top_k,
        "esfuerzo": None, "corrida": corrida,
        "tokens_entrada": entrada.input_ids.shape[1], "tokens_salida": len(ids),
        "tokens_razonamiento": 0, "latencia_s": latencia, "costo_usd": 0,
        "salida": salida, "respuesta_extraida": None, "esperada": None,
        "acierto": None, "error_codigo": None, "error_mensaje": None,
    }
    anotar([fila], parte="0")
    evidencia = {**fila, "prompt": prompt, "ids_salida": ids,
                 "soportes_por_paso": soportes, "semilla": semilla,
                 "config_generacion": config, "revision": REVISION,
                 "fecha_utc": datetime.now(timezone.utc).isoformat()}
    with (RAIZ / "datos" / "parte0_generaciones.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(evidencia, ensure_ascii=False) + "\n")
    return evidencia
