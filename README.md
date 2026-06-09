<div align="center">

# 🌑 Viagens Espaciais — Exploração de Cavernas Lunares

### Missão Aracne · Cena 3D autoral em Blender

![Blender](https://img.shields.io/badge/Blender-5.1-E87D0D?logo=blender&logoColor=white)
![Cycles](https://img.shields.io/badge/Render-Cycles%20(OptiX)-222)
![Three.js](https://img.shields.io/badge/3D%20Web-Three.js-000?logo=three.js&logoColor=white)
![Tema](https://img.shields.io/badge/Tema-Viagens%20Espaciais-36d6ff)

![Vista geral da missão](docs/prints/01_hero.png)

</div>

---

## 📖 Sobre o projeto

Uma missão fictícia de **exploração de cavernas lunares**: **aranhas-robô** autônomas
percorrem o relevo da Lua, apoiadas por um **foguete-lander** e por um **satélite de
comunicação** em órbita, sob o olhar da **Terra**. Todos os objetos principais foram
**modelados de forma autoral** no Blender, com materiais PBR, iluminação de três pontos
e gerenciamento de cor AgX.

> Tema da atividade: **Viagens Espaciais** · Ferramenta: **Blender 5.1 / Cycles**

---

## 🛰️ Objetos modelados (autorais)

| | |
|---|---|
| 🕷️ **Aranhas-exploradoras** | Corpo compacto, cabeça-sensor com cluster de olhos, faróis, sonda e seis pernas hexápodes arqueadas de três segmentos. |
| 🚀 **Foguete-lander** | Corpo de foguete com nariz cônico, aletas, janelas e antena, sobre estágio de descida octogonal com pernas, tanques e bocal. |
| 📡 **Satélite** | Corpo com louvers térmicos e star-tracker, painéis solares com grade de células e antena parabólica côncava com nervuras e alimentador. |
| 🇧🇷 **Bandeira do Brasil** | Marco da missão fincado no solo lunar. |
| 🌑 **Cenário** | Terreno lunar com crateras, caverna com arco de rochas e brilho interno, campo de estrelas/nebulosa e **Terra** procedural (nuvens, atmosfera e luzes de cidade). |

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
├── moon_scene.blend              # Cena Blender (editável, com Collections e partes nomeadas)
├── Trabalho_Viagens_Espaciais.pdf# Documento (capa + 16 figuras com legendas)
└── docs/                         # Site interativo
    ├── index.html  style.css  script.js  spider-data.js
    ├── models/spider.glb         # Aranha exportada (3D web)
    └── prints/                   # 16 renders 1920×1080
```

---

## ▶️ Como abrir

**Site:** abra `docs/index.html` no navegador.

**Blender:** abra `moon_scene.blend` no Blender 5.1 — cada objeto está em sua própria
Collection, dividido em partes nomeadas (ex.: `Satelite_Antena_Parabolica`, `Foguete_Motor`,
`Aranha1_Pernas`), pronto para inspeção em Wireframe / Edit Mode.

---

## 👥 Integrantes do Grupo (FIAP)

| Nome | RM |
|------|----|
| Arthur Marcio de Barros Silva | 563359 |
| Matheus Goes da Silva | 566407 |
| Maria Eduarda Sousa Acyole de Oliveira | 566337 |
| Mayke Costa Santos | 562680 |
| Gabriela Abdelnor Tavares | 562291 |

---

<div align="center">
<sub>Modelagem 3D autoral · Blender 5.1 (Cycles) · Visualização 3D com Three.js</sub><br>
<sub>© 2026 · Grupo FIAP</sub>
</div>
