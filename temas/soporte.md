# Solicitudes de soporte técnico

## Output Model Design

Identificá el producto o sistema mencionado y resumí el problema principal.

- **producto** (texto, opcional): producto o sistema mencionado.
- **categoria** (texto: acceso | rendimiento | funcionalidad | otro, obligatoria): categoría del problema principal.
- **problema** (texto, obligatorio): resumen breve del problema informado.
- **pasos_probados** (lista, obligatoria): pasos que el usuario dice que ya probó. Usá una lista vacía si no informa ninguno.
- **codigo_error** (texto, opcional): código de error tal como aparece.

## Input Model Design

- **texto_solicitud** (texto, obligatorio): descripción del problema escrita por el usuario.

## Examples

### Error de acceso

**Entrada:**

- **texto_solicitud:** "No puedo entrar al portal de clientes. Ya restablecí mi contraseña y probé en otro navegador. Aparece el error AUTH-403."

**Salida esperada:**

- **producto:** "Portal de clientes"
- **categoria:** "acceso"
- **problema:** "El usuario no puede iniciar sesión en el portal."
- **pasos_probados:**
  - "Restableció la contraseña"
  - "Probó en otro navegador"
- **codigo_error:** "AUTH-403"
