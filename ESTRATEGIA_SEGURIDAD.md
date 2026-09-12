# 🛡️ Estrategia de Ciberseguridad — Gestión Comercial

Estrategia de defensa del aplicativo contra las clases de ataque relevantes para una aplicación web (alineada con **OWASP Top 10 2021**). Para cada amenaza: cómo funciona el ataque, **qué ya está implementado** en este proyecto, y **qué falta / se recomienda** por fases.

Leyenda: ✅ implementado · 🟡 parcial · 🔴 pendiente (recomendado)

---

## 1. Inyección SQL (A03: Injection)

**Ataque:** el atacante mete SQL en un campo (`'; DROP TABLE users;--`) para leer o destruir datos.

- ✅ **ORM con consultas parametrizadas.** Todo acceso a datos pasa por SQLAlchemy; nunca se concatena SQL con texto del usuario. Los filtros de búsqueda (`ilike`) usan parámetros enlazados.
- ✅ **Validación de tipos con Pydantic** en todos los endpoints: un `variant_id` debe ser entero, una cantidad `Decimal > 0`; lo que no cumple el esquema se rechaza con 422 antes de tocar la BD.
- 🔴 Mantener la regla: si algún día se necesita SQL crudo, usar siempre `text()` con parámetros enlazados (`:param`), jamás f-strings.

## 2. Cross-Site Scripting — XSS (A03)

**Ataque:** inyectar `<script>` en un campo (nombre de producto, notas) para robar sesiones de otros usuarios.

- ✅ **React escapa todo por defecto.** El proyecto no usa `dangerouslySetInnerHTML` en ningún componente; cualquier texto malicioso se renderiza como texto plano.
- ✅ La API devuelve `Content-Type: application/json`, nunca HTML con datos del usuario.
- 🟡 **Token JWT en `localStorage`**: si existiera un XSS, el token sería robable. Mitigación actual: no hay vías de XSS conocidas + expiración de 8h. Endurecimiento futuro: migrar a cookies `HttpOnly; Secure; SameSite=Strict` (requiere añadir protección CSRF) o reducir expiración.
- 🔴 **Añadir cabecera Content-Security-Policy** en el frontend (ver sección 11) para bloquear scripts externos incluso si algo se escapara.

## 3. Autenticación rota (A07: Identification & Authentication Failures)

**Ataque:** adivinar contraseñas (fuerza bruta), robar credenciales, usar sesiones eternas.

- ✅ **Hash pbkdf2-sha256 con 600.000 iteraciones y salt aleatorio por usuario** — nunca se guarda la contraseña; un volcado de la BD no revela claves.
- ✅ Comparación con `secrets.compare_digest` (inmune a timing attacks).
- ✅ **JWT firmado (HS256) con expiración de 8 horas** (jornada laboral); usuario desactivado se verifica contra BD en **cada** request (desactivar = expulsión inmediata aunque el token siga vigente).
- ✅ Mensaje de error genérico en login ("correo o contraseña incorrectos") — no revela si el correo existe.
- ✅ Mínimo 6 caracteres de contraseña validado en backend.
- 🔴 **Rate limiting en `/auth/login`** (prioridad alta): p. ej. 5 intentos/minuto por IP. En Vercel: middleware simple con ventana en BD, o Cloudflare gratuito delante.
- 🔴 Bloqueo temporal de cuenta tras N intentos fallidos + registro del evento.
- 🔴 Política de contraseñas más fuerte para admins (12+ caracteres) y forzar cambio de la clave sembrada en el primer login.
- 🔴 (Futuro) 2FA TOTP para el rol administrador.

## 4. Control de acceso roto — IDOR / escalada (A01: Broken Access Control)

**Ataque:** un vendedor llama directamente a la API (`GET /purchases`, `POST /users`) saltándose los botones ocultos, o consulta ventas de otros cambiando el ID en la URL.

- ✅ **Autorización en el backend, no en la UI:** todos los endpoints exigen token (`get_current_user`); los de gestión exigen `require_admin` a nivel de router. Ocultar botones es solo cosmético.
- ✅ **Anti-IDOR en recursos por dueño:** `GET /sales/{id}` y `GET /invoices/{id}` verifican que la venta pertenezca al vendedor (o que sea admin) → 403. Los listados filtran por `user_id` en la consulta SQL.
- ✅ Anular ventas: solo admin (verificado con test automatizado).
- ✅ Deny-by-default: no existe ningún endpoint sin dependencia de autenticación salvo `/auth/login` y `/api/health`.
- 🔴 **Auditoría**: registrar quién cambia precios, usuarios y configuración (tabla `audit_log`), para detectar abuso de cuentas admin.

## 5. CSRF (Cross-Site Request Forgery)

**Ataque:** una página maliciosa hace que tu navegador, ya logueado, envíe una petición a la API sin que lo sepas.

- ✅ **Arquitectura inmune por diseño:** el token viaja en el header `Authorization: Bearer`, no en cookies. El navegador **no** adjunta ese header automáticamente desde otros sitios, así que el CSRF clásico no aplica.
- ✅ CORS restrictivo (ver sección 6) impide que otros orígenes lean respuestas.
- ⚠️ Regla a futuro: si se migra a cookies (sección 2), **hay que** añadir tokens CSRF al mismo tiempo.

## 6. Configuración insegura (A05: Security Misconfiguration)

- ✅ **CORS con lista blanca explícita** por variable de entorno (`CORS_ORIGINS`), `allow_credentials=False`, headers limitados a `Authorization` y `Content-Type`. Nada de `*`.
- ✅ **Documentación de la API (`/api/docs`) deshabilitada en producción** (`ENV=production`).
- ✅ HTTPS automático en Vercel y Supabase (TLS extremo a extremo); conexión a BD con `sslmode=require`.
- ✅ Los errores devuelven mensajes controlados; los stack traces no llegan al cliente en producción.
- 🔴 **Validar `JWT_SECRET` en el arranque:** hoy, si en producción olvidas la variable, usaría el default de desarrollo. Añadir en `config.py`: si `ENV=production` y el secreto es el default → abortar el arranque.
- 🔴 Cabeceras de seguridad (sección 11).

## 7. Exposición de datos sensibles (A02: Cryptographic Failures)

- ✅ **Ningún secreto en el frontend:** el bundle de Vite solo contiene `VITE_API_URL` (pública por naturaleza). `DATABASE_URL` y `JWT_SECRET` viven solo como variables de entorno del backend en Vercel.
- ✅ `.env` y `dev.db` en `.gitignore` — el repositorio no contiene credenciales.
- ✅ Los endpoints nunca serializan `password_hash` (los schemas Pydantic definen explícitamente qué campos salen).
- 🔴 Rotación: cambiar `JWT_SECRET` y la clave de Supabase si algún colaborador sale del proyecto; rotar cada 6-12 meses.
- 🔴 No compartir la URL directa (5432) de Supabase; es solo para migraciones desde tu PC.

## 8. Integridad de datos y lógica de negocio

**Ataque:** manipular el cliente para vender a precio 0, cantidades negativas, o sobrevender concurrentemente.

- ✅ **El servidor calcula todos los totales.** El carrito solo envía `variant_id + cantidad + unidad`; precio, IVA y total salen de la BD — imposible manipular precios desde el navegador.
- ✅ Cantidades `> 0` validadas (Pydantic + CHECK en BD); cantidades enteras para productos por unidad.
- ✅ **Anti-sobreventa atómica:** `UPDATE stock ... WHERE quantity >= cantidad` + `CHECK (quantity >= 0)` como segunda barrera; rollback total de la venta multilínea si una línea falla.
- ✅ No se puede vender una variante sin precio **publicado** ni de producto inactivo.
- ✅ Facturas con snapshots inmutables y consecutivo con row-lock (sin duplicados ni huecos incluso con ventas simultáneas).

## 9. Denegación de servicio — DoS (y abuso de recursos)

- ✅ Paginación obligatoria con tope (`page_size <= 100/200`) en todos los listados — nadie puede pedir "toda la tabla".
- ✅ Serverless de Vercel escala y aísla por request; pgbouncer protege a Postgres de agotamiento de conexiones (`NullPool` + pooler).
- ✅ Límites de longitud en todos los campos (`String(N)`, `max_length` en Pydantic).
- 🔴 **Rate limiting global por IP** (el free tier de Vercel no lo trae): poner **Cloudflare** (plan gratuito) delante del dominio da rate limiting, WAF básico y protección DDoS sin costo.
- 🔴 Vigilar el uso en los dashboards de Vercel/Supabase (el free tier se suspende si se agota — un ataque de volumen se convierte en indisponibilidad).

## 10. Dependencias vulnerables (A06: Vulnerable & Outdated Components)

- ✅ Superficie mínima: 6 paquetes Python de producción, sin librerías abandonadas (se evitó passlib/python-jose deliberadamente).
- ✅ Versiones fijadas (`requirements.txt`, `package-lock.json`) — builds reproducibles.
- 🔴 **Activar Dependabot** en GitHub (Settings → Security → Dependabot alerts + security updates). Gratis y automático.
- 🔴 Revisar y actualizar dependencias cada 1-2 meses (`pip list --outdated`, `npm audit`).

## 11. Cabeceras de seguridad HTTP (endurecimiento del navegador)

🔴 **Pendiente — quick win.** Añadir al `frontend/vercel.json`:

```json
{
  "rewrites": [{ "source": "/((?!assets/).*)", "destination": "/index.html" }],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
        { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains" },
        { "key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://TU-BACKEND.vercel.app" }
      ]
    }
  ]
}
```

(Reemplazar `TU-BACKEND` por la URL real de la API. `X-Frame-Options: DENY` también previene **clickjacking**.)

## 12. Registro, monitoreo y respuesta (A09: Logging & Monitoring Failures)

- 🟡 Vercel guarda logs de cada request y Supabase logs de BD (retención corta en free tier).
- 🔴 Registrar eventos de seguridad: logins fallidos, cambios de usuarios/roles, anulaciones de ventas, cambios de precios.
- 🔴 **Sentry (plan gratuito)** para errores del backend y frontend con alertas por correo.
- 🔴 Plan de respuesta ante incidente (mínimo): 1) rotar `JWT_SECRET` (invalida todas las sesiones), 2) rotar clave de BD en Supabase y actualizar variables en Vercel, 3) desactivar usuarios comprometidos, 4) revisar el kardex y `audit_log` para medir impacto.

## 13. Copias de seguridad y recuperación

- ✅ Supabase free hace backups diarios (retención 7 días).
- 🔴 Exportación semanal manual/programada adicional (`pg_dump` con la URL directa) guardada fuera de Supabase — protege contra borrado accidental del proyecto y ransomware.
- 🔴 Probar la restauración al menos una vez ("un backup no probado no es un backup").

## 14. Cadena de suministro y repositorio

- ✅ Repositorio limpio; `.env` y base local excluidos.
- 🔴 Activar **2FA en GitHub, Vercel y Supabase** (prioridad alta: quien controla esas cuentas controla todo el sistema).
- 🔴 Proteger la rama `main` (Settings → Branches → protection rule: PR antes de merge) cuando trabaje más de una persona.
- 🔴 GitHub Actions de CI (pytest + build) para que nada roto llegue a producción.

---

## Plan de acción priorizado

| # | Acción | Esfuerzo | Impacto | Estado |
|---|--------|----------|---------|--------|
| 1 | 2FA en GitHub, Vercel y Supabase | 15 min | 🔥 Crítico | 🔴 Manual (hazlo tú en cada cuenta) |
| 2 | Validar `JWT_SECRET` en arranque (abortar si default en prod) | 10 min | Alto | ✅ Hecho (`app/main.py`) |
| 3 | Cabeceras de seguridad en `frontend/vercel.json` | 15 min | Alto | ✅ Hecho (afina `connect-src` con la URL real del backend) |
| 4 | Rate limiting en login (+ Cloudflare gratis delante) | 2-4 h | Alto | 🔴 Pendiente |
| 5 | Dependabot + `npm audit`/`pip audit` periódicos | 15 min | Medio | 🟡 CI creado; activa Dependabot en GitHub (Settings → Security) |
| 6 | Sentry + logging de eventos de seguridad | 2-3 h | Medio | 🟡 Integración lista: define `SENTRY_DSN` en Vercel al crear cuenta en sentry.io |
| 7 | Tabla `audit_log` para acciones de admin | 3-4 h | Medio | 🔴 Pendiente |
| 8 | Backup externo semanal con `pg_dump` | 1 h | Medio | 🔴 Pendiente |
| 9 | Forzar cambio de contraseña inicial + política 12+ chars admin | 2 h | Medio | 🔴 Pendiente |
| 10 | Migrar token a cookie HttpOnly + CSRF tokens (opcional) | 4-6 h | Bajo/Medio | 🔴 Pendiente |

**Principio rector:** la seguridad ya está *en el diseño* (autorización server-side, totales calculados en servidor, ORM parametrizado, secretos fuera del código). Las mejoras pendientes son capas adicionales de defensa en profundidad, no parches a huecos estructurales.
