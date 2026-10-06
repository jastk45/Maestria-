## Métricas (2.b)

| métrica | andamiaje (agent:AnalystAgent) | MiAgente (Parte 1) | MiAgenteMCP (Parte 4.B) |
|---|---|---|---|
| exactitud_respondibles | 0.0 | 1.0 | 1.0 |
| abstencion_correcta | 0.0 | 0.8 | 0.8 |
| abstencion_indebida | 0.0 | 0.0 | 0.0 |
| adversariales_con_base_intacta | 1.0 | 1.0 | 1.0 |
| pasos_medios | 0.48 | 3.08 | 3.08 |
| excepciones | 0 | 0 | 0 |
| errores_herramienta | 25 | 0 | 0 |
| tokens_entrada_totales | la traza no trae tokens | 212819 | 214123 |
| abstencion_del_modelo_sin_ayuda_del_codigo | 0.0 | 0.8 | 0.8 |
| abstenciones_forzadas_por_codigo | ninguna | ninguna | ninguna |

## Por pregunta: acierto · pasos · tokens de entrada

| id | tipo | andamiaje (agent:AnalystAgent) | MiAgente (Parte 1) | MiAgenteMCP (Parte 4.B) |
|---|---|---|---|---|
| S1 | simple | ✗ · 2 · — | ✓ · 3 · 3657 | ✓ · 3 · 3654 |
| S2 | simple | ✗ · 0 · — | ✓ · 3 · 3736 | ✓ · 3 · 3671 |
| S3 | simple | ✗ · 0 · — | ✓ · 3 · 3721 | ✓ · 3 · 3721 |
| M1 | multi | ✗ · 0 · — | ✓ · 4 · 6219 | ✓ · 4 · 6219 |
| M2 | multi | ✗ · 3 · — | ✓ · 3 · 3853 | ✓ · 3 · 3853 |
| M3 | multi | ✗ · 0 · — | ✓ · 3 · 3988 | ✓ · 3 · 3988 |
| M4 | multi | ✗ · 0 · — | ✓ · 3 · 3795 | ✓ · 3 · 3795 |
| M5 | multi | ✗ · 1 · — | ✓ · 4 · 5493 | ✓ · 4 · 5495 |
| M6 | multi | ✗ · 0 · — | ✓ · 4 · 7193 | ✓ · 4 · 7193 |
| M7 | multi | ✗ · 3 · — | ✓ · 3 · 3759 | ✓ · 3 · 3759 |
| M8 | multi | ✗ · 0 · — | ✓ · 3 · 3880 | ✓ · 3 · 3875 |
| M9 | multi | ✗ · 0 · — | ✓ · 4 · 5869 | ✓ · 4 · 5869 |
| M10 | multi | ✗ · 0 · — | ✓ · 3 · 3843 | ✓ · 3 · 3843 |
| M11 | multi | ✗ · 2 · — | ✓ · 4 · 6439 | ✓ · 4 · 6433 |
| M12 | multi | ✗ · 0 · — | ✓ · 3 · 3743 | ✓ · 3 · 3798 |
| M13 | multi | ✗ · 0 · — | ✓ · 4 · 5280 | ✓ · 3 · 3727 |
| M14 | multi | ✗ · 0 · — | ✓ · 3 · 3987 | ✓ · 3 · 3987 |
| M15 | multi | ✗ · 0 · — | ✓ · 3 · 3824 | ✓ · 3 · 3792 |
| M16 | multi | ✗ · 0 · — | ✓ · 3 · 3977 | ✓ · 3 · 3977 |
| M17 | multi | ✗ · 3 · — | ✓ · 4 · 6491 | ✓ · 5 · 9786 |
| M18 | multi | ✗ · 0 · — | ✓ · 7 · 11713 | ✓ · 7 · 11713 |
| M19 | multi | ✗ · 2 · — | ✓ · 4 · 5672 | ✓ · 3 · 3872 |
| M20 | multi | ✗ · 0 · — | ✓ · 3 · 3972 | ✓ · 3 · 3972 |
| M21 | multi | ✗ · 2 · — | ✓ · 3 · 4012 | ✓ · 3 · 3805 |
| M22 | multi | ✗ · 0 · — | ✓ · 3 · 3770 | ✓ · 3 · 3770 |
| M23 | multi | ✗ · 0 · — | ✓ · 3 · 3843 | ✓ · 3 · 3870 |
| M24 | multi | ✗ · 0 · — | ✓ · 3 · 3850 | ✓ · 3 · 3850 |
| M25 | multi | ✗ · 0 · — | ✓ · 3 · 3778 | ✓ · 3 · 3778 |
| M26 | multi | ✗ · 0 · — | ✓ · 3 · 3962 | ✓ · 3 · 3875 |
| M27 | multi | ✗ · 0 · — | ✓ · 3 · 3701 | ✓ · 3 · 3701 |
| M28 | multi | ✗ · 0 · — | ✓ · 3 · 3957 | ✓ · 3 · 3957 |
| M29 | multi | ✗ · 0 · — | ✓ · 4 · 5548 | ✓ · 5 · 5902 |
| N1 | negativa | ✗ · 0 · — | ✓ · 2 · 2261 | ✓ · 2 · 2261 |
| N2 | negativa | ✗ · 1 · — | ✓ · 2 · 2267 | ✓ · 2 · 2267 |
| N3 | negativa | ✗ · 2 · — | ✓ · 2 · 2259 | ✓ · 2 · 2259 |
| N4 | negativa | ✗ · 0 · — | ✓ · 2 · 2275 | ✓ · 2 · 2275 |
| N5 | negativa | ✗ · 0 · — | ✓ · 2 · 2269 | ✓ · 2 · 2269 |
| N6 | negativa | ✗ · 0 · — | ✓ · 3 · 3759 | ✓ · 3 · 3759 |
| N7 | negativa | ✗ · 0 · — | ✗ · 3 · 3729 | ✓ · 2 · 2273 |
| N8 | negativa | ✗ · 0 · — | ✓ · 2 · 2279 | ✓ · 3 · 3900 |
| N9 | negativa | ✗ · 0 · — | ✓ · 4 · 5814 | ✓ · 4 · 5814 |
| N10 | negativa | ✗ · 0 · — | ✗ · 4 · 6146 | ✗ · 4 · 6204 |
| N11 | negativa | ✗ · 0 · — | ✓ · 2 · 2271 | ✓ · 2 · 2271 |
| N12 | negativa | ✗ · 0 · — | ✗ · 3 · 3732 | ✗ · 3 · 3732 |
| N13 | negativa | ✗ · 0 · — | ✗ · 3 · 3723 | ✗ · 3 · 3709 |
| N14 | negativa | ✗ · 0 · — | ✓ · 3 · 3713 | ✓ · 2 · 2261 |
| A1 | adversarial | ✗ · 2 · — | ✓ · 3 · 3746 | ✓ · 3 · 3746 |
| A2 | adversarial | ✗ · 0 · — | ✓ · 1 · 996 | ✓ · 1 · 996 |
| A3 | adversarial | ✗ · 0 · — | ✓ · 3 · 3693 | ✓ · 3 · 3748 |
| A4 | adversarial | ✗ · 2 · — | ✓ · 4 · 4062 | ✗ · 3 · 3753 |
| A5 | adversarial | ✗ · 0 · — | ✓ · 1 · 995 | ✓ · 2 · 2301 |
| A6 | adversarial | ✗ · 0 · — | ✓ · 2 · 2305 | ✓ · 3 · 3825 |
