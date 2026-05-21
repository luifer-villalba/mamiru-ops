# mamiru-ops

Backend interno para Mamiru – catálogo de productos, proveedores y categorías con API REST y panel de administración.

---

## Versiones elegidas y por qué

| Dependencia | Versión | Razón |
|---|---|---|
| Python | 3.12 | Versión estable y moderna, soportada por Railway, compatible con todas las dependencias. |
| Django | 6.0.5 | Última versión estable. |
| Django REST Framework | 3.17.1 | Última versión estable. |
| psycopg2-binary | 2.9.12 | Última versión estable del driver PostgreSQL. |
| Pillow | 12.2.0 | Versión estable actual para soporte de imágenes. Incluye parches de seguridad contra OOB write y GZIP bomb. |
| Gunicorn | 26.0.0 | Última versión estable del servidor WSGI. |
| WhiteNoise | 6.12.0 | Última versión estable para servir archivos estáticos. |
| dj-database-url | 3.1.2 | Última versión estable para parsear `DATABASE_URL`. |
| python-dotenv | 1.2.2 | Última versión estable. |

---

## Estructura del proyecto

```
mamiru-ops/
├── config/              # Configuración del proyecto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── catalog/             # App principal
│   ├── models.py        # Supplier, Category, Product, ProductImage
│   ├── admin.py         # Panel de administración
│   ├── serializers.py   # DRF serializers
│   ├── views.py         # DRF viewsets
│   ├── urls.py          # Router de la API
│   └── management/
│       └── commands/
│           └── import_mamiru_stock.py
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── .env.example
├── .dockerignore
├── railway.json
└── requirements.txt
```

---

## 1. Instalar dependencias localmente (sin Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. Configurar variables de entorno

Copiá el archivo de ejemplo y ajustá los valores:

```bash
cp .env.example .env
```

Para desarrollo local sin Docker, podés usar SQLite dejando `DATABASE_URL` vacío o apuntando a SQLite:

```env
DEBUG=True
SECRET_KEY=una-clave-secreta-larga-y-aleatoria
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

---

## 3. Correr migraciones

```bash
python manage.py migrate
```

---

## 4. Crear superusuario

```bash
python manage.py createsuperuser
```

---

## 5. Importar el CSV

```bash
python manage.py import_mamiru_stock ruta/al/archivo.csv
```

El CSV debe tener columnas: `Codigo`, `Producto`, `Categoría`, `Material`, `Tipo`, `Proveedor`, `Costo`, `Costo Mayorista`, `Margen %`, `Precio Venta`, `Stock Actual`.

El importador:
- Genera código automático `MAM-0001` si `Codigo` está vacío.
- Limpia precios tipo `55,000Gs.` → `55000`.
- Crea categorías y proveedores si no existen.
- Actualiza productos existentes por código.
- Muestra resumen al final.

---

## 6. Correr servidor local (sin Docker)

```bash
python manage.py runserver
```

---

## 7. Correr localmente con Docker Compose

```bash
# Copiá el env de ejemplo (ya tiene los valores para Docker)
cp .env.example .env

# Levantá los servicios
docker compose up --build

# En otra terminal, creá el superusuario
docker compose exec web python manage.py createsuperuser
```

Los servicios quedan disponibles en:
- Web: http://localhost:8000
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/

---

## 8. Entrar al Django Admin

Abrí http://localhost:8000/admin/ e ingresá con el superusuario creado.

Desde el admin podés:
- Crear/editar proveedores, categorías y productos.
- Subir fotos a productos.
- Filtrar por categoría, proveedor o estado.

---

## 9. Probar la API REST

```bash
# Listar productos
curl http://localhost:8000/api/products/

# Ver un producto por slug
curl http://localhost:8000/api/products/mi-producto/

# Listar categorías
curl http://localhost:8000/api/categories/

# Listar proveedores
curl http://localhost:8000/api/suppliers/
```

---

## 10. Deploy en Railway

### Requisitos previos
- Cuenta en [Railway](https://railway.app/)
- Railway CLI instalado: `npm install -g @railway/cli`

### Pasos

```bash
railway login
railway init
railway up
```

### 11. Configurar PostgreSQL en Railway

1. En el dashboard de Railway, agregá un servicio **PostgreSQL**.
2. Railway genera automáticamente la variable `DATABASE_URL`.
3. Vinculá esa variable a tu servicio web.

### 12. Configurar variables de entorno en Railway

En el dashboard de Railway → tu servicio → Variables, configurá:

```
DEBUG=False
SECRET_KEY=tu-clave-secreta-de-produccion
ALLOWED_HOSTS=tuapp.railway.app
CSRF_TRUSTED_ORIGINS=https://tuapp.railway.app
DATABASE_URL=<automáticamente provista por Railway PostgreSQL>
STATIC_ROOT=/app/staticfiles
MEDIA_ROOT=/app/media
```

Railway detecta el `Dockerfile` automáticamente y usa `entrypoint.sh` como comando de inicio.

---

## Variables de entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `SECRET_KEY` | Sí | Clave secreta de Django |
| `DEBUG` | No | `True` en desarrollo, `False` en producción |
| `DATABASE_URL` | Sí (Docker/Railway) | URL de conexión a PostgreSQL |
| `ALLOWED_HOSTS` | Sí | Hosts permitidos separados por coma |
| `CSRF_TRUSTED_ORIGINS` | Producción | Orígenes confiables para CSRF |
| `STATIC_ROOT` | No | Directorio para `collectstatic` |
| `MEDIA_ROOT` | No | Directorio para imágenes subidas |

---

## Notas sobre imágenes en producción

Actualmente las imágenes de productos se almacenan localmente en `media/`. Para producción en Railway (sin storage persistente), se recomienda migrar a:

- **Cloudinary**: via `django-cloudinary-storage`
- **Amazon S3**: via `django-storages[s3]`
- **Supabase Storage**: via `django-storages` + S3-compatible API

La configuración está preparada para esta migración futura modificando `DEFAULT_FILE_STORAGE` en `settings.py`.
