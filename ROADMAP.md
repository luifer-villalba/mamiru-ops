# 🗺️ Roadmap — mamiru-ops

Seguimiento interno de features. Actualizar al cerrar cada tarea.  
Prefijo de tickets: `MOP-` (Mamiru Ops), arranca en `MOP-100`.

---

## ✅ Done

- Catálogo de productos (Product, Category, Supplier, ProductImage)
- Panel de administración con django-unfold
- Filtros de stock (bajo, sin stock), acciones bulk (activar, ocultar, sin stock)
- Importador CSV (`import_mamiru_stock`)
- API REST de solo lectura (`/api/products/`, `/api/categories/`, `/api/suppliers/`)
- Órdenes de compra (PurchaseOrder + PurchaseOrderLine) con ajuste de stock automático
- MOP-100 · Historial de precios con auditoría de cambios en producto
- Login con usuario o email
- CI con GitHub Actions (tests + ruff)
- Deploy en Railway con Docker

---

## 🚧 In Progress

_(nada actualmente)_

---

## 📋 Backlog

### MOP-101 · Clientes y Pedidos
**Prioridad:** Alta  
**Esfuerzo:** Medio

**Descripción:**  
Registrar clientes y sus pedidos internamente. No reemplaza la facturación — el operador lleva el pedido a ekuatia'i para facturar.

**Modelos:**
```
Customer:
  name        CharField
  whatsapp    CharField (opcional)
  city        CharField (opcional)
  notes       TextField (opcional)
  created_at  DateTimeField (auto)

Order:
  customer    FK → Customer
  date        DateField
  status      CharField: borrador / confirmado / entregado / cancelado
  notes       TextField (opcional)
  created_by  FK → User
  created_at  DateTimeField (auto)

OrderLine:
  order         FK → Order
  product       FK → Product (nullable, por si se elimina el producto)
  product_name  CharField (snapshot del nombre al momento)
  product_code  CharField (snapshot del código)
  quantity      PositiveIntegerField
  unit_price    PositiveIntegerField (snapshot del precio al momento)
```

**Admin:**
- `CustomerAdmin`: lista con nombre, whatsapp, ciudad + inline de pedidos
- `OrderAdmin`: lista con cliente, fecha, estado, total calculado
- `OrderLine` como inline en Order
- Filtros: por estado, por fecha, por cliente
- Total del pedido calculado (sum de líneas) visible en lista y detalle

**Criterios de aceptación:**
- [ ] Crear cliente con whatsapp → aparece en lista
- [ ] Crear pedido con líneas → total se calcula correctamente
- [ ] Historial de pedidos visible desde el detalle del cliente
- [ ] Snapshot de nombre y precio se guarda al confirmar (no cambia si el producto se edita después)
- [ ] Tests cubren: creación, cálculo de total, snapshot de precios

---

### MOP-102 · Ajuste de Inventario (Conteo Físico)
**Prioridad:** Alta  
**Esfuerzo:** Medio

**Descripción:**  
Flujo para que Eli haga un conteo físico de productos. Ve lo que "dice" el sistema y anota lo que "hay" en la realidad. Al finalizar, el sistema ajusta el stock automáticamente y guarda la diferencia como auditoría.

**Modelos:**
```
StocktakingSession:
  date              DateField
  status            CharField: abierta / cerrada
  notes             TextField (opcional)
  created_by        FK → User
  closed_at         DateTimeField (nullable)
  filter_category   FK → Category (nullable)
  filter_supplier   FK → Supplier (nullable)

StocktakingLine:
  session        FK → StocktakingSession
  product        FK → Product
  system_stock   PositiveIntegerField (snapshot al abrir = "dice")
  counted_stock  PositiveIntegerField (nullable = "hay", ingresado por Eli)
  difference     IntegerField (computed: counted - system, puede ser negativo)
  adjusted       BooleanField (default False)
```

**Flujo:**
1. Operador crea sesión → elige filtro opcional (categoría o proveedor)
2. Sistema genera `StocktakingLine` por cada producto activo del filtro, capturando `system_stock`
3. Eli va producto por producto anotando `counted_stock`
4. Al hacer "Finalizar sesión" → sistema actualiza `Product.stock = counted_stock` para cada línea con diferencia ≠ 0
5. Sesión queda cerrada → no editable

**Admin:**
- Vista custom "Finalizar sesión" con botón de confirmación
- Lista de líneas muestra: código, nombre, dice, hay, diferencia (con color: verde=ok, rojo=falta, naranja=sobra)
- Sesiones cerradas son de solo lectura

**Criterios de aceptación:**
- [ ] Crear sesión sin filtro → genera líneas para todos los productos activos
- [ ] Crear sesión con filtro categoría → solo productos de esa categoría
- [ ] Finalizar sesión → stock de productos ajustado correctamente
- [ ] Sesión cerrada → líneas no editables
- [ ] Diferencia negativa (hay menos de lo que dice) se refleja correctamente
- [ ] Tests cubren: generación de líneas, ajuste de stock, sesión cerrada no editable

---

### MOP-103 · Dashboard
**Prioridad:** Media  
**Esfuerzo:** Medio

**Descripción:**  
Vista de inicio del admin con métricas clave del negocio. Reemplaza la página de índice genérica de Django.

**Métricas a mostrar:**
- Valor total del inventario (sum de `stock × cost_price`)
- Productos con stock bajo (< umbral, configurable)
- Productos sin stock
- Últimas 5 órdenes de compra
- Últimos 5 pedidos de clientes
- Total de clientes registrados
- Productos activos / ocultos / sin stock (conteo por estado)

**Implementación:**
- Custom admin view en `config/` o `catalog/`
- Template con tarjetas de métricas usando clases de unfold
- Sin dependencias externas (solo ORM)

**Criterios de aceptación:**
- [ ] Al entrar al admin → se ve el dashboard en lugar del índice genérico
- [ ] Métricas se calculan correctamente
- [ ] Links desde métricas llevan al listado filtrado correspondiente
- [ ] No rompe el flujo de navegación del admin

---

### MOP-104 · Notas en Productos
**Prioridad:** Media  
**Esfuerzo:** Bajo

**Descripción:**  
Campo libre en `Product` para que Eli anote observaciones operativas: particularidades del proveedor, condiciones de reposición, etc.

**Cambios:**
- Agregar `notes = TextField(blank=True, default="")` a `Product`
- Migración correspondiente
- Agregar al fieldset de "Detalles" en `ProductAdmin`
- Indicador visual en lista si tiene contenido

**Criterios de aceptación:**
- [ ] Campo editable en el admin
- [ ] Campo vacío por defecto, no rompe importador CSV
- [ ] Migración aplica sin errores en producción

---

### MOP-105 · Exportar a Excel
**Prioridad:** Media  
**Esfuerzo:** Medio

**Descripción:**  
Exportar datos clave a Excel desde el admin, para reportes y reuniones sin necesidad de acceso al sistema.

**Exports planificados:**
- Stock actual (código, nombre, categoría, proveedor, stock, costo, precio venta)
- Historial de compras (órdenes + líneas, por rango de fechas)
- Pedidos por cliente (por rango de fechas)

**Implementación:**
- Acciones bulk en los admins correspondientes (`export_to_excel`)
- Librería: `openpyxl` (agregar a requirements si no está)
- Archivo descargado directamente desde el navegador

**Criterios de aceptación:**
- [ ] Seleccionar productos → "Exportar a Excel" → descarga .xlsx con datos correctos
- [ ] Columnas con headers en español
- [ ] Precios formateados como números (no strings con "Gs.")
- [ ] Tests cubren: que el response es un .xlsx válido

---

### MOP-106 · Alertas de Stock Mínimo
**Prioridad:** Baja  
**Esfuerzo:** Bajo

**Descripción:**  
Definir un umbral de stock mínimo por producto. El dashboard y el admin muestran alertas cuando el stock cae por debajo.

**Cambios:**
- Agregar `stock_min = PositiveIntegerField(default=0)` a `Product`
- Migración correspondiente
- `StockLevelFilter` actualizado para usar `stock_min` en lugar de valor hardcodeado
- Dashboard MOP-103 muestra sección "Reponer pronto" con productos bajo umbral
- Indicador visual en lista de productos

**Dependencia:** MOP-103 (Dashboard)

**Criterios de aceptación:**
- [ ] Definir `stock_min=5` en un producto con `stock=3` → aparece en alertas
- [ ] Producto con `stock_min=0` → no genera alerta aunque stock sea 0
- [ ] Migración aplica sin errores

---

## 🔮 Futuro (sin fecha)

- **Multi-sucursal** — stock separado por ubicación si Mamiru abre otra tienda
- **Integración ekuatia'i** — si habilitan API pública para facturación electrónica
