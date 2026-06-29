# _lang v2.0

Segunda versión del sistema de adquisición de idiomas [`_lang`](https://github.com/ulrivera/_lang) cuya premisa era aprender polaco lo mas eficientemente posible. Esta primera versión quedó cerrada formalmente mas no abandonada. Esta es su continuación con una arquitectura distinta.

## Justificación

La arquitectura de `_lang` pedía todo a un solo modelo de lenguaje corriendo local (Qwen 2.5 7B vía Ollama) mediante 4 capas de prompts:
    - Capa 1: Lineamientos generales del sistema
    - Capa 2: Lineamientos operativos del idioma (Voz neural TSS, drills, velocidad)
    - Capa 3: Lineamientos generales por nivel para todos los idiomas (A2, B2, C2)
    - Capa 4: Lineamientos especificos para cuellos de boltella propios del idioma (por ejemplo para PL: Dokonany y Niedokonany)
    

A medida que se realizaban test encontraba dificultades en que el modelo sostuviera la conversación, detectara el error del usuario, decidiera la severidad pedagógica, y devolviera todo eso en un formato JSON estricto, en una sola llamada.

En sesiones más largas el modelo empezaba a romper el formato de salida que le pedía, a veces ignoraba instrucciones pedagógicas explícitas, y en un punto until mezcló sin que se lo pidiera mandarín dentro de una conversación en polaco. No eran fallos aislados — eran el mismo problema apareciendo de formas distintas: un modelo de 7B tiene un límite real de cuántas responsabilidades puede sostener bien al mismo tiempo, sobre todo cuando el contexto crece.

Revisando otra vez la literatura sobre SLMs (modelos de lenguaje pequeños) y RAG, decidi que debia aligerar y optimizar la carga del modelo. No había memoria de mis notas reales, no había nada determinista respaldando sus decisiones — todo dependía de que el modelo "se acordara" de seguir las reglas que le di al inicio del prompt.

## Reestructura

Integro dos modulos al pipeline:
    1. Módulo Analizador, con temperatura baja, solo decide qué error cometió el usuario y qué tan grave es sin generar conversación. 
    2. Módulo Conversador, toma ese diagnóstico y sí genera la respuesta natural. 

El contenido pedagógico alimentan el RAG indexadas a una base de datos vectorial local (ChromaDB) y recuperadas por significado, no por palabra exacta. Una consulta en español encuentra la tarjeta correcta en polaco sin sin que se traduzca.

El semaforo de recast (modulo de corrección) son comportamientos del motor que se aplica siempre que viven completamente separadas del contenido que se busca semánticamente. 

Las combinaciones gramaticales para ejercicios de práctica (drilling) se generan con código Python puro, sin pedirle nada al modelo — cero posibilidad de que alucine una conjugación incorrecta, esto aplicado para los niveles A0 y A2.

## Estado actual

En desarrollo activo:

- Manifiestos de idioma en YAML, separando reglas universales de recast (las que aplican a cualquier idioma) de las específicas de cada uno.
- Parser de vault de Obsidian con validación de formato.
- Indexación en ChromaDB con embeddings multilingües.

Proximo paso: el pipeline de dos pasos (Analizador + Conversador) sobre ese contexto recuperado.

## Stack

Python, SQLite, ChromaDB, sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2), Ollama (Qwen 2.5 7B). Sin servicios en la nube. Corre completo en un Mac Air M1 de 16GB.

## Estructura

Las decisiones técnicas (ADRs), el backlog por sprint, y el detalle de arquitectura están en `TECHNICAL_DESIGN.md`.