## Output Model Design

El LLM debe analizar el texto de una reclamación de seguros y devolver los siguientes datos estructurados:

- **tipo_incidente** (texto, obligatorio): tipo de siniestro, como choque, robo, incendio o daño por agua.
- **fecha_incidente** (fecha, opcional): fecha del incidente en formato AAAA-MM-DD.
- **importe_estimado** (número decimal, opcional): costo estimado de los daños.
- **moneda** (texto, opcional): moneda del importe, como ARS o USD.
- **danios_afectados** (lista, obligatoria): lista de bienes afectados. Cada elemento contiene:
  - **descripcion** (texto, obligatorio): descripción del bien o daño.
  - **importe_estimado** (número decimal, opcional): costo estimado del daño individual.
- **descripcion_general** (texto, obligatorio): resumen breve del incidente.

Los campos opcionales deben quedar vacíos cuando no exista información suficiente. No se deben inventar datos.

## Input Model Design

La aplicación recibirá los siguientes datos:

- **texto_reclamacion** (texto, obligatorio): descripción libre del siniestro escrita por el cliente.
- **numero_poliza** (texto, opcional): identificador de la póliza de seguro.
- **nombre_cliente** (texto, opcional): nombre del asegurado.

El LLM analizará el texto de la reclamación para identificar, clasificar y estructurar los datos del incidente.

## Examples

### Ejemplo 1: Accidente de tránsito

**Entrada:**

- **texto_reclamacion:** "El 5 de noviembre de 2026 choqué mi auto contra otro vehículo. Se dañaron el paragolpes delantero y el faro izquierdo. Calculo que la reparación costará unos $850.000 pesos argentinos."
- **numero_poliza:** "AUT-12345"
- **nombre_cliente:** "Juan Pérez"

**Salida esperada:**

- **tipo_incidente:** "choque"
- **fecha_incidente:** "2026-11-05"
- **importe_estimado:** 850000
- **moneda:** "ARS"
- **danios_afectados:**
  - **descripcion:** "Paragolpes delantero dañado"
  - **descripcion:** "Faro izquierdo dañado"
- **descripcion_general:** "Colisión con otro vehículo que provocó daños en la parte delantera del automóvil."

### Ejemplo 2: Daño por agua en vivienda

**Entrada:**

- **texto_reclamacion:** "Ayer se rompió una cañería de la cocina y se inundó parte de mi casa. Se dañaron los muebles de cocina y el piso de madera. Todavía no sé cuánto costarán las reparaciones."
- **numero_poliza:** "HOG-67890"
- **nombre_cliente:** "María Gómez"

**Salida esperada:**

- **tipo_incidente:** "daño por agua"
- **fecha_incidente:** "2026-11-09"
- **importe_estimado:** null
- **moneda:** null
- **danios_afectados:**
  - **descripcion:** "Muebles de cocina dañados por agua"
  - **descripcion:** "Piso de madera dañado por inundación"
- **descripcion_general:** "Rotura de cañería que provocó una inundación y daños materiales en la vivienda."

**Nota:** La fecha del segundo ejemplo se calcula considerando que la reclamación se recibió el 10 de noviembre de 2026.
