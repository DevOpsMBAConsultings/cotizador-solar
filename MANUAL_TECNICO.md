# Manual Técnico: Módulo de Cotización Solar

## Estructura del Módulo
- **models/solar_quote.py**: Define el modelo `solar.quote` con campos y métodos
- **views/solar_quote_views.xml**: Define las vistas (tree, form, search)
- **reports/solar_quote_report.xml**: Define el reporte PDF
- **security/**: Contiene reglas de acceso
- **tests/test_solar_quote.py**: Pruebas unitarias
- **static/src/css/cotizador_solar.css**: Estilos CSS

## Modelo `solar.quote`
### Campos principales
- Campos de consumo mensual (M1-M12)
- `mode`: Modo de cálculo (rápido/avanzado)
- `total_yearly_consumption`: Consumo anual total (computado)
- `avg_daily_consumption`: Consumo diario promedio (computado)
- Campos específicos por modo (quick_*, advanced_*)

### Métodos clave
#### `_compute_consumption_stats()`
- **Dependencias**: Campos de consumo M1-M12
- **Lógica**: Calcula estadísticas de consumo anual, diario y mensual

#### `_compute_solar_calculations()`
- **Dependencias**: 
  - `mode`, campos de consumo, campos específicos de modo
- **Lógica**: Realiza cálculos solares según el modo seleccionado

#### `action_auto_size_advanced()`
- **Propósito**: Calcula automáticamente el tamaño del sistema en modo avanzado

#### `action_generate_proposal()`
- **Propósito**: Genera propuesta PDF usando el reporte definido

## Dependencias
- Módulos base de Odoo (base, web, sale)
- Librería Python: `odoo`

## Pruebas Unitarias
- `TestSolarQuote` en `tests/test_solar_quote.py`
  - `test_01_consumption_stats`: Verifica cálculos de consumo
  - `test_02_quick_calculation_mode`: Prueba modo rápido
  - `test_03_advanced_calculation_mode`: Prueba modo avanzado
  - `test_04_action_generate_proposal`: Verifica generación de propuesta
