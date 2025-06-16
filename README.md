<p align="center">
  <h1 style="font-size:80px; font-weight: 800;" align="center">D A T A N I A</h1>
  <p align="center">Datos, sin complicaciones.</a> </p>
</p>

<div align="center">
  <img alt="GitHub" src="https://img.shields.io/github/license/davidgasquez/datania?style=flat-square">
  <img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/davidgasquez/datania/ci.yml?style=flat-square">
  <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/davidgasquez/datania?style=flat-square">
</div>

<br>

Datania es una plataforma de datos abiertos colaborativa con el objetivo de unificar y armonizar información de diversas fuentes a nivel de España.

<div align="center">

[![Acceder a los datos en Hugging Face](https://img.shields.io/badge/🤗%20Hugging%20Face-Acceder%20a%20los%20datos-FFD21E?style=for-the-badge&logoColor=black)](https://huggingface.co/datania)

</div>

## 📋 Recursos

Aquí tienes algunos recursos que te pueden ser de utilidad relacionados con datos abiertos y transparencia a nivel de España.

- [INE](https://www.ine.es/).
- [Datos Abiertos de España](https://datos.gob.es/) (y en [GitHub](https://github.com/datosgobes)).
- [Iniciativa Aporta](https://datos.gob.es/es/acerca-de-la-iniciativa-aporta).
- [DGT](https://nap.dgt.es/dataset). También en [mapa](https://infocar.dgt.es/etraffic/).
- [AEMET](https://opendata.aemet.es/centrodedescargas/inicio).
- [WikiData](https://www.wikidata.org/).
- [ESRI](https://opendata.esri.es/search?collection=Dataset).
- [Datadista](https://www.datadista.com/).
- [Newtral](https://transparentia.newtral.es/buscador).
- [Spanish Origin Destination Data](https://github.com/rOpenSpain/spanishoddata).
- [DataMarket](https://github.com/Data-Market).
- [Eurostat](https://ec.europa.eu/eurostat/data/database). Existe una librería en [R](https://github.com/rOpenGov/eurostat).
- [Gobierto](https://www.gobierto.es/)
- [Vulturno](https://github.com/vulturno)

## 💡 Principios

- **Transparencia**: Código, estándares, infraestructura, y datos, son públicos. Usa herramientas, estándares e infraestructuras abiertas, y comparte datos en [formatos accesibles](https://voltrondata.com/codex/a-new-frontier).
- **Modularidad**: Cada componente o dataset puede ser reemplazado, extendido o eliminado. El código funciona bien en muchos entornos (un portátil, un clúster, o desde el navegador) y puede desplegarse en distintos lugares.
- **Sin Rozamiento**: No preguntes, haz un fork y mejora el código, los modelos, o añade una nueva fuente de datos. Usa los datasets sin límites de API o cuotas.
- **Datos como Código**: Transformaciones declarativas trackeadas en `git`. Los datasets y sus transformaciones se publican para que otras personas puedan construir sobre ellos.
- **Pegamento**: Datania es un puente entre herramientas y enfoques y no un estándar o una herramienta en sí misma. Se integra con otras herramientas y servicios.

## ⚙️ Configuración

Si quieres contribuir, es fácil! Clona el repositorio y sigue estas instrucciones.

Cualquier problema que encuentres, no dudes en [abrir una issue](https://github.com/davidgasquez/datania/issues/new)!

### 🐍 Python

Instala Python en tu sistema y opcionalmente, [`uv`](https://github.com/astral-sh/uv).

Si tienes `uv`, puedes instalar todas las dependencias dentro de un entorno virtual de Python ejecutando `make setup` una vez hayas clonado el repositorio.

```bash
make setup
```

Si no quieres instalar `uv`, puedes usar Python para crear un entorno virtual y instalar las dependencias.

```bash
python3 -m venv .venv
source .venv/bin/activate

# Install the package and dependencies
pip install -e ".[dev]"
```

Ahora, puedes ejecutar `make run` para empezar a descargar datos.

## 📄 Licencia

Datania es un proyecto de código abierto bajo la licencia [MIT](LICENSE).
