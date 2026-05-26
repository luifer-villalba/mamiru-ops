# 🗺️ Roadmap — mamiru-ops

Seguimiento interno de features. Prefijo: `MOP-`, arranca en `MOP-102`.  
**Target:** Todo listo antes de que Eli vuelva a la oficina en junio.

> **Para Codex:** Desarrollar en orden. Un commit por ticket. Mensaje de commit: `MOP-XXX · Título del ticket`. Correr tests y ruff antes de cada commit.

---

## ✅ Done

- Catálogo de productos (Product, Category, Supplier, ProductImage)
- Panel de administración con django-unfold
- Filtros de stock (bajo, sin stock), acciones bulk (activar, ocultar, sin stock)
- Importador CSV (`import_mamiru_stock`)
- API REST de solo lectura (`/api/products/`, `/api/categories/`, `/api/suppliers/`)
- Órdenes de compra (PurchaseOrder + PurchaseOrderLine) con ajuste de stock automático
- MOP-100 · Historial de precios con auditoría de cambios en producto
- MOP-101 · Clientes y Pedidos (Customer, Order, OrderLine)
- Login con usuario o email
- CI con GitHub Actions (tests + ruff)
- Deploy en Railway con Docker

---

## 🚧 In Progress

_(nada actualmente)_

---

## 📋 Backlog activo

> Orden de desarrollo recomendado. MOP-102 a 106 comparten migración — se pueden agrupar en un solo `makemigrations` antes de los commits individuales.

---

### MOP-102 · Canal de origen en Pedidos
**Prioridad:** Alta | **Esfuerzo:** Bajo  
**Commit:** `MOP-102 · Canal de origen en Pedidos`

**Descripción:**  
Eli necesita saber qué canal trae clientes. Sin esto no hay forma de evaluar si Instagram o WhatsApp convierte más, ni si vale la pena invertir en ads para Pilar.

**Cambios en `Order`:**
```python
class Source(models.TextChoices):
    WHATSAPP   = "whatsapp",   "WhatsApp"
    INSTAGRAM  = "instagram",  "Instagram"
    FACEBOOK   = "facebook",   "Facebook"
    REFERRAL   = "referral",   "Referido"
    OTHER      = "other",      "Otro"

source = models.CharField(
    "Canal de origen",
    max_length=20,
    choices=Source.choices,
    blank=True,
    default="",
)
```

**Admin:** Agregar `source` a `list_display`, `list_filter` y al fieldset del formulario.

**Criterios de aceptación:**
- [ ] Campo visible y editable en el admin
- [ ] Filtro por canal en la lista de pedidos
- [ ] Campo opcional (blank=True) — no rompe pedidos existentes
- [ ] Test: pedido creado sin source tiene valor vacío por defecto

---

### MOP-103 · Modalidad y ciudad de entrega en Pedidos
**Prioridad:** Alta | **Esfuerzo:** Bajo  
**Commit:** `MOP-103 · Modalidad y ciudad de entrega en Pedidos`

**Descripción:**  
Diferencia Asunción (retiro) de Pilar (envío). Eli desde la oficina necesita ver de un vistazo qué pedidos requieren coordinación logística.

**Cambios en `Order`:**
```python
class DeliveryType(models.TextChoices):
    PICKUP   = "pickup",   "Retiro en Asunción"
    SHIPPING = "shipping", "Envío"

delivery_type = models.CharField(
    "Modalidad de entrega",
    max_length=20,
    choices=DeliveryType.choices,
    default=DeliveryType.PICKUP,
)
delivery_city = models.CharField("Ciudad de entrega", max_length=100, blank=True, default="")
```

**Admin:** Agregar a `list_display`, `list_filter` y fieldset.

**Criterios de aceptación:**
- [ ] Pedido con `delivery_type=shipping` muestra ciudad
- [ ] Filtro por modalidad funciona
- [ ] Test: pedido sin ciudad creado con delivery_type=pickup es válido

---

### MOP-104 · Descuento por pedido
**Prioridad:** Alta | **Esfuerzo:** Bajo  
**Commit:** `MOP-104 · Descuento por pedido`

**Descripción:**  
Eli da descuentos a conocidas. Sin campo de descuento, el `total` del pedido no refleja lo que se cobró realmente y los márgenes quedan mal calculados.

**Cambios en `Order`:**
```python
discount_amount = models.PositiveIntegerField("Descuento (Gs.)", default=0)
```

**Cambio en `Order.total` property:**
```python
@property
def total(self):
    subtotal = sum(line.total for line in self.lines.all())
    return max(subtotal - self.discount_amount, 0)
```

**Admin:** Mostrar `discount_amount` en el fieldset. Mostrar subtotal y descuento en el resumen del pedido.

**Criterios de aceptación:**
- [ ] Pedido con descuento 10.000 Gs muestra total correcto
- [ ] Total nunca negativo
- [ ] Test: subtotal 50.000, descuento 10.000 → total 40.000
- [ ] Test: descuento mayor al subtotal → total es 0

---

### MOP-105 · Método de pago en Pedidos
**Prioridad:** Alta | **Esfuerzo:** Bajo  
**Commit:** `MOP-105 · Método de pago en Pedidos`

**Descripción:**  
Control de caja real. Ueno, transferencia y efectivo tienen flujos distintos — necesario para conciliar al final del día.

**Cambios en `Order`:**
```python
class PaymentMethod(models.TextChoices):
    CASH     = "cash",     "Efectivo"
    TRANSFER = "transfer", "Transferencia"
    UENO     = "ueno",     "Ueno"
    OTHER    = "other",    "Otro"

payment_method = models.CharField(
    "Método de pago",
    max_length=20,
    choices=PaymentMethod.choices,
    blank=True,
    default="",
)
```

**Admin:** Agregar a `list_display`, `list_filter` y fieldset.

**Criterios de aceptación:**
- [ ] Campo visible y filtrable
- [ ] Opcional — no rompe pedidos existentes
- [ ] Test: pedido con payment_method=ueno se guarda correctamente

---

### MOP-106 · Estado "Seña recibida" en Pedidos
**Prioridad:** Alta | **Esfuerzo:** Bajo  
**Commit:** `MOP-106 · Estado seña recibida en Pedidos`

**Descripción:**  
Eli exige seña obligatoria desde día 1. El flujo real es: confirmado → seña recibida → entregado. Sin este estado intermedio no hay forma de saber qué pedidos están "en proceso" vs "pendientes de seña".

**Cambio en `Order.Status`:**
```python
# Agregar entre CONFIRMED y DELIVERED:
DEPOSIT = "deposit", "Seña recibida"
```

Flujo completo: `draft → confirmed → deposit → delivered`  
`cancelled` disponible desde cualquier estado.

**Admin:** Actualizar `list_display` y `list_filter` para incluir el nuevo estado. El color del badge en unfold debe diferenciarlo visualmente.

**Criterios de aceptación:**
- [ ] Transición confirmed → deposit → delivered funciona
- [ ] Pedidos en estado "deposit" aparecen diferenciados en la lista
- [ ] Test: pedido en deposit no descuenta stock de nuevo (solo confirmed lo hace)
- [ ] Migración aplica sin errores

---

### MOP-107 · Seguimiento de envío en Pedidos
**Prioridad:** Alta | **Esfuerzo:** Bajo  
**Commit:** `MOP-107 · Seguimiento de envío en Pedidos`

**Descripción:**  
Cuando una clienta de Pilar pregunta "¿dónde está mi pedido?", Eli necesita la respuesta en 5 segundos desde la oficina, sin llamar a Luifer.

**Cambios en `Order`:**
```python
shipping_service = models.CharField(
    "Servicio de envío",
    max_length=100,
    blank=True,
    default="",
)  # ej: "Urbano", "PedidosYa", "Encomienda bus"

tracking_code = models.CharField(
    "Código de seguimiento",
    max_length=200,
    blank=True,
    default="",
)

shipped_at = models.DateField(
    "Fecha de envío",
    null=True,
    blank=True,
)
```

**Admin:** Mostrar `shipping_service`, `tracking_code` y `shipped_at` en un fieldset "Envío" que aparezca solo cuando `delivery_type=shipping`.

**Criterios de aceptación:**
- [ ] Campos editables en el admin
- [ ] Campos opcionales — no afectan pedidos de retiro
- [ ] Test: pedido con tracking_code se guarda y recupera correctamente

---

### MOP-108 · Vista de pedidos activos (mobile-friendly)
**Prioridad:** Alta | **Esfuerzo:** Medio  
**Commit:** `MOP-108 · Vista de pedidos activos`

**Descripción:**  
Eli opera desde el celular en la oficina. Necesita una pantalla simple que muestre solo los pedidos "vivos" (confirmed, deposit, shipped si se agrega) sin navegar el admin completo.

**Implementación:**
- Custom admin view en `catalog/` registrada en `config/urls.py`
- URL: `/ops/pedidos/activos/`
- Requiere login (`@login_required`)
- Muestra pedidos con status en `[confirmed, deposit]` ordenados por fecha desc
- Columnas: cliente, whatsapp (clickeable como `wa.me/`), estado, modalidad, ciudad, total, notas
- Sin paginación — son pocos pedidos simultáneos
- Template con clases de unfold, responsive

**Criterios de aceptación:**
- [ ] URL accesible solo para usuarios logueados
- [ ] Muestra solo pedidos activos (no draft, delivered, cancelled)
- [ ] WhatsApp de cada cliente es un link directo
- [ ] Test: usuario no autenticado es redirigido al login

---

### MOP-109 · Dashboard de métricas del mes
**Prioridad:** Media | **Esfuerzo:** Medio  
**Commit:** `MOP-109 · Dashboard de métricas del mes`  
**Depende de:** MOP-102, 103, 104, 105

**Descripción:**  
Reemplaza la página de inicio genérica del admin. Eli entra y ve el estado del negocio sin hacer nada más.

**Métricas a mostrar:**
- Ventas del mes: unidades entregadas + total en Gs
- Ticket promedio del mes
- Pedidos activos (confirmed + deposit): conteo con link
- Pedidos por canal (`source`) — top canales del mes
- Pedidos por modalidad (retiro vs envío) del mes
- Top 5 productos más vendidos del mes (por unidades)
- Productos con stock bajo (< `stock_min` o < 2 si no definido)
- Últimos 5 pedidos registrados

**Implementación:**
- Custom admin view en `config/` o `catalog/`
- Todo calculado con ORM, sin librerías externas
- Template con tarjetas usando clases de unfold
- Links desde cada métrica al listado filtrado correspondiente

**Criterios de aceptación:**
- [ ] Al entrar al admin → dashboard en lugar del índice genérico
- [ ] Métricas calculadas correctamente
- [ ] Test: mes sin pedidos muestra 0 en todas las métricas sin errores
- [ ] Test: top productos refleja solo pedidos `delivered` del mes

---

### MOP-110 · Reporte de márgenes por producto vendido
**Prioridad:** Media | **Esfuerzo:** Medio  
**Commit:** `MOP-110 · Reporte de márgenes por producto vendido`

**Descripción:**  
Saber qué productos generan más ganancia real — no solo cuántos se vendieron. Informa decisiones de reposición.

**Implementación:**
- Custom admin view: `/ops/reportes/margenes/`
- Rango de fechas filtrable (default: mes actual)
- Tabla con: producto, costo unitario, precio cobrado promedio, margen real %, unidades vendidas, ganancia total en Gs
- Solo pedidos con status `delivered`
- Precio cobrado = `unit_price` de `OrderLine` (snapshot al confirmar) menos proporción de descuento del pedido
- Ordenado por ganancia total desc

**Criterios de aceptación:**
- [ ] Vista accesible desde el sidebar del admin
- [ ] Filtro por rango de fechas funciona
- [ ] Cálculo de margen usa precio real cobrado, no precio de lista
- [ ] Test: producto vendido con descuento refleja margen reducido

---

### MOP-111 · Ajuste de inventario (conteo físico)
**Prioridad:** Media | **Esfuerzo:** Medio  
**Commit:** `MOP-111 · Ajuste de inventario`

**Descripción:**  
Con 53 piezas en stock ya vale tener un conteo formal. Especialmente antes de reposición mes 2.

**Modelos:**
```python
StocktakingSession:
    date            DateField
    status          CharField: open / closed
    notes           TextField (blank)
    created_by      FK → User
    closed_at       DateTimeField (null)
    filter_category FK → Category (null)

StocktakingLine:
    session       FK → StocktakingSession
    product       FK → Product
    system_stock  PositiveIntegerField  # snapshot al abrir
    counted_stock PositiveIntegerField (null)  # ingresado por Eli
    difference    IntegerField (property: counted - system)
    adjusted      BooleanField (default False)
```

**Flujo:**
1. Crear sesión → genera líneas para todos los productos activos (o filtrado por categoría)
2. Eli anota `counted_stock` por producto
3. "Finalizar sesión" → actualiza `Product.stock` donde diferencia ≠ 0
4. Sesión cerrada → solo lectura

**Admin:** Lista de líneas con columnas: código, nombre, dice, hay, diferencia (verde/rojo/naranja). Botón "Finalizar sesión" con confirmación.

**Criterios de aceptación:**
- [ ] Crear sesión genera líneas correctas
- [ ] Finalizar ajusta stock correctamente
- [ ] Sesión cerrada no editable
- [ ] Test: diferencia negativa se refleja en stock
- [ ] Test: sesión cerrada lanza error si se intenta modificar

---

## 🧊 Icebox (sin fecha)

> Movidos desde backlog anterior. Revisar en mes 2 si el volumen lo justifica.

- **MOP-I01** · Notas en Productos (campo libre operativo)
- **MOP-I02** · Exportar a Excel (stock, compras, pedidos)
- **MOP-I03** · Alertas de stock mínimo configurable por producto
- **MOP-I04** · Historial de compras por cliente en vista Customer
- **MOP-I05** · Etiqueta de producto para impresión (nombre + precio + código)

---

## 🔮 Futuro (sin fecha)

- **Multi-sucursal** — stock separado por ubicación
- **Integración ekuatia'i** — API pública de facturación electrónica
- **Catálogo público** — frontend para Instagram bio link