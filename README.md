# Laboratorio de extracción estructurada con LLM

**Código de ejemplo para pruebas y prototipos.**

La herramienta convierte texto libre de reclamos, solicitudes de soporte u otros temas en JSON validado desde la línea de comandos. Cada tema se define en Markdown mediante reglas de extracción, campos de entrada y salida, y ejemplos. Para adaptar la herramienta a otro tema, editá ese archivo.

El repositorio incluye dos temas con datos sintéticos.

- [Reclamaciones de seguros](temas/seguros.md) con fechas relativas, importes y bienes afectados.
- [Solicitudes de soporte](temas/soporte.md) con categoría, pasos probados y código de error.

## Descarga e instalación

Necesitás Python 3.11 o posterior. Podés [descargar el ZIP](https://github.com/gteijeiro/laboratorio-extraccion-llm/archive/refs/heads/main.zip) y descomprimirlo, o clonar el repositorio con Git.

```bash
git clone https://github.com/gteijeiro/laboratorio-extraccion-llm.git
cd laboratorio-extraccion-llm
```

Desde la carpeta descargada, creá un entorno virtual e instalá el proyecto.

**macOS y Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

**Windows (PowerShell)**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

La instalación base incluye Groq. Para instalar también las integraciones opcionales y las herramientas de prueba, ejecutá `python -m pip install -e '.[all,dev]'`.

## Configurar Groq

Podés validar los temas localmente antes de configurar una cuenta. Para ejecutar los ejemplos con Groq, creá una [clave de API en Groq Console](https://console.groq.com/keys).

En una copia nueva del proyecto, creá tu archivo de configuración local con `cp .env.example .env` en macOS o Linux, o `Copy-Item .env.example .env` en PowerShell. Abrí `.env` con un editor y completá `GROQ_API_KEY`. La plantilla usa `groq` y `openai/gpt-oss-120b`. Si querés declarar la URL, usá `LLM_BASE_URL=https://api.groq.com/openai/v1`. El proyecto carga `.env` automáticamente y Git lo excluye. [Documentación de Groq](https://console.groq.com/docs/openai)

## Uso

Verificá los dos archivos Markdown y sus salidas esperadas sin credenciales:

```bash
extraer-llm --tema temas/seguros.md --validar-tema
extraer-llm --tema temas/soporte.md --validar-tema
```

Con el proveedor configurado, ejecutá los ejemplos directamente desde el archivo Markdown:

```bash
extraer-llm --tema temas/seguros.md
extraer-llm --tema temas/soporte.md
```

La CLI lee el modelo de entrada, el modelo de salida y los valores bajo **Entrada**. Envía al modelo las entradas que figuran en el Markdown e imprime una lista JSON con el nombre y el resultado de cada ejemplo. Los valores de **Salida esperada** sirven para verificar el esquema localmente.

Si el ejemplo incluye una **Nota** con fecha de referencia, se usa esa fecha para interpretar expresiones como «ayer». Podés aplicar una referencia a toda la ejecución con `--fecha-referencia '2026-11-10T18:00:00-03:00'`. Cuando el ejemplo carece de referencia, se usa la hora actual de Córdoba.

También podés analizar una entrada individual:

```bash
extraer-llm --tema temas/soporte.md --texto 'No puedo entrar al portal. Aparece AUTH-403.'
extraer-llm --tema temas/soporte.md --archivo solicitud.txt
```

En esas dos modalidades, el texto se asigna al primer campo obligatorio de tipo `texto` en **Input Model Design**. `--contexto '{"clave":"valor"}'` permite completar otros campos declarados ahí. La salida individual es un objeto JSON. También podés ejecutar `python -m extraccion_llm`.

## Crear otro tema

Copiá `temas/seguros.md` o `temas/soporte.md` y adaptá sus secciones:

1. En `## Output Model Design`, escribí las reglas de extracción y declarale un tipo y un requisito a cada campo con la sintaxis `- **campo** (texto, obligatorio): descripción`.
2. En `## Input Model Design`, declarale un tipo y un requisito a cada campo de entrada. Ubicá primero el campo de texto libre entre los campos de texto obligatorios.
3. En `## Examples`, usá un encabezado `###` por ejemplo. Bajo `**Entrada:**`, escribí los valores con `- **campo:** valor`. Podés agregar `**Salida esperada:**` con el mismo formato y una `**Nota:**` con una frase como «Fecha de referencia 10 de noviembre de 2026».
4. Corré `extraer-llm --tema ruta/al-tema.md --validar-tema`. Después ejecutá el archivo con `extraer-llm --tema ruta/al-tema.md`.

Tipos admitidos: `texto`, `fecha`, `número decimal`, `número entero`, `booleano`, `lista` y `objeto`. Para enumerar valores usá `texto: opción A | opción B` como tipo. Los requisitos admitidos son `obligatorio`, `obligatoria` y `opcional`.

Usá viñetas indentadas para declarar campos de un objeto o de cada elemento de una lista. En el ejemplo de una lista de objetos, el primer campo declarado marca el comienzo de cada elemento. Una lista sin subcampos contiene texto. Los campos opcionales de salida se representan con `null` si no hay datos.

El programa genera un esquema JSON desde el Markdown y valida la salida localmente. Cada proveedor y modelo admite un subconjunto de JSON Schema. Cuando usás un proveedor alojado, el texto de entrada se envía a ese servicio.

## Proveedores

Editá `.env` para cambiar de proveedor o de modelo.

| `LLM_PROVIDER` | Clave | Método predeterminado |
| --- | --- | --- |
| `groq` | `GROQ_API_KEY` | `json_schema` |
| `openai` | `OPENAI_API_KEY` | `json_schema` |
| `anthropic` | `ANTHROPIC_API_KEY` | `function_calling` |
| `ollama` | | `json_schema` |
| `openai_compatible` | `LLM_API_KEY` | `function_calling` |

`LLM_MODEL` indica el identificador del modelo. `LLM_BASE_URL` es obligatoria para `openai_compatible` y opcional para los demás. `LLM_STRUCTURED_METHOD` permite elegir `json_schema` o `function_calling` si el modelo lo admite. `LLM_STRICT` aplica a Groq con `json_schema`. `LLM_TIMEOUT_SECONDS` y `LLM_MAX_RETRIES` controlan los tiempos de espera y los reintentos. En Ollama, los reintentos cubren errores de transporte.

## Pruebas

```bash
python -m pip install -e '.[all,dev]'
python -m compileall -q src tests
pytest -q
```

La suite funciona sin credenciales ni llamadas a proveedores. Los casos de ejemplo son sintéticos.

## Licencia

Publicado bajo la [licencia MIT](LICENSE).
