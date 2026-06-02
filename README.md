<div align="center">

# 🌑 Viagens Espaciais — Exploração de Cavernas Lunares

### Missão Aracne · Cena 3D autoral em Blender

![Blender](https://img.shields.io/badge/Blender-5.1-E87D0D?logo=blender&logoColor=white)
![Cycles](https://img.shields.io/badge/Render-Cycles%20(OptiX)-222)
![Three.js](https://img.shields.io/badge/3D%20Web-Three.js-000?logo=three.js&logoColor=white)
![Tema](https://img.shields.io/badge/Tema-Viagens%20Espaciais-36d6ff)

**🚀 [Ver o site interativo ao vivo »](https://maykesantos98.github.io/arvrGsFiap2026/)**

![Vista geral da missão](docs/prints/01_hero.png)

</div>

---

## 📖 Sobre o projeto

Uma missão fictícia de **exploração de cavernas lunares**: **aranhas-robô** autônomas
percorrem o relevo da Lua, apoiadas por um **foguete-lander** e por um **satélite de
comunicação** em órbita, sob o olhar da **Terra**. Todos os objetos principais foram
**modelados de forma autoral por geometria procedural** no Blender (script Python `bpy`),
com materiais PBR, iluminação de três pontos e gerenciamento de cor AgX.

> Tema da atividade: **Viagens Espaciais** · Ferramenta: **Blender 5.1 / Cycles**

---

## 🛰️ Objetos modelados (autorais)

| | |
|---|---|
| 🕷️ **Aranhas-exploradoras** | Corpo compacto, cabeça-sensor com cluster de olhos, faróis, sonda e seis pernas hexápodes arqueadas de três segmentos. |
| 🚀 **Foguete-lander** | Corpo de foguete com nariz cônico, aletas, janelas e antena, sobre estágio de descida octogonal com pernas, tanques e bocal. |
| 📡 **Satélite** | Corpo com manta térmica, painéis solares procedurais e antena parabólica. |
| 🇧🇷 **Bandeira do Brasil** | Marco da missão fincado no solo lunar. |
| 🌑 **Cenário** | Terreno lunar com crateras, caverna com arco de rochas e brilho interno, campo de estrelas/nebulosa e **Terra procedural** (nuvens, atmosfera e luzes de cidade). |

---

## 🖼️ Galeria

| Aranha-exploradora | Foguete-lander | A Terra |
|:---:|:---:|:---:|
| ![](docs/prints/03_robo_heroi.png) | ![](docs/prints/08_foguete.png) | ![](docs/prints/12_terra.png) |

| Satélite | Caverna lunar | Bandeira do Brasil |
|:---:|:---:|:---:|
| ![](docs/prints/06_satelite.png) | ![](docs/prints/11_caverna.png) | ![](docs/prints/10_bandeira.png) |

### Modelagem (prova de autoria)

| Wireframe da cena | Clay do robô | Wireframe do robô |
|:---:|:---:|:---:|
| ![](docs/prints/14_wireframe_cena.png) | ![](docs/prints/15_clay_robo.png) | ![](docs/prints/16_wireframe_robo.png) |

> A galeria completa (16 imagens) e a história animada da expedição estão no
> **[site interativo](https://maykesantos98.github.io/arvrGsFiap2026/)**.

---

## ✨ Site interativo

- **História da expedição** em 7 capítulos com animações de scroll.
- **Visualizador 3D** (Three.js) da aranha — arraste para orbitar, role para zoom.
- **Galeria** com filtros por categoria e lightbox navegável.
- Fundo de estrelas animado e tema espacial.

---

## 📂 Estrutura

```
.
├── moon_scene.blend              # Cena Blender (editável, com Collections)
├── moon_scene.py                 # Script-fonte (gera cena, renders e .glb)
├── Trabalho_Viagens_Espaciais.pdf# Documento (capa + 16 figuras com legendas)
├── docs/                         # Site interativo (fonte do GitHub Pages)
│   ├── index.html  style.css  script.js  spider-data.js
│   ├── models/spider.glb         # Aranha exportada (3D web)
│   └── prints/                   # 16 renders 1920×1080
└── fonte-pdf/report.html         # Fonte do PDF
```

---

## ▶️ Como rodar

**Site:** abra <https://maykesantos98.github.io/arvrGsFiap2026/> ou `docs/index.html` localmente.

**Blender:** abra `moon_scene.blend` no Blender 5.1.

**Regerar os renders:**
```bash
blender -b --factory-startup -P moon_scene.py -- --shots "docs/prints" --save "moon_scene.blend"
```

**Exportar a aranha 3D (.glb):**
```bash
blender -b --factory-startup -P moon_scene.py -- --export "docs/models/spider.glb"
```

---

## 👥 Autores

- [@Maykesantos98](https://github.com/Maykesantos98)
- [@jhowcardinale](https://github.com/jhowcardinale)

---

<div align="center">
<sub>Modelagem 3D autoral · Blender 5.1 (Cycles) · Visualização 3D com Three.js</sub><br>
<sub>© 2026 · Maykesantos98 &amp; jhowcardinale</sub>
</div>
