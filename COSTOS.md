# Analisis economico

## Arquitectura de costo

La recoleccion desde World Bank y UN Comtrade y el calculo en `src/ranking.py` son deterministas y no consumen tokens. Las APIs publicas no requieren una suscripcion paga para el volumen de este TP.

La capa de lenguaje se limita a explicar una salida JSON ya calculada. Por eso se justifica un modelo pequeno: no decide el ranking ni ejecuta acciones comerciales.

## Estimacion por corrida

Supuesto conservador para una explicacion: 2.000 tokens de entrada (JSON resumido y contrato) y 600 tokens de salida (recomendacion y alertas). El costo exacto depende del proveedor/modelo elegido y debe registrarse al conectar la capa de lenguaje. La decision de separar calculo y explicacion evita usar un modelo grande para una tarea numerica.

## Proyeccion operativa

Con una corrida semanal: 52 corridas por ano. Con cinco escenarios mensuales: 60 corridas por ano. El costo de APIs y calculo permanece en cero bajo las condiciones actuales; el costo variable es exclusivamente la explicacion del modelo y escala linealmente con el numero de corridas.

## Control

Cada corrida conserva entrada, respuestas crudas, fecha y salida. Esto permite medir tokens reales cuando se conecte el modelo y sustituir estas estimaciones por costos observados.
